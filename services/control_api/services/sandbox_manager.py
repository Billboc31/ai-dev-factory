from __future__ import annotations

import json
import logging
import os
import shutil
import signal
import subprocess
import sys
import threading
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

from ..models.sandbox import (
    EnvironmentMode,
    EnvironmentType,
    RefType,
    SandboxState,
    SandboxStatus,
)
from .deployer_runner import _load_deploy_profile
from .infra_service_manager import resolve_proxy_routes_dir
from .proxy_manager import ProxyManager, build_sandbox_urls
from .runtime_resolver import get_project_sandbox_dir
from .undeploy_runner import run_cleanup, run_undeploy

# Single source of truth for compose project-name normalisation, shared
# with the host-side worker (tools/agent_runner/run_sandbox.py). The
# uuid-hex IDs minted here are already lowercase alphanumeric, so the
# call is a no-op in practice — but applying it here too keeps this
# module robust against future ID schemes.
_REPO_ROOT = Path(__file__).resolve().parents[4]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tools.agent_runner.compose_utils import normalize_compose_project_name  # noqa: E402

logger = logging.getLogger("control-api")

_BASE_WEB_PORT = 3000
_BASE_API_PORT = 8080
_PORT_STEP = 100

# Module-level lock guards port-registry.json reads/writes.
_registry_lock = threading.Lock()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


class SandboxNotFoundError(Exception):
    pass


