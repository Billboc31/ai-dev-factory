from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import threading
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ..models.sandbox import SandboxState, SandboxStatus

logger = logging.getLogger("control-api")

_BASE_WEB_PORT = 3000
_BASE_API_PORT = 8080
_PORT_STEP = 100

# Module-level lock guards port-registry.json reads/writes.
_registry_lock = threading.Lock()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class SandboxNotFoundError(Exception):
    pass


class SandboxManager:
    def __init__(self, sandboxes_dir: Path | None = None) -> None:
        if sandboxes_dir is None:
            runtime_root = os.environ.get("AI_DEV_FACTORY_RUNTIME_ROOT")
            if runtime_root:
                sandboxes_dir = Path(runtime_root) / "sandboxes"
            else:
                sandboxes_dir = Path.cwd() / "sandboxes"
        self.sandboxes_dir = sandboxes_dir
        self.sandboxes_dir.mkdir(parents=True, exist_ok=True)
        self._registry_path = self.sandboxes_dir / "port-registry.json"

    # --- port registry ---

    def _read_registry(self) -> dict[str, int]:
        try:
            return json.loads(self._registry_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}

    def _write_registry(self, registry: dict[str, int]) -> None:
        self._registry_path.write_text(
            json.dumps(registry, indent=2), encoding="utf-8"
        )

    def _allocate_slot(self, sandbox_id: str) -> int:
        with _registry_lock:
            registry = self._read_registry()
            used = set(registry.values())
            slot = 1
            while slot in used:
                slot += 1
            registry[sandbox_id] = slot
            self._write_registry(registry)
            return slot

    def _release_slot(self, sandbox_id: str) -> None:
        with _registry_lock:
            registry = self._read_registry()
            registry.pop(sandbox_id, None)
            self._write_registry(registry)

    # --- state helpers ---

    def _sandbox_dir(self, sandbox_id: str) -> Path:
        return self.sandboxes_dir / sandbox_id

    def _state_path(self, sandbox_id: str) -> Path:
        return self._sandbox_dir(sandbox_id) / "state.json"

    def _read_state(self, sandbox_id: str) -> SandboxState:
        path = self._state_path(sandbox_id)
        if not path.exists():
            raise SandboxNotFoundError(f"sandbox not found: {sandbox_id}")
        return SandboxState.model_validate_json(path.read_text(encoding="utf-8"))

    def _write_state(self, state: SandboxState) -> None:
        path = self._state_path(state.id)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(state.model_dump_json(indent=2), encoding="utf-8")

    # --- compose helper ---

    def _run_compose(self, sandbox: SandboxState, *args: str) -> tuple[int, str, str]:
        cmd = [
            "docker", "compose",
            "-p", sandbox.compose_project,
            "--env-file", sandbox.env_file,
        ] + list(args)
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=sandbox.project_root,
            check=False,
        )
        return result.returncode, result.stdout, result.stderr

    # --- public API ---

    def create(self, ticket_id: str, project_root: str) -> SandboxState:
        sandbox_id = uuid.uuid4().hex[:12]
        slot = self._allocate_slot(sandbox_id)

        compose_project = f"sandbox-{sandbox_id}"
        web_port = _BASE_WEB_PORT + slot * _PORT_STEP
        api_port = _BASE_API_PORT + slot * _PORT_STEP
        ports: dict[str, int] = {"web": web_port, "api": api_port}

        sandbox_dir = self._sandbox_dir(sandbox_id)
        sandbox_dir.mkdir(parents=True, exist_ok=True)

        env_file = sandbox_dir / ".env"
        env_file.write_text(
            f"COMPOSE_PROJECT_NAME={compose_project}\n"
            f"WEB_PORT={web_port}\n"
            f"API_PORT={api_port}\n",
            encoding="utf-8",
        )

        state = SandboxState(
            id=sandbox_id,
            ticket_id=ticket_id,
            project_root=project_root,
            compose_project=compose_project,
            ports=ports,
            env_file=str(env_file),
            status=SandboxStatus.stopped,
            created_at=_now_iso(),
            slot=slot,
        )
        self._write_state(state)
        logger.info("sandbox created: %s (slot=%d ports=%s)", sandbox_id, slot, ports)
        return state

    def start(self, sandbox_id: str) -> SandboxState:
        state = self._read_state(sandbox_id)
        rc, _out, err = self._run_compose(state, "up", "-d")
        if rc != 0:
            logger.warning("sandbox start failed: %s — %s", sandbox_id, err.strip())
            state = state.model_copy(update={"status": SandboxStatus.error})
        else:
            state = state.model_copy(update={"status": SandboxStatus.running})
        self._write_state(state)
        return state

    def stop(self, sandbox_id: str) -> SandboxState:
        state = self._read_state(sandbox_id)
        rc, _out, err = self._run_compose(state, "down")
        if rc != 0:
            logger.warning("sandbox stop warning: %s — %s", sandbox_id, err.strip())
        state = state.model_copy(update={"status": SandboxStatus.stopped})
        self._write_state(state)
        return state

    def create_with_worktree(
        self,
        ticket_id: str,
        project_root: str,
        branch: str | None = None,
        job_type: str = "deploy",
    ) -> SandboxState:
        state = self.create(ticket_id, project_root)
        worktree_path = self._sandbox_dir(state.id) / "worktree"
        if branch:
            cmd = ["git", "worktree", "add", str(worktree_path), branch]
        else:
            cmd = ["git", "worktree", "add", "--detach", str(worktree_path)]
        result = subprocess.run(
            cmd, capture_output=True, text=True, cwd=project_root, check=False
        )
        if result.returncode != 0:
            self.destroy(state.id)
            raise RuntimeError(
                f"git worktree add failed: {result.stderr.strip()}"
            )
        state = state.model_copy(
            update={"worktree_path": str(worktree_path), "job_type": job_type}
        )
        self._write_state(state)
        logger.info(
            "sandbox worktree created: %s job_type=%s path=%s",
            state.id, job_type, worktree_path,
        )
        return state

    def mark_completed(self, sandbox_id: str) -> SandboxState:
        state = self._read_state(sandbox_id)
        state = state.model_copy(
            update={"completed_at": _now_iso(), "status": SandboxStatus.stopped}
        )
        self._write_state(state)
        return state

    def cleanup_completed(self, max_age_minutes: int = 30) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=max_age_minutes)
        destroyed = 0
        for sandbox in self.list():
            if sandbox.completed_at is None:
                continue
            try:
                completed = datetime.fromisoformat(sandbox.completed_at)
                if completed.tzinfo is None:
                    completed = completed.replace(tzinfo=timezone.utc)
                if completed < cutoff:
                    self.destroy(sandbox.id)
                    destroyed += 1
            except Exception:
                pass
        return destroyed

    def destroy(self, sandbox_id: str) -> None:
        try:
            state = self._read_state(sandbox_id)
            if state.worktree_path:
                subprocess.run(
                    ["git", "worktree", "remove", "--force", state.worktree_path],
                    capture_output=True, text=True, check=False,
                )
            self._run_compose(state, "down")
        except SandboxNotFoundError:
            pass
        self._release_slot(sandbox_id)
        sandbox_dir = self._sandbox_dir(sandbox_id)
        if sandbox_dir.exists():
            shutil.rmtree(sandbox_dir)
        logger.info("sandbox destroyed: %s", sandbox_id)

    def status(self, sandbox_id: str) -> SandboxState:
        return self._read_state(sandbox_id)

    def logs(self, sandbox_id: str, component: str | None = None) -> str:
        state = self._read_state(sandbox_id)
        cmd = [
            "docker", "compose",
            "-p", state.compose_project,
            "--env-file", state.env_file,
            "logs", "--no-color",
        ]
        if component:
            cmd.append(component)
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=state.project_root,
            check=False,
        )
        return result.stdout or result.stderr or ""

    def list(self) -> list[SandboxState]:
        sandboxes = []
        for state_file in sorted(self.sandboxes_dir.glob("*/state.json")):
            try:
                sandboxes.append(
                    SandboxState.model_validate_json(
                        state_file.read_text(encoding="utf-8")
                    )
                )
            except Exception:
                pass
        return sandboxes

    def cleanup_old(self, max_age_days: int = 7) -> int:
        cutoff = datetime.now(timezone.utc) - timedelta(days=max_age_days)
        destroyed = 0
        for sandbox in self.list():
            try:
                created = datetime.fromisoformat(sandbox.created_at)
                if created.tzinfo is None:
                    created = created.replace(tzinfo=timezone.utc)
                if created < cutoff:
                    self.destroy(sandbox.id)
                    destroyed += 1
            except Exception:
                pass
        return destroyed
