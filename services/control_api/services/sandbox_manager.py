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
from .infra_service_manager import ensure_runtime_network, resolve_proxy_routes_dir
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
    def __init__(
        self,
        sandboxes_dir: Path | None = None,
        proxy_routes_dir: Path | None = None,
    ) -> None:
        if sandboxes_dir is None:
            sandboxes_dir = get_project_sandbox_dir()
        self.sandboxes_dir = sandboxes_dir
        self.sandboxes_dir.mkdir(parents=True, exist_ok=True)
        self._registry_path = self.sandboxes_dir / "port-registry.json"
        self._proxy = ProxyManager(
            routes_dir=proxy_routes_dir,
            auto_ensure_infra=proxy_routes_dir is None,
        )

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
        self.sandboxes_dir.mkdir(parents=True, exist_ok=True)
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

    # --- custom storage index (sandbox_id → absolute host path) ---

    def _storage_index_path(self) -> Path:
        return self.sandboxes_dir / ".sandbox-storage.json"

    def _read_storage_index(self) -> dict[str, str]:
        try:
            data = json.loads(self._storage_index_path().read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    def _write_storage_index(self, index: dict[str, str]) -> None:
        self.sandboxes_dir.mkdir(parents=True, exist_ok=True)
        self._storage_index_path().write_text(
            json.dumps(index, indent=2), encoding="utf-8"
        )

    def _register_storage_dir(self, sandbox_id: str, storage_dir: Path) -> None:
        with _registry_lock:
            index = self._read_storage_index()
            index[sandbox_id] = str(storage_dir)
            self._write_storage_index(index)

    def _unregister_storage_dir(self, sandbox_id: str) -> None:
        with _registry_lock:
            index = self._read_storage_index()
            if sandbox_id in index:
                index.pop(sandbox_id, None)
                self._write_storage_index(index)

    def _ensure_storage_dir(
        self, sandbox_id: str, sandbox_path: str | None
    ) -> tuple[Path, str | None]:
        """Create the sandbox storage directory before any file writes.

        Returns ``(storage_dir, sandbox_dir_field)`` where *sandbox_dir_field*
        is persisted on :class:`SandboxState` when the path is user-specified.
        """
        self.sandboxes_dir.mkdir(parents=True, exist_ok=True)
        if sandbox_path:
            storage = Path(sandbox_path).expanduser().resolve()
            storage.mkdir(parents=True, exist_ok=True)
            self._register_storage_dir(sandbox_id, storage)
            return storage, str(storage)
        storage = self.sandboxes_dir / sandbox_id
        storage.mkdir(parents=True, exist_ok=True)
        return storage, None

    # --- state helpers ---

    def _storage_dir_for_state(self, state: SandboxState) -> Path:
        if state.sandbox_dir:
            return Path(state.sandbox_dir)
        return self.sandboxes_dir / state.id

    def _storage_dir(self, sandbox_id: str) -> Path:
        indexed = self._read_storage_index().get(sandbox_id)
        if indexed:
            return Path(indexed)
        return self.sandboxes_dir / sandbox_id

    def _sandbox_dir(self, sandbox_id: str) -> Path:
        return self._storage_dir(sandbox_id)

    def _state_path(self, sandbox_id: str) -> Path:
        return self._storage_dir(sandbox_id) / "state.json"

    def _env_file_path(self, sandbox_id: str) -> Path:
        return self._storage_dir(sandbox_id) / ".env"

    def _runtime_root_path(self, sandbox_id: str) -> Path:
        return self._storage_dir(sandbox_id) / "runtime"

    def _state_file_candidates(self, sandbox_id: str) -> list[Path]:
        candidates: list[Path] = []
        indexed = self._read_storage_index().get(sandbox_id)
        if indexed:
            candidates.append(Path(indexed) / "state.json")
        default = self.sandboxes_dir / sandbox_id / "state.json"
        if default not in candidates:
            candidates.append(default)
        return candidates

    def _read_state(self, sandbox_id: str) -> SandboxState:
        for path in self._state_file_candidates(sandbox_id):
            if path.exists():
                return SandboxState.model_validate_json(
                    path.read_text(encoding="utf-8")
                )
        raise SandboxNotFoundError(f"sandbox not found: {sandbox_id}")

    def _write_state(self, state: SandboxState) -> None:
        storage = self._storage_dir_for_state(state)
        storage.mkdir(parents=True, exist_ok=True)
        path = storage / "state.json"
        path.write_text(state.model_dump_json(indent=2), encoding="utf-8")

    # --- compose helper ---

    def _run_compose(self, sandbox: SandboxState, *args: str) -> tuple[int, str, str]:
        sandbox_env_file = str(self._env_file_path(sandbox.id))
        deploy_env = Path(sandbox.project_root) / "deploy" / ".env"

        env_files: list[str] = []
        if deploy_env.exists():
            env_files.append(str(deploy_env))
        env_files.append(sandbox_env_file)

        cmd_base = ["docker", "compose", "-p", sandbox.compose_project]
        for ef in env_files:
            cmd_base += ["--env-file", ef]

        logger.info(
            "sandbox compose: sandbox=%s SANDBOX_ID=%s env_files=[%s] project=%s",
            sandbox.id, sandbox.id, ", ".join(env_files), sandbox.compose_project,
        )

        # Pre-flight config validation before 'up' — catches alias mismatch
        # before any container is created.
        if args and args[0] == "up":
            config_result = subprocess.run(
                cmd_base + ["config"],
                capture_output=True,
                text=True,
                cwd=sandbox.project_root,
                check=False,
            )
            expected_alias = f"sandbox-{sandbox.id}-"
            if expected_alias not in config_result.stdout:
                alias_lines = "\n".join(
                    line for line in config_result.stdout.splitlines() if "sandbox-" in line
                )
                logger.warning(
                    "sandbox compose config alias mismatch: sandbox=%s expected=%s aliases:\n%s",
                    sandbox.id, expected_alias, alias_lines or "(none)",
                )
                return 1, "", (
                    f"compose config alias mismatch: expected {expected_alias}, found:\n"
                    + (alias_lines or "(none)")
                )
            logger.info(
                "sandbox compose config ok: sandbox=%s alias=%s", sandbox.id, expected_alias
            )

        cmd = cmd_base + list(args)
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
        sandbox_path: str | None = None,
    ) -> SandboxState:
        sandbox_id = uuid.uuid4().hex[:12]
        storage_dir, sandbox_dir_field = self._ensure_storage_dir(
            sandbox_id, sandbox_path
        )
        slot = self._allocate_slot(sandbox_id)

        compose_project = normalize_compose_project_name(f"sandbox-{sandbox_id}")
        web_port = _BASE_WEB_PORT + slot * _PORT_STEP
        api_port = _BASE_API_PORT + slot * _PORT_STEP
        supervisor_port = 8090 + slot
        ports: dict[str, int] = {"web": web_port, "api": api_port}

        env_file = storage_dir / ".env"
        sandbox_runtime_root = str(storage_dir / "runtime")

        # Pre-compute the pretty URLs. Custom hosts (if provided) are used
        # verbatim; otherwise the default sandbox-<id>.* pattern applies.
        urls = build_sandbox_urls(sandbox_id, web_host=web_host, api_host=api_host)
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
            sandbox_dir=sandbox_dir_field,
        )
        self._write_state(state)
        logger.info(
            "sandbox created: %s (slot=%d storage=%s ports=%s)",
            sandbox_id, slot, storage_dir, ports,
        )
        return state

    def start(self, sandbox_id: str) -> SandboxState:
        state = self._read_state(sandbox_id)
        ensure_runtime_network()
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
        runtime_root = self._runtime_root_path(sandbox_id)
        if runtime_root.exists():
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

    def create_with_source(
        self,
        ticket_id: str,
        project_root: str,
        branch: str | None = None,
        job_type: str = "deploy",
    ) -> SandboxState:
        state = self.create(ticket_id, project_root)
        source_path = self._sandbox_dir(state.id) / "source"

        requested_ref: str | None = None
        commit_sha: str | None = None

        clone_cmd = ["git", "clone"]
        if branch:
            requested_ref = branch
            clone_cmd.extend(["--branch", branch])
        clone_cmd.extend([project_root, str(source_path)])

        logger.info(
            "sandbox source: cloning repo branch=%s source=%s sandbox=%s",
            branch or "(default)", source_path, state.id,
        )
        clone_result = subprocess.run(
            clone_cmd, capture_output=True, text=True, check=False,
        )
        if clone_result.returncode != 0:
            self.destroy(state.id)
            raise RuntimeError(
                f"git clone failed: {clone_result.stderr.strip()}"
            )

        if branch:
            branch_result = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True, text=True, check=False, cwd=str(source_path),
            )
            actual_branch = branch_result.stdout.strip()
            if actual_branch != branch:
                self.destroy(state.id)
                raise RuntimeError(
                    f"branch mismatch after clone: expected {branch!r}, got {actual_branch!r}"
                )

        commit_result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, check=False, cwd=str(source_path),
        )
        commit_sha = commit_result.stdout.strip() or None

        logger.info(
            "sandbox source ready: %s job_type=%s branch=%s commit=%s path=%s",
            state.id, job_type, branch, commit_sha, source_path,
        )
        state = state.model_copy(
            update={
                "source_path": str(source_path),
                "job_type": job_type,
                "requested_ref": requested_ref,
                "resolved_ref": requested_ref,
                "commit_sha": commit_sha,
            }
        )
        self._write_state(state)
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
        runtime_root = self._runtime_root_path(state.id)
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
        if pid is None:
            pid_path = self._runtime_root_path(state.id) / "supervisor.pid"
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
            self._unregister_storage_dir(sandbox_id)
            if sandbox_dir.exists():
                shutil.rmtree(sandbox_dir)
            return

        # 1. Terminate supervisor before undeploy to avoid interference.
        self._terminate_sandbox_supervisor(state)
        self._proxy.unregister(
            sandbox_id,
            remove_route_file=True,
        )

        # 2. Resolve project root for deploy profile lookup.
        source = Path(state.source_path) if state.source_path else None
        legacy_worktree = Path(state.worktree_path) if state.worktree_path else None
        project_root = Path(state.project_root)
        cwd = (
            source if (source and source.exists()) else
            legacy_worktree if (legacy_worktree and legacy_worktree.exists()) else
            project_root
        )
        profile = _load_deploy_profile(cwd)

        runtime_root = self._runtime_root_path(sandbox_id)

        # 3. Stop runtime services via undeploy lifecycle.
        run_undeploy(
            profile,
            state.compose_project,
            str(self._env_file_path(sandbox_id)),
            cwd,
            sandbox_id,
        )

        # 4. Run cleanup hooks and remove stale pid/lock files.
        run_cleanup(profile, sandbox_dir, runtime_root, sandbox_id)

        # 5. Remove source directory after services are confirmed stopped.
        if state.source_path:
            source_dir = Path(state.source_path)
            if source_dir.exists():
                shutil.rmtree(source_dir)
        elif state.worktree_path:
            # Legacy: remove old-style git worktrees.
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
        self._unregister_storage_dir(sandbox_id)

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
        sandbox_dir = self._storage_dir(sandbox_id)
        if state.env_name is not None:
            from .sandbox_runtime_deploy import format_environment_logs

            return format_environment_logs(
                sandbox_dir, state, docker_component=component
            )
        cmd = [
            "docker", "compose",
            "-p", state.compose_project,
            "--env-file", str(self._env_file_path(sandbox_id)),
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
        seen: set[str] = set()
        sandboxes: list[SandboxState] = []
        state_files: list[Path] = list(self.sandboxes_dir.glob("*/state.json"))
        for storage in self._read_storage_index().values():
            candidate = Path(storage) / "state.json"
            if candidate not in state_files:
                state_files.append(candidate)
        for state_file in sorted(state_files):
            try:
                state = SandboxState.model_validate_json(
                    state_file.read_text(encoding="utf-8")
                )
            except Exception:
                continue
            if state.id in seen:
                continue
            seen.add(state.id)
            sandboxes.append(state)
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