class SandboxManager:
    def __init__(self, sandboxes_dir: Path | None = None) -> None:
        if sandboxes_dir is None:
            sandboxes_dir = get_project_sandbox_dir()
        self.sandboxes_dir = sandboxes_dir
        self.sandboxes_dir.mkdir(parents=True, exist_ok=True)
        self._registry_path = self.sandboxes_dir / "port-registry.json"
        self._proxy = ProxyManager()

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

    def create(
        self,
        ticket_id: str,
        project_root: str,
        *,
        env_name: str | None = None,
        env_type: EnvironmentType | None = None,
        ref: str | None = None,
        ref_type: RefType | None = None,
        deployment_mode: EnvironmentMode | None = None,
        web_host: str | None = None,
        api_host: str | None = None,
    ) -> SandboxState:
        sandbox_id = uuid.uuid4().hex[:12]
        slot = self._allocate_slot(sandbox_id)

        compose_project = normalize_compose_project_name(f"sandbox-{sandbox_id}")
        web_port = _BASE_WEB_PORT + slot * _PORT_STEP
        api_port = _BASE_API_PORT + slot * _PORT_STEP
        supervisor_port = 8090 + slot
        ports: dict[str, int] = {"web": web_port, "api": api_port}

        sandbox_dir = self._sandbox_dir(sandbox_id)
        sandbox_dir.mkdir(parents=True, exist_ok=True)
        sandbox_runtime_root = str(sandbox_dir / "runtime")

        # Pre-compute the pretty URLs. Custom hosts (if provided) are used
        # verbatim; otherwise the default sandbox-<id>.* pattern applies.
        urls = build_sandbox_urls(sandbox_id, web_host=web_host, api_host=api_host)
        env_file = sandbox_dir / ".env"
        env_file.write_text(
            f"COMPOSE_PROJECT_NAME={compose_project}\n"
            f"WEB_PORT={web_port}\n"
            f"API_PORT={api_port}\n"
            f"SANDBOX_ID={sandbox_id}\n"
            f"SANDBOX_WEB_URL={urls['web']}\n"
            f"SANDBOX_API_URL={urls['api']}\n"
            # Two distinct supervisor URLs — see deploy/.env.example:
            #   * SUPERVISOR_URL: how *containers* reach the host
            #     supervisor (via host.docker.internal);
            #   * SUPERVISOR_HEALTH_URL: how *host-side* scripts
            #     (healthcheck.sh) reach it (host.docker.internal is
            #     not resolvable from the host, so we need 127.0.0.1).
            f"AI_DEV_FACTORY_SUPERVISOR_PORT={supervisor_port}\n"
            f"AI_DEV_FACTORY_SUPERVISOR_URL=http://host.docker.internal:{supervisor_port}\n"
            f"AI_DEV_FACTORY_SUPERVISOR_HEALTH_URL=http://127.0.0.1:{supervisor_port}\n"
            f"AI_DEV_FACTORY_RUNTIME_ROOT={sandbox_runtime_root}\n",
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
            supervisor_port=supervisor_port,
            sandbox_runtime_root=sandbox_runtime_root,
            env_name=env_name,
            env_type=env_type,
            ref=ref,
            ref_type=ref_type,
            deployment_mode=deployment_mode,
            web_host=web_host,
            api_host=api_host,
        )
        self._write_state(state)
        logger.info("sandbox created: %s (slot=%d ports=%s)", sandbox_id, slot, ports)
        return state

    def start(self, sandbox_id: str) -> SandboxState:
        state = self._read_state(sandbox_id)
        supervisor_pid = self._start_sandbox_supervisor(state)
        rc, _out, err = self._run_compose(state, "up", "-d")
        if rc != 0:
            logger.warning("sandbox start failed: %s — %s", sandbox_id, err.strip())
            state = state.model_copy(update={"status": SandboxStatus.error, "supervisor_pid": supervisor_pid})
        else:
            # ProxyManager.register ensures reverse_proxy infra and
            # writes routes under resolve_proxy_routes_dir() (host-global).
            logger.info(
                "sandbox start: proxy routes dir=%s sandbox=%s",
                resolve_proxy_routes_dir(),
                sandbox_id,
            )
            urls = self._proxy.register(
                sandbox_id,
                state.ports,
                web_host=state.web_host,
                api_host=state.api_host,
            )
            state = state.model_copy(update={"status": SandboxStatus.running, "supervisor_pid": supervisor_pid, "urls": urls, "deployed_at": _now_iso()})
        self._write_state(state)
        return state

    def stop(self, sandbox_id: str) -> SandboxState:
        state = self._read_state(sandbox_id)
        self._terminate_sandbox_supervisor(state)
        rc, _out, err = self._run_compose(state, "down")
        if rc != 0:
            logger.warning("sandbox stop warning: %s — %s", sandbox_id, err.strip())
        if state.sandbox_runtime_root:
            runtime_root = Path(state.sandbox_runtime_root)
            for pattern in ("*.pid", "*.lock"):
                for stale in runtime_root.glob(pattern):
                    try:
                        stale.unlink()
                    except OSError:
                        pass
        state = state.model_copy(update={"status": SandboxStatus.stopped, "supervisor_pid": None, "stopped_at": _now_iso()})
        self._write_state(state)
        return state

    def restart(self, sandbox_id: str) -> SandboxState:
        self.stop(sandbox_id)
        return self.start(sandbox_id)

    def refresh(self, sandbox_id: str) -> SandboxState:
        return self._read_state(sandbox_id)

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

    def _start_sandbox_supervisor(self, state: SandboxState) -> int | None:
        """Spawn a per-sandbox supervisor subprocess. Returns PID or None on failure."""
        if not state.supervisor_port:
            return None
        runtime_root = Path(state.sandbox_runtime_root)
        runtime_root.mkdir(parents=True, exist_ok=True)
        for subdir in ("state", "logs", "runs"):
            (runtime_root / subdir).mkdir(exist_ok=True)
        env = {
            **os.environ,
            "AI_DEV_FACTORY_RUNTIME_ROOT": str(runtime_root),
            "PYTHONDONTWRITEBYTECODE": "1",
        }
        cmd = [
            sys.executable, "-m", "uvicorn",
            "services.supervisor.main:app",
            "--host", "127.0.0.1",
            "--port", str(state.supervisor_port),
        ]
        sup_log = runtime_root / "supervisor.log"
        try:
            with sup_log.open("a", encoding="utf-8") as fh:
                proc = subprocess.Popen(
                    cmd,
                    cwd=str(_REPO_ROOT),
                    env=env,
                    stdin=subprocess.DEVNULL,
                    stdout=fh,
                    stderr=fh,
                    start_new_session=True,
                )
            pid_path = runtime_root / "supervisor.pid"
            pid_path.write_text(
                json.dumps({"pid": proc.pid, "port": state.supervisor_port}),
                encoding="utf-8",
            )
            logger.info(
                "sandbox supervisor started: sandbox=%s pid=%d port=%d",
                state.id, proc.pid, state.supervisor_port,
            )
            return proc.pid
        except OSError as exc:
            logger.warning(
                "sandbox supervisor failed to start: sandbox=%s error=%s",
                state.id, exc,
            )
            return None

    def _terminate_sandbox_supervisor(self, state: SandboxState) -> None:
        """SIGTERM the sandbox supervisor process."""
        pid: int | None = state.supervisor_pid
        if pid is None and state.sandbox_runtime_root:
            pid_path = Path(state.sandbox_runtime_root) / "supervisor.pid"
            if pid_path.exists():
                try:
                    data = json.loads(pid_path.read_text(encoding="utf-8"))
                    pid = data.get("pid") if isinstance(data, dict) else int(data)
                except (OSError, ValueError, json.JSONDecodeError):
                    pass
        if not isinstance(pid, int):
            return
        try:
            os.kill(pid, signal.SIGTERM)
            logger.info("sandbox supervisor SIGTERM: sandbox=%s pid=%d", state.id, pid)
        except OSError:
            pass

    def destroy(self, sandbox_id: str) -> None:
        sandbox_dir = self._sandbox_dir(sandbox_id)
        try:
            state = self._read_state(sandbox_id)
        except SandboxNotFoundError:
            self._release_slot(sandbox_id)
            if sandbox_dir.exists():
                shutil.rmtree(sandbox_dir)
            return

        # 1. Terminate supervisor before undeploy to avoid interference.
        self._terminate_sandbox_supervisor(state)
        self._proxy.unregister(sandbox_id)

        # 2. Resolve project root for deploy profile lookup.
        worktree = Path(state.worktree_path) if state.worktree_path else None
        project_root = Path(state.project_root)
        cwd = worktree if (worktree and worktree.exists()) else project_root
        profile = _load_deploy_profile(cwd)

        runtime_root = (
            Path(state.sandbox_runtime_root) if state.sandbox_runtime_root else None
        )

        # 3. Stop runtime services via undeploy lifecycle.
        run_undeploy(
            profile,
            state.compose_project,
            state.env_file,
            cwd,
            sandbox_id,
        )

        # 4. Run cleanup hooks and remove stale pid/lock files.
        run_cleanup(profile, sandbox_dir, runtime_root, sandbox_id)

        # 5. Remove worktree after services are confirmed stopped.
        if state.worktree_path:
            subprocess.run(
                ["git", "worktree", "remove", "--force", state.worktree_path],
                capture_output=True, text=True, check=False,
            )

        # 6. Mark as destroyed before removing the directory.
        try:
            self._write_state(
                state.model_copy(
                    update={"status": SandboxStatus.destroyed, "supervisor_pid": None}
                )
            )
        except OSError:
            pass

        # 7. Release port slot only after undeploy completes.
        self._release_slot(sandbox_id)

        # 8. Remove sandbox directory.
        if sandbox_dir.exists():
            shutil.rmtree(sandbox_dir)

        logger.info("sandbox destroyed: %s", sandbox_id)

    def status(self, sandbox_id: str) -> SandboxState:
        state = self._read_state(sandbox_id)
        if state.status == SandboxStatus.running and state.supervisor_pid is not None:
            if not _pid_alive(state.supervisor_pid):
                state = state.model_copy(
                    update={"status": SandboxStatus.stopped, "supervisor_pid": None}
                )
                self._write_state(state)
        return state

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

    def cleanup_stale_routes(self) -> list[str]:
        """Remove proxy route files whose sandbox no longer exists.

        Safe to call at any time — only sandbox-prefixed files are
        considered, infra-owned ``_``-prefixed files (e.g. the
        Traefik dashboard route) are skipped. Returns the list of
        sandbox ids whose route files were removed.
        """
        active = [s.id for s in self.list()]
        return self._proxy.cleanup_stale_routes(active)

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
