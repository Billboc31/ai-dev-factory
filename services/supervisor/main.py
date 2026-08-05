"""Host-side supervisor — manages the AI dev factory daemon on the host.

Binds to 127.0.0.1:8090 (localhost only). No auth — localhost trust.
Start via deploy/start_supervisor.sh.
"""

from __future__ import annotations

import asyncio
import datetime
import json
import logging
import os
import signal
import subprocess
import sys
import threading
import uuid
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path

from fastapi import FastAPI, Query
from pydantic import BaseModel, Field

# Optional sandbox support — gracefully disabled when the control_api package
# is not importable (e.g. in isolated test environments).
_project_root_dir = Path(__file__).resolve().parents[2]
if str(_project_root_dir) not in sys.path:
    sys.path.insert(0, str(_project_root_dir))

try:
    from services.control_api.services.sandbox_manager import SandboxManager as _SandboxManager
    _sandbox_manager: _SandboxManager | None = _SandboxManager()
except Exception:
    _SandboxManager = None  # type: ignore[assignment,misc]
    _sandbox_manager = None

logger = logging.getLogger("supervisor")

_SUPERVISOR_DIR = Path(__file__).resolve().parent
if str(_SUPERVISOR_DIR) not in sys.path:
    sys.path.insert(0, str(_SUPERVISOR_DIR))

from path_mapper import ContainerToHostMapper  # noqa: E402
from recovery import (  # noqa: E402
    BlockerClass,
    RecoveryResult,
    RecoverySession,
    RecoveryStage,
    ProposalStatus,
    MAX_RECOVERY_ITERATIONS,
    ALLOWLISTED_RECOVERY_OPS,
    apply_recovery_op,
    build_recovery_plan,
    classify_blocker,
    compute_bug_signature,
    compute_state_fingerprint,
    create_bug_issue,
    search_existing_bug_issues,
    verify_ticket_progress,
    _artifact_paths_for_ticket,
    _ticket_run_dir,
    _TERMINAL_TICKET_STATES,
)

mapper = ContainerToHostMapper()

_PID_FILENAME = "daemon.pid"
_LOG_FILENAME = "daemon.log"


# ── Path helpers ──────────────────────────────────────────────────────────────

def _project_root() -> Path:
    return Path(os.environ.get("AI_DEV_FACTORY_PROJECT_ROOT", Path.cwd()))


def _runtime_root() -> Path:
    """Canonical host runtime root used by sandbox workers and other jobs.

    Mirrors the logic baked into the per-subsystem helpers below so that
    log statements can reference a single, consistent value.
    """
    rr = os.environ.get("AI_DEV_FACTORY_RUNTIME_ROOT")
    if rr:
        return Path(rr)
    return _project_root() / ".ai-dev-factory"


def _runtime_base_root() -> Path:
    """Parent directory containing one runtime root per managed project.

    Used only by multi-project operations (bootstrap, per-project daemons), so
    it is safe to raise here — this is never reached during plain startup.

    Resolution order:
    1. RUNTIME_BASE_ROOT env var (explicit config) — rejected only if it
       resolves to '/'.
    2. Parent of AI_DEV_FACTORY_RUNTIME_ROOT, but only when that parent is not
       '/'. We never accept '/' derived from e.g. AI_DEV_FACTORY_RUNTIME_ROOT=/runtime.
    3. ~/runtime (safe local fallback) when no env is configured at all.

    Raises a clear configuration error when a base is required but cannot be
    resolved (e.g. AI_DEV_FACTORY_RUNTIME_ROOT=/runtime with no RUNTIME_BASE_ROOT).
    """
    base = os.environ.get("RUNTIME_BASE_ROOT")
    if base:
        result = Path(base).expanduser().resolve()
        if result == Path("/"):
            raise RuntimeError(
                "RUNTIME_BASE_ROOT resolves to filesystem root '/' — check environment configuration"
            )
        return result
    factory_root = os.environ.get("AI_DEV_FACTORY_RUNTIME_ROOT")
    if factory_root:
        parent = Path(factory_root).expanduser().resolve().parent
        if parent != Path("/"):
            return parent
        raise RuntimeError(
            "RUNTIME_BASE_ROOT is not configured and cannot be derived from "
            f"AI_DEV_FACTORY_RUNTIME_ROOT={factory_root!r} (parent is '/'). "
            "Set RUNTIME_BASE_ROOT explicitly for multi-project operations."
        )
    return Path.home() / "runtime"


def _runs_dir() -> Path:
    runtime_root = os.environ.get("AI_DEV_FACTORY_RUNTIME_ROOT")
    if runtime_root:
        return Path(runtime_root) / "runs"
    return _project_root() / "runs"


def _logs_dir() -> Path:
    runtime_root = os.environ.get("AI_DEV_FACTORY_RUNTIME_ROOT")
    if runtime_root:
        return Path(runtime_root) / "logs"
    return _project_root() / "logs"


def _worktrees_dir() -> Path:
    runtime_root = os.environ.get("AI_DEV_FACTORY_RUNTIME_ROOT")
    if runtime_root:
        return Path(runtime_root) / "worktrees"
    root = _project_root()
    return root.parent / (root.name + "-worktrees")


def _state_dir() -> Path:
    runtime_root = os.environ.get("AI_DEV_FACTORY_RUNTIME_ROOT")
    if runtime_root:
        return Path(runtime_root) / "state"
    return _project_root() / "state"


def _run_daemon_path() -> Path:
    return Path(__file__).resolve().parents[2] / "tools" / "agent_runner" / "run_daemon.py"


def _run_analysis_path() -> Path:
    return Path(__file__).resolve().parents[2] / "tools" / "agent_runner" / "run_analysis.py"


def _run_scripts_path() -> Path:
    return Path(__file__).resolve().parents[2] / "tools" / "agent_runner" / "run_scripts.py"


def _run_sandbox_path() -> Path:
    return Path(__file__).resolve().parents[2] / "tools" / "agent_runner" / "run_sandbox.py"


def _pid_path() -> Path:
    return _runs_dir() / _PID_FILENAME


def _log_path() -> Path:
    return _logs_dir() / _LOG_FILENAME


# ── PID file helpers ──────────────────────────────────────────────────────────

def _read_pid_file() -> dict | None:
    path = _pid_path()
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _write_pid_file(pid: int, started_at: str, exec_cmd: str = "", restart_policy: str = "no-restart") -> None:
    path = _pid_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"pid": pid, "started_at": started_at, "exec_cmd": exec_cmd, "restart_policy": restart_policy}),
        encoding="utf-8",
    )


def _remove_pid_file() -> None:
    try:
        _pid_path().unlink()
    except OSError:
        pass


def _is_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


# ── Daemon in-memory state ────────────────────────────────────────────────────

@dataclass
class DaemonState:
    pid: int | None = None
    started_at: str | None = None
    last_exit_code: int | None = None
    last_exit_time: str | None = None
    last_error: str | None = None
    restart_count: int = 0
    restart_policy: str = "no-restart"
    exit_unexpected: bool = False


_daemon_state = DaemonState()
_daemon_proc: subprocess.Popen | None = None
_voluntary_stop: bool = False
_daemon_exec_cmd: str = os.environ.get(
    "DAEMON_EXEC_CMD",
    "claude --dangerously-skip-permissions --model sonnet",
)


# ── Daemon spawn helper ───────────────────────────────────────────────────────

def _spawn_daemon(exec_cmd: str) -> tuple[int | None, str | None, str | None]:
    """Spawn the daemon. Returns (pid, started_at, error_str)."""
    global _daemon_proc
    started_at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    log = _log_path()
    log.parent.mkdir(parents=True, exist_ok=True)
    _legacy_project = os.environ.get("PROJECT_NAME")
    cmd = [
        sys.executable,
        str(_run_daemon_path()),
        "--exec-cmd", exec_cmd,
        "--poll-issues",
        "--issue-label", "ai-ready",
        "--auto-commit",
        "--auto-push",
        "--auto-include-code",
        "--worktrees-dir", str(_worktrees_dir()),
    ]
    if _legacy_project:
        cmd += ["--project", _legacy_project]
    tools_dir = _project_root_dir / "tools" / "agent_runner"
    if str(tools_dir) not in sys.path:
        sys.path.insert(0, str(tools_dir))
    import runtime_settings as _runtime_settings  # noqa: E402

    cmd += _runtime_settings.daemon_max_workers_argv_for_project(_legacy_project)
    try:
        # Daemon inherits the supervisor env (incl. RUNTIME_DB_* from deploy/.env)
        # so it shares the same runtime DB backend as the API — no split-brain.
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
        with open(log, "a", encoding="utf-8") as log_fh:
            log_fh.write(
                f"[{started_at}] supervisor spawning daemon\n"
                f"  command={' '.join(cmd)}\n"
            )
            log_fh.flush()
            proc = subprocess.Popen(
                cmd,
                cwd=str(_project_root()),
                stdout=log_fh,
                stderr=log_fh,
                start_new_session=True,
                env=env,
            )
        _daemon_proc = proc
        _write_pid_file(proc.pid, started_at, exec_cmd, _daemon_state.restart_policy)
        logger.info("supervisor: daemon started pid=%d", proc.pid)
        return proc.pid, started_at, None
    except OSError as exc:
        return None, None, str(exc)


# ── Monitor ───────────────────────────────────────────────────────────────────

def _check_and_maybe_restart() -> None:
    """Single monitor cycle: detect daemon exit, update state, restart if policy says so."""
    global _daemon_proc, _voluntary_stop
    if _daemon_state.pid is None:
        return
    if _is_alive(_daemon_state.pid):
        return

    # Process is gone — record exit info
    exit_code: int | None = None
    if _daemon_proc is not None:
        exit_code = _daemon_proc.poll()

    now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    _daemon_state.last_exit_code = exit_code
    _daemon_state.last_exit_time = now
    _daemon_state.last_error = f"process exited with code {exit_code}"
    _daemon_state.exit_unexpected = not _voluntary_stop
    if _voluntary_stop:
        _voluntary_stop = False

    old_pid = _daemon_state.pid
    _daemon_state.pid = None
    _daemon_proc = None
    _remove_pid_file()

    logger.info(
        "supervisor: daemon pid=%d exited (code=%s, unexpected=%s)",
        old_pid, exit_code, _daemon_state.exit_unexpected,
    )

    if _daemon_state.exit_unexpected and _daemon_state.restart_policy == "restart-on-crash":
        _daemon_state.restart_count += 1
        logger.info(
            "supervisor: restart-on-crash — respawning (attempt=%d)",
            _daemon_state.restart_count,
        )
        pid, started_at, err = _spawn_daemon(_daemon_exec_cmd)
        if pid is not None:
            _daemon_state.pid = pid
            _daemon_state.started_at = started_at
            _daemon_state.exit_unexpected = False
        else:
            _daemon_state.last_error = err


async def _monitor_daemon() -> None:
    while True:
        await asyncio.sleep(5)
        _check_and_maybe_restart()


# ── FastAPI lifespan ──────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _daemon_exec_cmd
    # Initialise in-memory state from PID file so a supervisor restart
    # reconnects to a live daemon, and cleans up stale PID files.
    data = _read_pid_file()
    if data is not None:
        pid = data.get("pid")
        if isinstance(pid, int):
            if _is_alive(pid):
                _daemon_state.pid = pid
                _daemon_state.started_at = data.get("started_at")
                _daemon_exec_cmd = data.get("exec_cmd", _daemon_exec_cmd)
                _daemon_state.restart_policy = data.get("restart_policy", "no-restart")
            else:
                _remove_pid_file()

    task = asyncio.create_task(_monitor_daemon())
    yield
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


# ── sandbox cleanup helper ────────────────────────────────────────────────────

def _destroy_sandbox_after_proc(proc: subprocess.Popen, sandbox_id: str) -> None:
    """Wait for *proc* to exit, then destroy its sandbox. Run in a daemon thread."""
    try:
        proc.wait()
    except Exception:
        pass
    if _sandbox_manager is None:
        return
    try:
        _sandbox_manager.destroy(sandbox_id)
        logger.info("supervisor: sandbox destroyed after subprocess: %s", sandbox_id)
    except Exception as exc:
        logger.warning("supervisor: sandbox cleanup failed for %s: %s", sandbox_id, exc)


# ── analysis per-project locking ──────────────────────────────────────────────

_analysis_locks: dict[str, threading.Lock] = {}
_analysis_locks_mutex = threading.Lock()


def _get_analysis_lock(project_id: str) -> threading.Lock:
    with _analysis_locks_mutex:
        if project_id not in _analysis_locks:
            _analysis_locks[project_id] = threading.Lock()
        return _analysis_locks[project_id]


def _get_redeploy_lock(project_id: str) -> threading.Lock:
    with _workspace_redeploy_locks_mutex:
        if project_id not in _workspace_redeploy_locks:
            _workspace_redeploy_locks[project_id] = threading.Lock()
        return _workspace_redeploy_locks[project_id]


def _analysis_pid_path(project_id: str) -> Path:
    return _runs_dir() / f"analysis-{project_id}.pid"


def _analysis_log_path(project_id: str) -> Path:
    d = _logs_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d / f"analysis-{project_id}.log"


def _analysis_state_path(project_id: str) -> Path:
    d = _state_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d / f"analysis-{project_id}.json"


def _read_analysis_state(project_id: str) -> dict:
    path = _analysis_state_path(project_id)
    if not path.exists():
        return {"state": "idle"}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"state": "idle"}


def _analysis_current_pid(project_id: str) -> int | None:
    path = _analysis_pid_path(project_id)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    pid = data.get("pid")
    if not isinstance(pid, int):
        return None
    if not _is_alive(pid):
        try:
            path.unlink()
        except OSError:
            pass
        return None
    return pid


# ── scripts per-project locking ───────────────────────────────────────────────

_scripts_locks: dict[str, threading.Lock] = {}
_scripts_locks_mutex = threading.Lock()


def _get_scripts_lock(project_id: str) -> threading.Lock:
    with _scripts_locks_mutex:
        if project_id not in _scripts_locks:
            _scripts_locks[project_id] = threading.Lock()
        return _scripts_locks[project_id]


# ── sandbox per-project locking ───────────────────────────────────────────────
#
# Mirrors the scripts/analysis pattern: one lock per project_id, plus a PID
# file under runs/ so a supervisor restart can re-bind to a live worker. The
# worker itself (tools/agent_runner/run_sandbox.py) writes the state file
# under state/sandbox-{project_id}.json and a per-run log under
# sandboxes/{sandbox_id}/run.log.

_sandbox_locks: dict[str, threading.Lock] = {}
_sandbox_locks_mutex = threading.Lock()


def _get_sandbox_lock(project_id: str) -> threading.Lock:
    with _sandbox_locks_mutex:
        if project_id not in _sandbox_locks:
            _sandbox_locks[project_id] = threading.Lock()
        return _sandbox_locks[project_id]


def _sandbox_pid_path(project_id: str) -> Path:
    return _runs_dir() / f"sandbox-{project_id}.pid"


def _sandbox_log_path(project_id: str) -> Path:
    d = _logs_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d / f"sandbox-{project_id}.log"


def _sandbox_state_path(project_id: str) -> Path:
    d = _state_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d / f"sandbox-{project_id}.json"


def _read_sandbox_state(project_id: str) -> dict:
    path = _sandbox_state_path(project_id)
    if not path.exists():
        return {"state": "idle"}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"state": "idle"}


def _sandbox_current_pid(project_id: str) -> int | None:
    path = _sandbox_pid_path(project_id)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    pid = data.get("pid")
    if not isinstance(pid, int):
        return None
    if not _is_alive(pid):
        try:
            path.unlink()
        except OSError:
            pass
        return None
    return pid


def _scripts_pid_path(project_id: str) -> Path:
    return _runs_dir() / f"scripts-{project_id}.pid"


def _scripts_log_path(project_id: str) -> Path:
    d = _logs_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d / f"scripts-{project_id}.log"


def _scripts_state_path(project_id: str) -> Path:
    d = _state_dir()
    d.mkdir(parents=True, exist_ok=True)
    return d / f"scripts-{project_id}.json"


def _read_scripts_state(project_id: str) -> dict:
    path = _scripts_state_path(project_id)
    if not path.exists():
        return {"state": "idle"}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"state": "idle"}


def _scripts_current_pid(project_id: str) -> int | None:
    path = _scripts_pid_path(project_id)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    pid = data.get("pid")
    if not isinstance(pid, int):
        return None
    if not _is_alive(pid):
        try:
            path.unlink()
        except OSError:
            pass
        return None
    return pid


app = FastAPI(title="AI Dev Factory Supervisor", version="1.0.0")


@app.get("/health")
def health():
    pid = _daemon_state.pid
    return {"status": "ok", "daemon_pid": pid if (pid and _is_alive(pid)) else None}


@app.get("/supervisor/status")
def supervisor_status():
    return {
        "container_runtime_root": mapper.container_root or None,
        "host_runtime_root": mapper.host_root or None,
    }


@app.get("/daemon/status")
def daemon_status():  # noqa: C901
    global _daemon_exec_cmd
    pid = _daemon_state.pid

    if pid is not None and not _is_alive(pid):
        # Process died between monitor cycles — clean up PID file proactively.
        # The monitor will update exit_unexpected etc. on its next cycle.
        _remove_pid_file()
        running = False
        pid = None
    elif pid is None:
        # No in-memory state: check the PID file for live processes or stale
        # entries (handles fresh supervisor start and stale PID recovery).
        data = _read_pid_file()
        if data is not None:
            file_pid = data.get("pid")
            if isinstance(file_pid, int) and _is_alive(file_pid):
                _daemon_state.pid = file_pid
                _daemon_state.started_at = data.get("started_at")
                _daemon_exec_cmd = data.get("exec_cmd", _daemon_exec_cmd)
                _daemon_state.restart_policy = data.get("restart_policy", "no-restart")
                pid = file_pid
                running = True
            else:
                _remove_pid_file()
                running = False
        else:
            running = False
    else:
        running = True

    return {
        "running": running,
        "pid": pid,
        "started_at": _daemon_state.started_at,
        "last_exit_code": _daemon_state.last_exit_code,
        "last_exit_time": _daemon_state.last_exit_time,
        "last_error": _daemon_state.last_error,
        "exit_unexpected": _daemon_state.exit_unexpected,
        "restart_count": _daemon_state.restart_count,
        "restart_policy": _daemon_state.restart_policy,
    }


class StartRequest(BaseModel):
    exec_cmd: str = "claude --dangerously-skip-permissions"
    restart_policy: str = "no-restart"


@app.post("/daemon/start")
def daemon_start(body: StartRequest = None):  # noqa: B008
    global _daemon_exec_cmd
    if body is None:
        body = StartRequest()

    pid = _daemon_state.pid
    if pid is not None and _is_alive(pid):
        return {"ok": False, "pid": pid, "error": "already_running"}

    _daemon_state.restart_policy = body.restart_policy
    _daemon_exec_cmd = body.exec_cmd

    pid, started_at, err = _spawn_daemon(body.exec_cmd)
    if pid is None:
        return {"ok": False, "pid": None, "error": err}

    _daemon_state.pid = pid
    _daemon_state.started_at = started_at
    _daemon_state.exit_unexpected = False
    return {"ok": True, "pid": pid}


@app.post("/daemon/stop")
def daemon_stop():
    global _voluntary_stop
    pid = _daemon_state.pid
    if pid is None or not _is_alive(pid):
        _remove_pid_file()
        return {"ok": False, "error": "not_running"}

    _voluntary_stop = True
    try:
        os.kill(pid, signal.SIGTERM)
        _daemon_state.pid = None
        _daemon_state.started_at = None
        _remove_pid_file()
        logger.info("supervisor: daemon stopped pid=%d", pid)
        return {"ok": True}
    except OSError as exc:
        _voluntary_stop = False
        return {"ok": False, "error": str(exc)}


# ── analysis endpoints ────────────────────────────────────────────────────────

class AnalysisStartRequest(BaseModel):
    project_root: str
    project_id: str
    exec_cmd: str = "claude --dangerously-skip-permissions"


@app.post("/analysis/start")
def analysis_start(body: AnalysisStartRequest):
    from fastapi.responses import JSONResponse

    lock = _get_analysis_lock(body.project_id)
    if not lock.acquire(blocking=False):
        return JSONResponse(status_code=409, content={"ok": False, "error": "locked"})

    try:
        if _analysis_current_pid(body.project_id) is not None:
            return JSONResponse(status_code=409, content={"ok": False, "error": "locked"})

        mapped_root = mapper.map(body.project_root)
        logger.info(
            "supervisor: analysis start project_id=%s project_root=%r -> %r",
            body.project_id, body.project_root, mapped_root,
        )

        started_at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        log = _analysis_log_path(body.project_id)
        cmd = [
            sys.executable,
            str(_run_analysis_path()),
            "--project-root", mapped_root,
            "--project-id", body.project_id,
            "--exec-cmd", body.exec_cmd,
            "--worktrees-dir", str(_worktrees_dir()),
        ]
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}

        # Create an isolated worktree sandbox for this analysis job.
        sandbox = None
        if _sandbox_manager is not None:
            try:
                sandbox = _sandbox_manager.create_with_worktree(
                    ticket_id=body.project_id,
                    project_root=body.project_root,
                    branch=None,
                    job_type="analysis",
                )
                env["SANDBOX_ID"] = sandbox.id
                env["SANDBOX_WORKTREE"] = sandbox.worktree_path or ""
                logger.info(
                    "supervisor: analysis sandbox created %s for project_id=%s",
                    sandbox.id, body.project_id,
                )
            except Exception as exc:
                logger.warning(
                    "supervisor: sandbox creation failed for analysis %s: %s — continuing without sandbox",
                    body.project_id, exc,
                )
                sandbox = None

        try:
            with open(log, "a", encoding="utf-8") as log_fh:
                log_fh.write(
                    f"[{started_at}] supervisor spawning analysis for {body.project_id}\n"
                    f"  project_root={body.project_root} -> {mapped_root}\n"
                )
                log_fh.flush()
                proc = subprocess.Popen(
                    cmd,
                    cwd=str(_project_root()),
                    stdout=log_fh,
                    stderr=log_fh,
                    start_new_session=True,
                    env=env,
                )
            pid_path = _analysis_pid_path(body.project_id)
            pid_path.parent.mkdir(parents=True, exist_ok=True)
            pid_path.write_text(
                json.dumps({"pid": proc.pid, "started_at": started_at}),
                encoding="utf-8",
            )
            logger.info("supervisor: analysis started pid=%d project_id=%s", proc.pid, body.project_id)
            if sandbox is not None:
                threading.Thread(
                    target=_destroy_sandbox_after_proc,
                    args=(proc, sandbox.id),
                    daemon=True,
                ).start()
            return {"ok": True, "pid": proc.pid}
        except OSError as exc:
            if sandbox is not None:
                try:
                    _sandbox_manager.destroy(sandbox.id)
                except Exception:
                    pass
            return {"ok": False, "error": str(exc)}
    finally:
        lock.release()


@app.get("/analysis/{project_id}/status")
def analysis_status(project_id: str):
    state = _read_analysis_state(project_id)
    if state.get("state") == "running":
        if _analysis_current_pid(project_id) is None:
            state["state"] = "failed"
            state["error"] = "analysis process disappeared"
            state["finished_at"] = datetime.datetime.now(datetime.timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )
            _analysis_state_path(project_id).write_text(
                json.dumps(state, indent=2), encoding="utf-8"
            )
            try:
                _analysis_pid_path(project_id).unlink()
            except OSError:
                pass
    return state


@app.get("/analysis/{project_id}/logs")
def analysis_logs(project_id: str, lines: int = Query(default=100, ge=1, le=10000)):
    log_path = _analysis_log_path(project_id)
    if not log_path.exists():
        return {"lines": []}
    text = log_path.read_text(encoding="utf-8")
    all_lines = text.splitlines()
    return {"lines": all_lines[-lines:] if len(all_lines) > lines else all_lines}


@app.post("/analysis/{project_id}/stop")
def analysis_stop(project_id: str):
    pid = _analysis_current_pid(project_id)
    if pid is None:
        return {"ok": False, "error": "not_running"}
    try:
        os.kill(pid, signal.SIGTERM)
        try:
            _analysis_pid_path(project_id).unlink()
        except OSError:
            pass
        logger.info("supervisor: analysis stopped pid=%d project_id=%s", pid, project_id)
        return {"ok": True}
    except OSError as exc:
        return {"ok": False, "error": str(exc)}


# ── scripts endpoints ─────────────────────────────────────────────────────────

class ScriptsStartRequest(BaseModel):
    project_root: str
    project_id: str
    exec_cmd: str = "claude --dangerously-skip-permissions"


@app.post("/scripts/start")
def scripts_start(body: ScriptsStartRequest):
    from fastapi.responses import JSONResponse

    lock = _get_scripts_lock(body.project_id)
    if not lock.acquire(blocking=False):
        return JSONResponse(status_code=409, content={"ok": False, "error": "locked"})

    try:
        if _scripts_current_pid(body.project_id) is not None:
            return JSONResponse(status_code=409, content={"ok": False, "error": "locked"})

        started_at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        log = _scripts_log_path(body.project_id)
        cmd = [
            sys.executable,
            str(_run_scripts_path()),
            "--project-root", body.project_root,
            "--project-id", body.project_id,
            "--exec-cmd", body.exec_cmd,
        ]
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}

        # Create an isolated worktree sandbox for this scripts generation job.
        sandbox = None
        if _sandbox_manager is not None:
            try:
                sandbox = _sandbox_manager.create_with_worktree(
                    ticket_id=body.project_id,
                    project_root=body.project_root,
                    branch=None,
                    job_type="scripts",
                )
                env["SANDBOX_ID"] = sandbox.id
                env["SANDBOX_WORKTREE"] = sandbox.worktree_path or ""
                logger.info(
                    "supervisor: scripts sandbox created %s for project_id=%s",
                    sandbox.id, body.project_id,
                )
            except Exception as exc:
                logger.warning(
                    "supervisor: sandbox creation failed for scripts %s: %s — continuing without sandbox",
                    body.project_id, exc,
                )
                sandbox = None

        try:
            with open(log, "a", encoding="utf-8") as log_fh:
                log_fh.write(
                    f"[{started_at}] supervisor spawning scripts generation for {body.project_id}\n"
                    f"  project_root={body.project_root}\n"
                )
                log_fh.flush()
                proc = subprocess.Popen(
                    cmd,
                    cwd=str(_project_root()),
                    stdout=log_fh,
                    stderr=log_fh,
                    start_new_session=True,
                    env=env,
                )
            pid_path = _scripts_pid_path(body.project_id)
            pid_path.parent.mkdir(parents=True, exist_ok=True)
            pid_path.write_text(
                json.dumps({"pid": proc.pid, "started_at": started_at}),
                encoding="utf-8",
            )
            logger.info("supervisor: scripts started pid=%d project_id=%s", proc.pid, body.project_id)
            if sandbox is not None:
                threading.Thread(
                    target=_destroy_sandbox_after_proc,
                    args=(proc, sandbox.id),
                    daemon=True,
                ).start()
            return {"ok": True, "pid": proc.pid}
        except OSError as exc:
            if sandbox is not None:
                try:
                    _sandbox_manager.destroy(sandbox.id)
                except Exception:
                    pass
            return {"ok": False, "error": str(exc)}
    finally:
        lock.release()


@app.get("/scripts/{project_id}/status")
def scripts_status(project_id: str):
    state = _read_scripts_state(project_id)
    if state.get("state") == "running":
        if _scripts_current_pid(project_id) is None:
            state["state"] = "failed"
            state["error"] = "scripts process disappeared"
            state["finished_at"] = datetime.datetime.now(datetime.timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )
            _scripts_state_path(project_id).write_text(
                json.dumps(state, indent=2), encoding="utf-8"
            )
            try:
                _scripts_pid_path(project_id).unlink()
            except OSError:
                pass
    return state


@app.get("/scripts/{project_id}/logs")
def scripts_logs(project_id: str, lines: int = Query(default=100, ge=1, le=10000)):
    log_path = _scripts_log_path(project_id)
    if not log_path.exists():
        return {"lines": []}
    text = log_path.read_text(encoding="utf-8")
    all_lines = text.splitlines()
    return {"lines": all_lines[-lines:] if len(all_lines) > lines else all_lines}


@app.post("/scripts/{project_id}/stop")
def scripts_stop(project_id: str):
    pid = _scripts_current_pid(project_id)
    if pid is None:
        return {"ok": False, "error": "not_running"}
    try:
        os.kill(pid, signal.SIGTERM)
        try:
            _scripts_pid_path(project_id).unlink()
        except OSError:
            pass
        logger.info("supervisor: scripts stopped pid=%d project_id=%s", pid, project_id)
        return {"ok": True}
    except OSError as exc:
        return {"ok": False, "error": str(exc)}


# ── sandbox-validation endpoints ──────────────────────────────────────────────
#
# Architecture (mirrors /analysis and /scripts):
#   Dashboard → API container (routes/sandbox.py)
#              → services/sandbox_runner.py (HTTP client)
#              → POST /sandbox/start (this endpoint, host-side supervisor)
#              → subprocess Popen → tools/agent_runner/run_sandbox.py
#
# The supervisor's job is path translation + process management. ALL git
# worktree manipulation and script execution happens host-side inside
# run_sandbox.py — the API Docker container no longer touches host git
# repos directly.


class SandboxStartRequest(BaseModel):
    project_root: str
    project_id: str
    mode: str = "validation"


def _sandbox_release_stale_lock(project_id: str) -> None:
    """Remove a stale PID file and reset the per-project lock if the worker is dead.

    Called before lock.acquire() so a dead worker never permanently blocks new starts.
    """
    pid_path = _sandbox_pid_path(project_id)
    if not pid_path.exists():
        return
    existing_pid = _sandbox_current_pid(project_id)  # removes stale PID file
    if existing_pid is None:
        with _sandbox_locks_mutex:
            _sandbox_locks.pop(project_id, None)


@app.post("/sandbox/start")
def sandbox_start(body: SandboxStartRequest):
    from fastapi.responses import JSONResponse

    _sandbox_release_stale_lock(body.project_id)

    lock = _get_sandbox_lock(body.project_id)
    if not lock.acquire(blocking=False):
        return JSONResponse(status_code=409, content={"ok": False, "error": "locked"})

    try:
        if _sandbox_current_pid(body.project_id) is not None:
            return JSONResponse(status_code=409, content={"ok": False, "error": "locked"})

        # Translate the container-side project_root to its host equivalent.
        # The mapper is the SAME instance used by /analysis/start so the
        # mapping rules are consistent across all supervisor-managed jobs.
        mapped_root = mapper.map(body.project_root)
        _sandbox_root_env = os.environ.get("SANDBOX_ROOT", "").strip()
        _sandbox_root_path = (
            Path(_sandbox_root_env).expanduser().resolve()
            if _sandbox_root_env
            else Path.home() / "sandboxes"
        )
        _proj_name = (
            os.environ.get("PROJECT_NAME", "").strip()
            or Path(os.environ.get("AI_DEV_FACTORY_PROJECT_ROOT", "")).name
            or "default"
        )
        sandbox_root = str(_sandbox_root_path / _proj_name)
        logger.info(
            "supervisor spawning sandbox validation project_id=%s",
            body.project_id,
        )
        logger.info(
            "  project_root(container)=%r -> project_root(host)=%r",
            body.project_root, mapped_root,
        )
        logger.info("  sandbox_root(host)=%s", sandbox_root)

        started_at = datetime.datetime.now(datetime.timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        )
        log = _sandbox_log_path(body.project_id)
        mode = body.mode if body.mode in ("validation", "environment") else "validation"
        cmd = [
            sys.executable,
            str(_run_sandbox_path()),
            "--project-root", mapped_root,
            "--project-id", body.project_id,
            "--mode", mode,
        ]
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}

        try:
            with open(log, "a", encoding="utf-8") as log_fh:
                log_fh.write(
                    f"[{started_at}] supervisor spawning sandbox validation for {body.project_id}\n"
                    f"  project_root(container)={body.project_root}\n"
                    f"  project_root(host)={mapped_root}\n"
                    f"  sandbox_root(host)={sandbox_root}\n"
                    f"  mode={mode}\n"
                    f"  command={' '.join(cmd)}\n"
                )
                log_fh.flush()
                proc = subprocess.Popen(
                    cmd,
                    cwd=str(_project_root()),
                    stdout=log_fh,
                    stderr=log_fh,
                    start_new_session=True,
                    env=env,
                )
            pid_path = _sandbox_pid_path(body.project_id)
            pid_path.parent.mkdir(parents=True, exist_ok=True)
            pid_path.write_text(
                json.dumps({"pid": proc.pid, "started_at": started_at}),
                encoding="utf-8",
            )
            logger.info(
                "supervisor: sandbox started pid=%d project_id=%s mode=%s",
                proc.pid, body.project_id, mode,
            )

            def _watch_worker(p: subprocess.Popen, pp: Path) -> None:
                p.wait()
                try:
                    pp.unlink()
                except OSError:
                    pass

            threading.Thread(
                target=_watch_worker, args=(proc, pid_path), daemon=True
            ).start()

            return {"ok": True, "pid": proc.pid}
        except OSError as exc:
            return {"ok": False, "error": str(exc)}
    finally:
        lock.release()


@app.get("/sandbox/{project_id}/status")
def sandbox_status_endpoint(project_id: str):
    state = _read_sandbox_state(project_id)
    # Phantom-process recovery: if the worker died without writing a terminal
    # state, promote to failed.  "environment" is intentionally worker-exited,
    # so we never mark it as failed here.
    if state.get("state") in ("running", "validating"):
        if _sandbox_current_pid(project_id) is None:
            state["state"] = "failed"
            state["error"] = "sandbox process disappeared"
            state["finished_at"] = datetime.datetime.now(
                datetime.timezone.utc
            ).strftime("%Y-%m-%dT%H:%M:%SZ")
            _sandbox_state_path(project_id).write_text(
                json.dumps(state, indent=2), encoding="utf-8"
            )
            try:
                _sandbox_pid_path(project_id).unlink()
            except OSError:
                pass
    return state


@app.get("/sandbox/{project_id}/logs")
def sandbox_logs(project_id: str, lines: int = Query(default=100, ge=1, le=10000)):
    log_path = _sandbox_log_path(project_id)
    if not log_path.exists():
        return {"lines": []}
    text = log_path.read_text(encoding="utf-8")
    all_lines = text.splitlines()
    return {"lines": all_lines[-lines:] if len(all_lines) > lines else all_lines}


def _sandbox_root_dir() -> Path:
    env = os.environ.get("SANDBOX_ROOT", "").strip()
    base = Path(env).expanduser().resolve() if env else Path.home() / "sandboxes"
    proj = (
        os.environ.get("PROJECT_NAME", "").strip()
        or Path(os.environ.get("AI_DEV_FACTORY_PROJECT_ROOT", "")).name
        or "default"
    )
    return base / proj


def _release_port_slot_supervisor(sandbox_id: str) -> None:
    registry = _sandbox_root_dir() / "port-registry.json"
    lock_file = _sandbox_root_dir() / ".port-registry.lock"
    if not registry.exists():
        return
    import fcntl
    try:
        lock_file.touch(exist_ok=True)
        with lock_file.open("r+") as lf:
            fcntl.flock(lf, fcntl.LOCK_EX)
            try:
                data = json.loads(registry.read_text())
                data.pop(sandbox_id, None)
                registry.write_text(json.dumps(data, indent=2))
            finally:
                fcntl.flock(lf, fcntl.LOCK_UN)
    except (OSError, json.JSONDecodeError):
        pass


def _run_stop_sh_supervisor(worktree_path: Path, sandbox_dir: Path) -> None:
    scripts_dir = ".ai-dev-factory/scripts"
    stop_script = worktree_path / scripts_dir / "stop.sh"
    if not stop_script.exists():
        return
    env = {**os.environ}
    deploy_env = sandbox_dir / "deploy.env"
    if deploy_env.exists():
        for line in deploy_env.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                env[k.strip()] = v.strip()
    try:
        subprocess.run(
            ["bash", f"{scripts_dir}/stop.sh"],
            cwd=str(worktree_path),
            env=env,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired):
        pass


def _do_sandbox_stop(project_id: str) -> dict:
    """Shared stop logic used by /stop and /delete endpoints."""
    state = _read_sandbox_state(project_id)
    current_state = state.get("state", "idle")

    if current_state in ("stopped", "cleaned"):
        return {"ok": True, "already": current_state}

    # Kill worker process if still alive (e.g. mid-validation).
    pid = _sandbox_current_pid(project_id)
    if pid is not None:
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            pass
        try:
            _sandbox_pid_path(project_id).unlink()
        except OSError:
            pass

    # For environment sandboxes the worker already exited; bring down compose.
    worktree_path_str = state.get("worktree_path")
    sandbox_id = state.get("sandbox_id")
    if worktree_path_str:
        worktree_path = Path(worktree_path_str)
        sandbox_dir = worktree_path.parent
        if worktree_path.exists():
            _run_stop_sh_supervisor(worktree_path, sandbox_dir)

    if sandbox_id:
        _release_port_slot_supervisor(sandbox_id)

    finished_at = datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    state["state"] = "stopped"
    state["finished_at"] = finished_at
    state_path = _sandbox_state_path(project_id)
    try:
        state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    except OSError:
        pass
    logger.info("supervisor: sandbox stopped project_id=%s", project_id)
    return {"ok": True}


@app.post("/sandbox/{project_id}/stop")
def sandbox_stop(project_id: str):
    return _do_sandbox_stop(project_id)


@app.delete("/sandbox/{project_id}")
def sandbox_delete(project_id: str):
    import shutil

    _do_sandbox_stop(project_id)

    state = _read_sandbox_state(project_id)
    worktree_path_str = state.get("worktree_path")
    if worktree_path_str:
        worktree_path = Path(worktree_path_str)
        sandbox_dir = worktree_path.parent
        project_root_str = state.get("project_root")

        if worktree_path.exists():
            removed = False
            if project_root_str:
                try:
                    result = subprocess.run(
                        ["git", "worktree", "remove", "--force", str(worktree_path)],
                        cwd=project_root_str,
                        capture_output=True,
                        timeout=30,
                    )
                    removed = result.returncode == 0
                except (OSError, subprocess.TimeoutExpired):
                    pass
            if not removed:
                try:
                    shutil.rmtree(worktree_path)
                except OSError as exc:
                    logger.warning(
                        "sandbox delete: could not remove worktree %s: %s",
                        worktree_path, exc,
                    )

        if sandbox_dir.exists():
            try:
                shutil.rmtree(sandbox_dir)
            except OSError as exc:
                logger.warning(
                    "sandbox delete: could not remove sandbox_dir %s: %s",
                    sandbox_dir, exc,
                )

    state["state"] = "cleaned"
    state["finished_at"] = datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    state_path = _sandbox_state_path(project_id)
    try:
        state_path.write_text(json.dumps(state, indent=2), encoding="utf-8")
    except OSError:
        pass
    try:
        _sandbox_pid_path(project_id).unlink()
    except OSError:
        pass
    logger.info("supervisor: sandbox deleted project_id=%s", project_id)
    return {"ok": True}


# ── named environments (host-side SandboxManager) ────────────────────────────
#
# Dashboard → API container (routes/environments.py)
#            → services/control_api/services/environment_runner.py
#            → POST /environments/provision (this surface)
#            → environment_provision.provision_environment + _sandbox_manager


class EnvironmentProvisionRequest(BaseModel):
    env_name: str
    project_root: str
    ref: str | None = None
    ref_type: str | None = None
    env_type: str | None = None
    deployment_mode: str | None = None
    web_host: str | None = None
    api_host: str | None = None
    sandbox_path: str | None = None
    runtime_root: str | None = None
    force_source_refresh: bool = False


def _environment_mgr_unavailable():
    from fastapi.responses import JSONResponse

    return JSONResponse(
        status_code=503,
        content={"ok": False, "error": "sandbox manager unavailable on supervisor"},
    )


@app.post("/environments/provision")
def environments_provision(body: EnvironmentProvisionRequest):
    from pathlib import Path

    from fastapi.responses import JSONResponse

    from services.control_api.services.environment_provision import (
        provision_environment_from_body,
    )

    logger.info(
        "supervisor: provision request env_name=%s project_root=%s runtime_root=%s force_source_refresh=%s",
        body.env_name,
        body.project_root,
        "<set>" if body.runtime_root else None,
        body.force_source_refresh,
    )

    if body.runtime_root is not None:
        rt = Path(body.runtime_root)
        if not rt.is_absolute() or any(part == ".." for part in rt.parts):
            return JSONResponse(
                status_code=400,
                content={"ok": False, "error": "runtime_root: must be an absolute path without '..'"},
            )

    if _sandbox_manager is None:
        return _environment_mgr_unavailable()
    try:
        state = provision_environment_from_body(
            _sandbox_manager,
            body.model_dump(),
            mapper.map,
        )
        return {"ok": True, "state": state.model_dump(mode="json")}
    except ValueError as exc:
        return JSONResponse(
            status_code=422,
            content={"ok": False, "error": str(exc)},
        )
    except Exception as exc:
        logger.exception("supervisor: environment provision failed")
        return JSONResponse(
            status_code=500,
            content={"ok": False, "error": str(exc)},
        )


@app.get("/environments")
def environments_list():
    from fastapi.responses import JSONResponse

    if _sandbox_manager is None:
        return _environment_mgr_unavailable()
    envs = [s.model_dump(mode="json") for s in _sandbox_manager.list() if s.env_name]
    return {"ok": True, "environments": envs}


@app.get("/environments/{env_id}")
def environments_get(env_id: str):
    from fastapi.responses import JSONResponse

    from services.control_api.services.sandbox_manager import SandboxNotFoundError

    if _sandbox_manager is None:
        return _environment_mgr_unavailable()
    try:
        state = _sandbox_manager.status(env_id)
        return {"ok": True, "state": state.model_dump(mode="json")}
    except SandboxNotFoundError:
        return JSONResponse(
            status_code=404,
            content={"ok": False, "error": f"environment not found: {env_id}"},
        )


@app.post("/environments/{env_id}/redeploy")
def environments_redeploy(env_id: str):
    from fastapi.responses import JSONResponse

    from services.control_api.services.sandbox_manager import SandboxNotFoundError

    if _sandbox_manager is None:
        return _environment_mgr_unavailable()
    from services.control_api.services.environment_provision import redeploy_environment

    try:
        state = redeploy_environment(_sandbox_manager, env_id)
        return {"ok": True, "state": state.model_dump(mode="json")}
    except SandboxNotFoundError:
        return JSONResponse(
            status_code=404,
            content={"ok": False, "error": f"environment not found: {env_id}"},
        )
    except RuntimeError as exc:
        return JSONResponse(
            status_code=500,
            content={"ok": False, "error": str(exc)},
        )


@app.post("/environments/{env_id}/stop")
def environments_stop(env_id: str):
    from fastapi.responses import JSONResponse

    from services.control_api.services.sandbox_manager import SandboxNotFoundError

    if _sandbox_manager is None:
        return _environment_mgr_unavailable()
    try:
        state = _sandbox_manager.stop(env_id)
        return {"ok": True, "state": state.model_dump(mode="json")}
    except SandboxNotFoundError:
        return JSONResponse(
            status_code=404,
            content={"ok": False, "error": f"environment not found: {env_id}"},
        )


@app.post("/environments/{env_id}/refresh")
def environments_refresh(env_id: str):
    from fastapi.responses import JSONResponse

    from services.control_api.services.sandbox_manager import SandboxNotFoundError

    if _sandbox_manager is None:
        return _environment_mgr_unavailable()
    try:
        state = _sandbox_manager.refresh(env_id)
        return {"ok": True, "state": state.model_dump(mode="json")}
    except SandboxNotFoundError:
        return JSONResponse(
            status_code=404,
            content={"ok": False, "error": f"environment not found: {env_id}"},
        )


@app.delete("/environments/{env_id}")
def environments_delete(env_id: str):
    from fastapi.responses import JSONResponse

    from services.control_api.services.sandbox_manager import SandboxNotFoundError

    if _sandbox_manager is None:
        return _environment_mgr_unavailable()
    try:
        _sandbox_manager.destroy(env_id)
        return {"ok": True}
    except SandboxNotFoundError:
        return JSONResponse(
            status_code=404,
            content={"ok": False, "error": f"environment not found: {env_id}"},
        )


@app.get("/environments/{env_id}/logs")
def environments_logs(env_id: str):
    from fastapi.responses import JSONResponse

    from services.control_api.services.sandbox_manager import SandboxNotFoundError

    if _sandbox_manager is None:
        return _environment_mgr_unavailable()
    try:
        logs = _sandbox_manager.logs(env_id)
        return {"ok": True, "logs": logs}
    except SandboxNotFoundError:
        return JSONResponse(
            status_code=404,
            content={"ok": False, "error": f"environment not found: {env_id}"},
        )


# ── Project host-filesystem endpoints (T188) ──────────────────────────────────
#
# Filesystem validation and bootstrap operations are delegated here by the
# Control API so that host paths (e.g. /Users/…) remain accessible when the
# Control API runs inside Docker.


def _detect_stack_for_path(project_root: Path) -> str:
    checks = [
        ("python", ["pyproject.toml", "requirements.txt", "setup.py", "setup.cfg"]),
        ("node", ["package.json"]),
        ("go", ["go.mod"]),
        ("rust", ["Cargo.toml"]),
    ]
    for stack, markers in checks:
        if any((project_root / m).exists() for m in markers):
            return stack
    return "unknown"


class ValidatePathRequest(BaseModel):
    project_root: str


class ProjectBootstrapHostRequest(BaseModel):
    project_root: str
    project_id: str
    runtime_root: str


@app.post("/projects/validate-path")
def validate_project_path(body: ValidatePathRequest):
    from fastapi.responses import JSONResponse

    try:
        p = Path(body.project_root).expanduser().resolve()
    except (OSError, PermissionError) as exc:
        return JSONResponse(
            status_code=422,
            content={"error": "permission_denied", "detail": str(exc)},
        )

    if not p.exists():
        return JSONResponse(
            status_code=422,
            content={"error": "path_not_found", "detail": str(p)},
        )
    if not p.is_dir():
        return JSONResponse(
            status_code=422,
            content={"error": "not_a_directory", "detail": str(p)},
        )

    git_check = p / ".git"
    is_git_repo = git_check.exists()

    return {
        "resolved_path": str(p),
        "is_dir": True,
        "is_git_repo": is_git_repo,
        "git_root": str(p) if is_git_repo else None,
    }


@app.post("/projects/bootstrap")
def bootstrap_project_host(body: ProjectBootstrapHostRequest):
    from fastapi.responses import JSONResponse

    try:
        project_root = Path(body.project_root).expanduser().resolve()
    except (OSError, PermissionError) as exc:
        return JSONResponse(
            status_code=422,
            content={"error": "permission_denied", "detail": str(exc)},
        )

    if not project_root.exists():
        return JSONResponse(
            status_code=422,
            content={"error": "path_not_found", "detail": str(project_root)},
        )
    if not project_root.is_dir():
        return JSONResponse(
            status_code=422,
            content={"error": "not_a_directory", "detail": str(project_root)},
        )

    git_check = project_root / ".git"
    if not git_check.exists():
        return JSONResponse(
            status_code=422,
            content={"error": "git_not_found", "detail": str(project_root)},
        )

    stack = _detect_stack_for_path(project_root)

    runtime_base_root = _runtime_base_root()
    project_runtime_root = runtime_base_root / body.project_id

    logger.info(
        "supervisor: bootstrap"
        " project_id=%s"
        " project_root=%s"
        " runtime_base_root=%s"
        " project_runtime_root=%s",
        body.project_id, project_root, runtime_base_root, project_runtime_root,
    )

    # Check writability before attempting mkdir so we return a structured error
    # instead of an unhandled OSError when the filesystem is read-only.
    writable_check = runtime_base_root if runtime_base_root.exists() else runtime_base_root.parent
    if not os.access(writable_check, os.W_OK):
        return JSONResponse(
            status_code=422,
            content={
                "error": "runtime_base_root_not_writable",
                "detail": str(runtime_base_root),
            },
        )

    runs_dir = project_runtime_root / "runs"
    logs_dir = project_runtime_root / "logs"
    state_dir = project_runtime_root / "state"
    worktrees_dir = project_runtime_root / "worktrees"
    clones_dir = project_runtime_root / "clones"

    try:
        for d in (runs_dir, logs_dir, state_dir, worktrees_dir, clones_dir):
            d.mkdir(parents=True, exist_ok=True)
    except PermissionError as exc:
        return JSONResponse(
            status_code=422,
            content={"error": "permission_denied", "detail": str(exc)},
        )
    except OSError as exc:
        return JSONResponse(
            status_code=422,
            content={"error": "runtime_base_root_not_writable", "detail": str(exc)},
        )

    try:
        from tools.agent_runner.bootstrap_agent_layout import bootstrap_agent_layout
        layout_result = bootstrap_agent_layout(project_root, body.project_id, stack)
    except Exception as exc:
        logger.warning("bootstrap_agent_layout: unexpected error: %s", exc)
        layout_result = {"branch": None, "pr_url": None, "pr_number": None, "error": str(exc)}

    return {
        "project_id": body.project_id,
        "project_root": str(project_root),
        "runtime_root": str(project_runtime_root),
        "stack": stack,
        "runs_dir": str(runs_dir),
        "logs_dir": str(logs_dir),
        "state_dir": str(state_dir),
        "worktrees_dir": str(worktrees_dir),
        "clones_dir": str(clones_dir),
        "agent_layout_branch": layout_result.get("branch"),
        "agent_layout_pr_url": layout_result.get("pr_url"),
        "agent_layout_pr_number": layout_result.get("pr_number"),
        "agent_layout_error": layout_result.get("error"),
    }


# ── install-agent-layout endpoints (async job) ───────────────────────────────


try:
    from agent_layout_jobs import (  # noqa: E402
        append_log as _al_append_log,
        job_log_path as _al_job_log_path,
        latest_job as _al_latest_job,
        list_jobs as _al_list_jobs,
        load_job as _al_load_job,
        make_job as _al_make_job,
        new_job_id as _al_new_job_id,
        persist_job as _al_persist_job,
        read_log as _al_read_log,
    )
    _agent_layout_available = True
except ImportError:
    _agent_layout_available = False


def _agent_layout_runtime_root() -> Path:
    return _runtime_root()


def _run_supervisor_git(args: list[str], cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=str(cwd), capture_output=True, text=True,
    )


class InstallAgentLayoutRequest(BaseModel):
    project_root: str
    project_id: str
    exec_cmd: str = "claude --dangerously-skip-permissions"


def _run_agent_layout_bg(
    job: dict,
    project_root: Path,
    stack: str,
    exec_cmd: str,
    runtime_root: Path,
) -> None:
    """Background thread: run install_agent_layout, streaming progress to the job log."""
    project_id = job["project_id"]
    log_path = Path(job["log_path"])

    def _log(message: str) -> None:
        _al_append_log(log_path, message)

    try:
        from tools.agent_runner.install_agent_layout import install_agent_layout
        result = install_agent_layout(
            project_root, project_id, stack, exec_cmd, log_cb=_log,
        )
        job["result"] = result
        job["branch"] = result.get("branch")
        job["error"] = result.get("error")
        job["status"] = "error" if result.get("error") else "done"
    except Exception as exc:  # noqa: BLE001 - report any failure to the dashboard
        job["status"] = "error"
        job["error"] = str(exc)
        _log(f"ERROR: {exc}")
        logger.warning("agent-layout job %s crashed: %s", job.get("job_id"), exc)
    finally:
        job["finished_at"] = datetime.datetime.now(
            datetime.timezone.utc
        ).strftime("%Y-%m-%dT%H:%M:%SZ")
        try:
            _al_persist_job(project_id, job, runtime_root)
        except Exception as persist_exc:  # noqa: BLE001
            logger.error(
                "supervisor: failed to persist agent-layout job %s: %s",
                job.get("job_id"), persist_exc,
            )


@app.post("/projects/{project_id}/install-agent-layout")
def install_agent_layout_endpoint(project_id: str, body: InstallAgentLayoutRequest):
    from fastapi.responses import JSONResponse

    if not _agent_layout_available:
        return JSONResponse(
            status_code=503,
            content={"error": "agent_layout_jobs not available"},
        )

    try:
        mapped = mapper.map(body.project_root)
        project_root = Path(mapped).expanduser().resolve()
    except (OSError, PermissionError) as exc:
        return JSONResponse(
            status_code=422,
            content={"error": "permission_denied", "detail": str(exc)},
        )

    if not project_root.exists() or not project_root.is_dir():
        return JSONResponse(
            status_code=422,
            content={"error": "path_not_found", "detail": str(project_root)},
        )

    if not (project_root / ".git").exists():
        return JSONResponse(
            status_code=422,
            content={"error": "git_not_found", "detail": str(project_root)},
        )

    stack = _detect_stack_for_path(project_root)
    runtime_root = _agent_layout_runtime_root()
    job_id = _al_new_job_id()
    log_path = _al_job_log_path(runtime_root, project_id, job_id)
    job = _al_make_job(
        job_id=job_id,
        project_id=project_id,
        project_root=str(project_root),
        stack=stack,
        exec_cmd=body.exec_cmd,
        log_path=str(log_path),
    )
    _al_persist_job(project_id, job, runtime_root)
    _al_append_log(log_path, f"Queued agent-layout job for '{project_id}' (stack={stack})")

    logger.info(
        "supervisor: install-agent-layout job=%s project_id=%s root=%s stack=%s",
        job_id, project_id, project_root, stack,
    )

    threading.Thread(
        target=_run_agent_layout_bg,
        args=(job, project_root, stack, body.exec_cmd, runtime_root),
        daemon=True,
    ).start()

    return {"ok": True, "job_id": job_id}


@app.get("/projects/{project_id}/install-agent-layout/jobs")
def install_agent_layout_jobs(project_id: str):
    from fastapi.responses import JSONResponse

    if not _agent_layout_available:
        return JSONResponse(status_code=503, content={"error": "agent_layout_jobs not available"})
    return {"jobs": _al_list_jobs(project_id, _agent_layout_runtime_root())}


@app.get("/projects/{project_id}/install-agent-layout/status")
def install_agent_layout_status(project_id: str, project_root: str = Query(...)):
    from fastapi.responses import JSONResponse

    if not _agent_layout_available:
        return JSONResponse(status_code=503, content={"error": "agent_layout_jobs not available"})
    try:
        mapped = mapper.map(project_root)
        root = Path(mapped).expanduser().resolve()
    except (OSError, PermissionError) as exc:
        return JSONResponse(status_code=422, content={"error": "permission_denied", "detail": str(exc)})
    if not root.exists() or not root.is_dir():
        return JSONResponse(status_code=422, content={"error": "path_not_found", "detail": str(root)})
    try:
        from tools.agent_runner.install_agent_layout import inspect_layout
        return inspect_layout(root)
    except Exception as exc:  # noqa: BLE001
        logger.warning("install-agent-layout status failed: %s", exc)
        return JSONResponse(status_code=500, content={"error": str(exc)})


@app.get("/projects/{project_id}/install-agent-layout/latest")
def install_agent_layout_latest(project_id: str):
    from fastapi.responses import JSONResponse

    if not _agent_layout_available:
        return JSONResponse(status_code=503, content={"error": "agent_layout_jobs not available"})
    job = _al_latest_job(project_id, _agent_layout_runtime_root())
    if job is None:
        return JSONResponse(status_code=404, content={"error": "no agent-layout job yet"})
    return job


@app.get("/projects/{project_id}/install-agent-layout/{job_id}")
def install_agent_layout_job(project_id: str, job_id: str):
    from fastapi.responses import JSONResponse

    if not _agent_layout_available:
        return JSONResponse(status_code=503, content={"error": "agent_layout_jobs not available"})
    job = _al_load_job(project_id, job_id, _agent_layout_runtime_root())
    if job is None:
        return JSONResponse(status_code=404, content={"error": f"job not found: {job_id}"})
    return job


@app.get("/projects/{project_id}/install-agent-layout/{job_id}/logs")
def install_agent_layout_logs(project_id: str, job_id: str, offset: int = Query(default=0, ge=0)):
    from fastapi.responses import JSONResponse

    if not _agent_layout_available:
        return JSONResponse(status_code=503, content={"error": "agent_layout_jobs not available"})
    runtime_root = _agent_layout_runtime_root()
    job = _al_load_job(project_id, job_id, runtime_root)
    if job is None:
        return JSONResponse(status_code=404, content={"error": f"job not found: {job_id}"})
    text, new_offset = _al_read_log(Path(job["log_path"]), offset)
    return {"text": text, "offset": new_offset, "status": job.get("status")}


def _agent_layout_base_branch(project_root: Path) -> str:
    """Best-effort default/base branch for diffing the docs branch."""
    res = _run_supervisor_git(["rev-parse", "--abbrev-ref", "origin/HEAD"], project_root)
    if res.returncode == 0:
        ref = res.stdout.strip()
        if ref.startswith("origin/"):
            return ref.split("/", 1)[1]
    for candidate in ("main", "master"):
        chk = _run_supervisor_git(["rev-parse", "--verify", candidate], project_root)
        if chk.returncode == 0:
            return candidate
    return "main"


@app.get("/projects/{project_id}/install-agent-layout/{job_id}/files")
def install_agent_layout_files(project_id: str, job_id: str):
    from fastapi.responses import JSONResponse

    if not _agent_layout_available:
        return JSONResponse(status_code=503, content={"error": "agent_layout_jobs not available"})
    runtime_root = _agent_layout_runtime_root()
    job = _al_load_job(project_id, job_id, runtime_root)
    if job is None:
        return JSONResponse(status_code=404, content={"error": f"job not found: {job_id}"})

    project_root = Path(job["project_root"])
    branch = job.get("branch")
    result = job.get("result") or {}
    files: list[dict] = []
    if branch and project_root.exists():
        base = _agent_layout_base_branch(project_root)
        diff = _run_supervisor_git(
            ["diff", "--name-status", f"{base}...{branch}"], project_root,
        )
        if diff.returncode == 0:
            for line in diff.stdout.splitlines():
                parts = line.split("\t")
                if len(parts) >= 2:
                    files.append({"status": parts[0].strip(), "path": parts[-1].strip()})
    return {
        "files": files,
        "docs_paths": result.get("docs_paths", []),
        "warnings": result.get("warnings", []),
        "branch": branch,
    }


@app.get("/projects/{project_id}/install-agent-layout/{job_id}/file")
def install_agent_layout_file(project_id: str, job_id: str, path: str = Query(...)):
    from fastapi.responses import JSONResponse

    if not _agent_layout_available:
        return JSONResponse(status_code=503, content={"error": "agent_layout_jobs not available"})
    runtime_root = _agent_layout_runtime_root()
    job = _al_load_job(project_id, job_id, runtime_root)
    if job is None:
        return JSONResponse(status_code=404, content={"error": f"job not found: {job_id}"})

    if path.startswith("/") or ".." in Path(path).parts:
        return JSONResponse(status_code=422, content={"error": "invalid path"})

    project_root = Path(job["project_root"])
    branch = job.get("branch")
    if not branch or not project_root.exists():
        return JSONResponse(status_code=404, content={"error": "no branch for this job"})

    base = _agent_layout_base_branch(project_root)
    show = _run_supervisor_git(["show", f"{branch}:{path}"], project_root)
    diff = _run_supervisor_git(["diff", f"{base}...{branch}", "--", path], project_root)
    return {
        "path": path,
        "content": show.stdout if show.returncode == 0 else "",
        "diff": diff.stdout if diff.returncode == 0 else "",
    }


# ── per-project daemon endpoints ─────────────────────────────────────────────
#
# Each imported project gets its own isolated daemon.  Global daemon state
# (_daemon_state, _daemon_proc, _pid_path()) is untouched by these endpoints.

_project_daemon_states: dict[str, DaemonState] = {}
_project_daemon_procs: dict[str, subprocess.Popen] = {}
_project_daemon_exec_cmds: dict[str, str] = {}


def _project_runtime_root(project_id: str) -> Path:
    return _runtime_base_root() / project_id


def _project_runs_dir(project_id: str) -> Path:
    return _project_runtime_root(project_id) / "runs"


def _project_logs_dir(project_id: str) -> Path:
    return _project_runtime_root(project_id) / "logs"


def _project_state_dir(project_id: str) -> Path:
    return _project_runtime_root(project_id) / "state"


def _project_worktrees_dir(project_id: str) -> Path:
    return _project_runtime_root(project_id) / "worktrees"


def _project_pid_path(project_id: str) -> Path:
    return _project_runs_dir(project_id) / _PID_FILENAME


def _project_log_path(project_id: str) -> Path:
    return _project_logs_dir(project_id) / _LOG_FILENAME


def _read_project_pid_file(project_id: str) -> dict | None:
    path = _project_pid_path(project_id)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _write_project_pid_file(project_id: str, pid: int, started_at: str, exec_cmd: str, restart_policy: str) -> None:
    path = _project_pid_path(project_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"pid": pid, "started_at": started_at, "exec_cmd": exec_cmd, "restart_policy": restart_policy}),
        encoding="utf-8",
    )


def _remove_project_pid_file(project_id: str) -> None:
    try:
        _project_pid_path(project_id).unlink()
    except OSError:
        pass


def _lookup_project_root_from_control_api(project_id: str) -> str | None:
    """Query the control API workspace registry for a project's root path.

    Returns None when the control API is unreachable or the project is not registered.
    """
    import urllib.request

    control_api_url = os.environ.get("AI_DEV_FACTORY_CONTROL_API_URL", "http://127.0.0.1:8080")
    try:
        with urllib.request.urlopen(f"{control_api_url}/projects", timeout=3) as resp:
            data = json.loads(resp.read().decode())
        for proj in data:
            if isinstance(proj, dict) and proj.get("name") == project_id:
                return proj.get("root")
    except Exception:
        pass
    return None


class ProjectDaemonStartRequest(BaseModel):
    exec_cmd: str = "claude --dangerously-skip-permissions --model sonnet"
    restart_policy: str = "no-restart"


@app.post("/projects/{project_id}/daemon/start")
def project_daemon_start(project_id: str, body: ProjectDaemonStartRequest = None):  # noqa: B008
    from fastapi.responses import JSONResponse

    if body is None:
        body = ProjectDaemonStartRequest()

    project_root_str = _lookup_project_root_from_control_api(project_id)
    if project_root_str is None:
        return JSONResponse(
            status_code=404,
            content={"ok": False, "error": f"project not registered in workspace: {project_id!r}"},
        )

    # The control API runs inside Docker, so its registry "root" is a CONTAINER
    # path (e.g. /runtime/clones/<id>). Map it to the host path before using it
    # as the daemon's working directory — otherwise Popen(cwd=...) fails with
    # "No such file or directory" on the host.
    project_root = Path(mapper.map(project_root_str))
    project_runtime_root = _project_runtime_root(project_id)
    runs_dir = _project_runs_dir(project_id)
    logs_dir = _project_logs_dir(project_id)
    state_dir = _project_state_dir(project_id)
    worktrees_dir = _project_worktrees_dir(project_id)
    daemon_pid_path = _project_pid_path(project_id)

    logger.info(
        "supervisor: project daemon start project_id=%s project_root=%s"
        " project_runtime_root=%s runs_dir=%s logs_dir=%s state_dir=%s"
        " worktrees_dir=%s daemon_pid_path=%s",
        project_id, project_root, project_runtime_root,
        runs_dir, logs_dir, state_dir, worktrees_dir, daemon_pid_path,
    )

    state = _project_daemon_states.setdefault(project_id, DaemonState())
    pid = state.pid
    if pid is not None and _is_alive(pid):
        return {"ok": False, "pid": pid, "error": "already_running"}

    state.restart_policy = body.restart_policy
    _project_daemon_exec_cmds[project_id] = body.exec_cmd

    started_at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    logs_dir.mkdir(parents=True, exist_ok=True)
    log = _project_log_path(project_id)

    cmd = [
        sys.executable,
        str(_run_daemon_path()),
        "--exec-cmd", body.exec_cmd,
        "--poll-issues",
        "--issue-label", "ai-ready",
        "--auto-commit",
        "--auto-push",
        "--auto-include-code",
        "--worktrees-dir", str(worktrees_dir),
        "--project-root", str(project_root),
        # Scope this daemon's runtime DB rows to its project (Postgres backend).
        "--project", project_id,
    ]
    tools_dir = _project_root_dir / "tools" / "agent_runner"
    if str(tools_dir) not in sys.path:
        sys.path.insert(0, str(tools_dir))
    import runtime_settings as _runtime_settings  # noqa: E402

    cmd += _runtime_settings.daemon_max_workers_argv_for_project(
        project_id, project_runtime_root=project_runtime_root,
    )
    try:
        # The daemon inherits the supervisor's environment, which carries the
        # runtime DB config (RUNTIME_DB_BACKEND/HOST/PORT/USER/PASSWORD/NAME)
        # loaded from deploy/.env — so API, supervisor and daemon all share one
        # backend (no SQLite/Postgres split-brain). PROJECT_NAME is overridden
        # per project so rows are tagged with the correct project_id even though
        # the supervisor's own PROJECT_NAME is ai-dev-factory.
        env = {
            **os.environ,
            "PYTHONDONTWRITEBYTECODE": "1",
            "AI_DEV_FACTORY_RUNTIME_ROOT": str(project_runtime_root),
            "PROJECT_NAME": project_id,
        }
        with open(log, "a", encoding="utf-8") as log_fh:
            log_fh.write(
                f"[{started_at}] supervisor spawning project daemon\n"
                f"  project_id={project_id}\n"
                f"  project_root={project_root}\n"
                f"  project_runtime_root={project_runtime_root}\n"
                f"  runs_dir={runs_dir}\n"
                f"  logs_dir={logs_dir}\n"
                f"  state_dir={state_dir}\n"
                f"  worktrees_dir={worktrees_dir}\n"
                f"  daemon_pid_path={daemon_pid_path}\n"
                f"  runtime_db_backend={os.environ.get('RUNTIME_DB_BACKEND', 'sqlite')} "
                f"runtime_db_host={os.environ.get('RUNTIME_DB_HOST', '<unset>')} "
                f"runtime_db_name={os.environ.get('RUNTIME_DB_NAME', '<unset>')}\n"
                f"  command={' '.join(cmd)}\n"
            )
            log_fh.flush()
            proc = subprocess.Popen(
                cmd,
                cwd=str(project_root),
                stdout=log_fh,
                stderr=log_fh,
                start_new_session=True,
                env=env,
            )
        _project_daemon_procs[project_id] = proc
        _write_project_pid_file(project_id, proc.pid, started_at, body.exec_cmd, body.restart_policy)
        state.pid = proc.pid
        state.started_at = started_at
        state.exit_unexpected = False
        logger.info("supervisor: project daemon started project_id=%s pid=%d", project_id, proc.pid)
        return {"ok": True, "pid": proc.pid}
    except OSError as exc:
        return JSONResponse(status_code=500, content={"ok": False, "error": str(exc)})


@app.get("/projects/{project_id}/daemon/status")
def project_daemon_status(project_id: str):
    state = _project_daemon_states.get(project_id)
    if state is None:
        data = _read_project_pid_file(project_id)
        if data is not None:
            pid = data.get("pid")
            if isinstance(pid, int) and _is_alive(pid):
                state = _project_daemon_states.setdefault(project_id, DaemonState())
                state.pid = pid
                state.started_at = data.get("started_at")
                state.restart_policy = data.get("restart_policy", "no-restart")
            else:
                _remove_project_pid_file(project_id)

    if state is None:
        return {"running": False, "pid": None, "project_id": project_id}

    pid = state.pid
    running = pid is not None and _is_alive(pid)
    if not running and pid is not None:
        _remove_project_pid_file(project_id)
        state.pid = None

    return {
        "running": running,
        "pid": state.pid,
        "project_id": project_id,
        "started_at": state.started_at,
        "last_exit_code": state.last_exit_code,
        "last_exit_time": state.last_exit_time,
        "last_error": state.last_error,
        "exit_unexpected": state.exit_unexpected,
        "restart_count": state.restart_count,
        "restart_policy": state.restart_policy,
    }


@app.post("/projects/{project_id}/daemon/stop")
def project_daemon_stop(project_id: str):
    from fastapi.responses import JSONResponse

    state = _project_daemon_states.get(project_id)
    pid = state.pid if state is not None else None

    if pid is None:
        data = _read_project_pid_file(project_id)
        if data:
            pid = data.get("pid")

    if pid is None or not _is_alive(pid):
        _remove_project_pid_file(project_id)
        return JSONResponse(status_code=400, content={"ok": False, "error": "not_running"})

    try:
        os.kill(pid, signal.SIGTERM)
        _remove_project_pid_file(project_id)
        if state is not None:
            state.pid = None
            state.started_at = None
        _project_daemon_procs.pop(project_id, None)
        logger.info("supervisor: project daemon stopped project_id=%s pid=%d", project_id, pid)
        return {"ok": True}
    except OSError as exc:
        return JSONResponse(status_code=500, content={"ok": False, "error": str(exc)})


# ── ticket intelligence (host-side claude) ───────────────────────────────────
#
# The control API runs in Docker without the claude CLI. POST analyze is proxied
# here so hybrid analysis uses the same host credentials as the daemon.


class TicketIntelligenceAnalyzeRequest(BaseModel):
    exec_cmd: str = "claude --dangerously-skip-permissions"


def _default_exec_cmd() -> str:
    return os.environ.get(
        "DAEMON_EXEC_CMD",
        "claude --dangerously-skip-permissions --model sonnet",
    )




@app.get("/projects/{project_id}/tickets/{ticket_id}/intelligence")
def project_ticket_intelligence_get(project_id: str, ticket_id: str):
    """Return ticket intelligence from the host-owned runtime store."""
    from fastapi.responses import JSONResponse

    tools_dir = _project_root_dir / "tools" / "agent_runner"
    if str(tools_dir) not in sys.path:
        sys.path.insert(0, str(tools_dir))
    import runtime_db  # noqa: E402
    import ticket_intelligence_recovery as recovery  # noqa: E402

    project_runtime_root = _project_runtime_root(project_id)
    try:
        db = runtime_db.resolve_db_path_for_project(
            project_id,
            project_runtime_root=project_runtime_root,
        )
    except Exception as exc:
        return JSONResponse(status_code=503, content={"error": f"failed to resolve runtime DB: {exc}"})
    if db is None:
        return JSONResponse(status_code=503, content={"error": "database not available"})

    try:
        runtime_db.init_runtime_db(db)
    except Exception as exc:
        return JSONResponse(status_code=503, content={"error": f"runtime DB unavailable: {exc}"})

    try:
        for _reaped in recovery.reap_stale_intelligence(db):
            pass
    except Exception:
        logger.exception("supervisor: reaper failed on GET for %s", ticket_id)

    try:
        row = runtime_db.get_ticket_intelligence(db, ticket_id)
    except Exception as exc:
        return JSONResponse(status_code=503, content={"error": f"failed to read intelligence: {exc}"})
    if row is None:
        return JSONResponse(
            status_code=404,
            content={"detail": f"no intelligence analysis found for ticket {ticket_id}"},
        )
    if isinstance(row, dict):
        row = {k: v for k, v in row.items() if k != "project_id"}
    return row


@app.post("/projects/{project_id}/tickets/{ticket_id}/intelligence/analyze")
def project_ticket_intelligence_analyze(
    project_id: str,
    ticket_id: str,
    body: TicketIntelligenceAnalyzeRequest | None = None,
):
    from fastapi.responses import JSONResponse

    intel_log = logging.getLogger("intel")

    if body is None:
        body = TicketIntelligenceAnalyzeRequest(exec_cmd=_default_exec_cmd())
    elif body.exec_cmd == "claude --dangerously-skip-permissions":
        body.exec_cmd = _default_exec_cmd()

    tools_dir = _project_root_dir / "tools" / "agent_runner"
    if str(tools_dir) not in sys.path:
        sys.path.insert(0, str(tools_dir))
    import runtime_db  # noqa: E402
    import ticket_intelligence_analyzer as analyzer  # noqa: E402
    import ticket_intelligence_recovery as recovery  # noqa: E402

    project_root_str = _lookup_project_root_from_control_api(project_id)
    if project_root_str is None:
        return JSONResponse(
            status_code=404,
            content={"error": f"project not registered in workspace: {project_id!r}"},
        )

    project_root = Path(project_root_str)
    project_runtime_root = _project_runtime_root(project_id)
    worktrees_dir = _project_worktrees_dir(project_id)

    from services.control_api.services.runtime_resolver import (  # noqa: E402
        resolve_runs_dir,
        resolve_ticket_run_dir,
    )

    try:
        db = runtime_db.resolve_db_path_for_project(
            project_id,
            project_runtime_root=project_runtime_root,
        )
    except Exception as exc:
        logger.exception(
            "supervisor: failed to resolve DB for project_id=%s ticket_id=%s",
            project_id, ticket_id,
        )
        return JSONResponse(
            status_code=503,
            content={"error": f"failed to resolve runtime DB: {exc}"},
        )
    if db is None:
        return JSONResponse(status_code=503, content={"error": "database not available"})

    # Per-project DB may not exist yet — initialize before any read/write.
    try:
        runtime_db.init_runtime_db(db)
    except Exception as exc:
        logger.exception(
            "supervisor: init_runtime_db failed for %s/%s db=%s",
            project_id, ticket_id, db,
        )
        return JSONResponse(
            status_code=503,
            content={"error": f"runtime DB unavailable: {exc}"},
        )

    # Reap any stale row so the idempotency guard below does not block a manual
    # re-analyze on a ticket whose previous run died silently.
    try:
        for reaped in recovery.reap_stale_intelligence(db):
            intel_log.info(
                "intel.reaped project_id=%s ticket_id=%s db_path=%s previous_status=%s age_seconds=%d",
                project_id, reaped.get("ticket_id"), db,
                reaped.get("previous_status"), reaped.get("age_seconds"),
            )
    except Exception:
        logger.exception("supervisor: reaper failed before analyze for %s", ticket_id)

    try:
        existing = runtime_db.get_ticket_intelligence(db, ticket_id)
        if existing and existing.get("analysis_status") == "running":
            return {"ticket_id": ticket_id, "analysis_status": existing["analysis_status"]}

        try:
            runs_dir = resolve_runs_dir(
                project_root,
                project_id=project_id,
                project_runtime_root=project_runtime_root,
            )
            run_dir = resolve_ticket_run_dir(ticket_id, runs_dir, worktrees_dir)
            ticket_path = run_dir / "ticket.md"
            ticket_content = ticket_path.read_text(encoding="utf-8") if ticket_path.exists() else ""
        except Exception as exc:
            logger.warning("supervisor: could not read ticket.md for %s: %s", ticket_id, exc)
            ticket_content = ""

        runtime_db.upsert_ticket_intelligence(db, ticket_id, analysis_status="queued")
        intel_log.info(
            "intel.queued project_id=%s ticket_id=%s db_path=%s",
            project_id, ticket_id, db,
        )
    except Exception as exc:
        logger.exception(
            "supervisor: pre-thread failure for %s/%s — persisting failed",
            project_id, ticket_id,
        )
        try:
            runtime_db.upsert_ticket_intelligence(
                db, ticket_id,
                analysis_status="failed",
                analysis_summary=f"Supervisor pre-thread error: {exc}",
            )
            intel_log.info(
                "intel.failed project_id=%s ticket_id=%s db_path=%s reason=pre_thread",
                project_id, ticket_id, db,
            )
        except Exception:
            logger.exception(
                "supervisor: failed to persist pre-thread failure for %s",
                ticket_id,
            )
        return JSONResponse(
            status_code=503,
            content={"error": f"pre-thread failure: {exc}"},
        )

    def _bg() -> None:
        try:
            analyzer.run_analysis(
                db, ticket_id, ticket_content, body.exec_cmd, project_root,
                project_id=project_id,
            )
        except Exception as exc:
            logger.exception(
                "supervisor: intelligence analysis failed for project_id=%s ticket_id=%s stage=bg_thread",
                project_id, ticket_id,
            )
            intel_log.exception(
                "intel.bg_thread_crash project_id=%s ticket_id=%s db_path=%s detail=%s",
                project_id, ticket_id, db, exc,
            )
            # ``run_analysis`` is meant to persist its own failures. If something
            # still escapes (programmer error, BaseException, etc.), persist
            # failed here so the row never stays in ``queued`` / ``running``.
            import traceback as _traceback
            from datetime import datetime, timezone
            failed_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            tb = _traceback.format_exc()
            try:
                runtime_db.upsert_ticket_intelligence(
                    db, ticket_id,
                    analysis_status="failed",
                    analysis_summary=f"Background thread crashed: {exc}",
                    failed_at=failed_at,
                    failure_origin="bg_thread_crash",
                    stage="failed",
                )
            except Exception:
                logger.exception(
                    "supervisor: failed to persist bg-thread crash for %s",
                    ticket_id,
                )
            try:
                runtime_db.append_runtime_event(
                    db,
                    ticket_id,
                    "ticket_intelligence_analysis_failed",
                    f"ticket_intelligence bg-thread crashed ticket_id={ticket_id}",
                    metadata={
                        "project_id": project_id,
                        "stage": "failed",
                        "failure_origin": "bg_thread_crash",
                        "analysis_summary": f"Background thread crashed: {exc}",
                        "traceback": tb[-2048:] if tb else "",
                    },
                )
            except Exception:
                logger.exception(
                    "supervisor: failed to append bg-thread crash event for %s",
                    ticket_id,
                )

    threading.Thread(target=_bg, daemon=True).start()
    logger.info(
        "supervisor: ticket intelligence analyze queued project_id=%s ticket_id=%s",
        project_id,
        ticket_id,
    )
    return {"ticket_id": ticket_id, "analysis_status": "queued"}


# ── conflict resolution (host-side git + claude) ─────────────────────────────
#
# The control API runs in Docker where worktree ``.git`` files point at host
# paths, so ``git rev-parse`` fails in-container. POST resolve-conflicts is
# proxied here — same pattern as ticket intelligence analyze above.


class TicketResolveConflictsRequest(BaseModel):
    exec_cmd: str = "claude --dangerously-skip-permissions"


@app.post("/projects/{project_id}/tickets/{ticket_id}/resolve-conflicts")
def project_ticket_resolve_conflicts(
    project_id: str,
    ticket_id: str,
    body: TicketResolveConflictsRequest | None = None,
):
    from fastapi.responses import JSONResponse

    tools_dir = _project_root_dir / "tools" / "agent_runner"
    if str(tools_dir) not in sys.path:
        sys.path.insert(0, str(tools_dir))
    from conflict_resolution_eligibility import (  # noqa: WPS433
        conflict_resolution_eligible,
        git_conflicted_files,
        reset_conflict_resolution_auto_retry,
    )

    if body is None:
        body = TicketResolveConflictsRequest(exec_cmd=_default_exec_cmd())
    elif body.exec_cmd == "claude --dangerously-skip-permissions":
        body.exec_cmd = _default_exec_cmd()

    project_root_str = _lookup_project_root_from_control_api(project_id)
    if project_root_str is None:
        return JSONResponse(
            status_code=404,
            content={"error": f"project not registered in workspace: {project_id!r}"},
        )

    project_root = Path(project_root_str)
    worktrees_dir = _project_worktrees_dir(project_id)
    wt_cwd = worktrees_dir / ticket_id
    if not wt_cwd.is_dir():
        return JSONResponse(
            status_code=404,
            content={"error": f"worktree not found for ticket {ticket_id!r}"},
        )

    resolver = _project_root_dir / "tools" / "agent_runner" / "run_conflict_resolver.py"
    if not resolver.is_file():
        return JSONResponse(status_code=503, content={"error": "run_conflict_resolver.py not found"})

    state_file = wt_cwd / "runs" / ticket_id / "state.json"
    if not state_file.is_file():
        return JSONResponse(status_code=404, content={"error": f"state.json not found for {ticket_id}"})
    try:
        state_data = json.loads(state_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        return JSONResponse(status_code=500, content={"error": f"state.json unreadable: {exc}"})

    current = state_data.get("state")
    conflicted = git_conflicted_files(wt_cwd)
    if not conflict_resolution_eligible(state_data, wt_cwd):
        return JSONResponse(
            status_code=409,
            content={
                "error": (
                    f"ticket {ticket_id} is not awaiting conflict resolution "
                    f"(current: {current!r})"
                ),
            },
        )

    if current not in ("CONFLICT_RESOLUTION_NEEDED", "CONFLICT_RESOLUTION_FAILED", "CONFLICT_RESOLVING"):
        pre = state_data.get("pre_conflict_state") or current
        if pre in (
            "CONFLICT_RESOLUTION_NEEDED",
            "CONFLICT_RESOLVING",
            "CONFLICT_RESOLVED_REVIEW_NEEDED",
            "CONFLICT_RESOLUTION_FAILED",
        ):
            pre = "IMPLEMENTATION_REVIEW_NEEDED"
        state_data["pre_conflict_state"] = pre
        if conflicted:
            state_data["conflicted_files"] = conflicted
        if not state_data.get("conflict_detected_at"):
            state_data["conflict_detected_at"] = datetime.datetime.now(
                datetime.timezone.utc,
            ).strftime("%Y-%m-%dT%H:%M:%SZ")

    reset_conflict_resolution_auto_retry(wt_cwd / "runs" / ticket_id)

    state_data["state"] = "CONFLICT_RESOLVING"
    state_data["updated_at"] = datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ",
    )
    tmp = state_file.with_suffix(".tmp")
    tmp.write_text(json.dumps(state_data, indent=2), encoding="utf-8")
    tmp.replace(state_file)

    def _bg() -> None:
        try:
            subprocess.run(
                [sys.executable, str(resolver), ticket_id, "--exec-cmd", body.exec_cmd],
                cwd=str(wt_cwd),
                env={
                    **os.environ,
                    "PYTHONDONTWRITEBYTECODE": "1",
                    "PROJECT_NAME": project_id,
                },
                check=False,
            )
        except Exception:
            logger.exception(
                "supervisor: conflict resolution failed project_id=%s ticket_id=%s",
                project_id, ticket_id,
            )

    threading.Thread(target=_bg, daemon=True).start()
    logger.info(
        "supervisor: conflict resolution queued project_id=%s ticket_id=%s cwd=%s",
        project_id, ticket_id, wt_cwd,
    )
    return {"ticket_id": ticket_id, "state": "CONFLICT_RESOLVING"}


# ── auto-fix proposal endpoints ───────────────────────────────────────────────
#
# Architecture:
#   Dashboard → API container (routes/auto_fix.py)
#              → services/auto_fix_runner.py (HTTP client)
#              → POST /auto-fix/{project_id}/propose (this endpoint)
#              → background thread → auto_fix_proposer.py
#
# The proposal runs in a background daemon thread so the HTTP response
# returns immediately with a proposal_id. The GET endpoints poll state.json.

try:
    from auto_fix_proposer import (  # noqa: E402
        collect_failure_context,
        call_ai_runtime,
        validate_patches,
        make_proposal,
        make_proposal_id,
        persist_proposal,
        load_proposal,
        list_proposals as _list_proposals_disk,
    )
    _auto_fix_available = True
except ImportError:
    _auto_fix_available = False


def _auto_fix_runtime_root() -> Path:
    return _runtime_root()


class AutoFixProposeRequest(BaseModel):
    project_root: str
    exec_cmd: str
    sandbox_id: str
    failing_step: str | None = None


def _run_proposal_bg(
    proposal: dict,
    project_root: Path,
    exec_cmd: str,
    runtime_root: Path,
) -> None:
    """Background thread: collect context, call AI, validate, persist."""
    project_id = proposal["project_id"]
    sandbox_id = proposal["sandbox_id"]
    failing_step = proposal.get("failing_step")

    try:
        context = collect_failure_context(sandbox_id, project_root, runtime_root)
        raw_patches = call_ai_runtime(context, exec_cmd, project_root, failing_step)
        validated = validate_patches(raw_patches, project_root)

        any_valid = any(p["valid"] for p in validated)
        any_invalid = any(not p["valid"] for p in validated)
        if any_valid and any_invalid:
            proposal["status"] = "ready_with_warnings"
        elif any_valid:
            proposal["status"] = "ready"
        else:
            proposal["status"] = "rejected"
        proposal["patches"] = validated
        proposal["context_snapshot"] = {
            "deploy_profile_present": bool(context.get("deploy_profile")),
            "log_lines": len(context.get("logs") or []),
            "script_files": list((context.get("operational_scripts") or {}).keys()),
        }
        logger.info(
            "supervisor: auto-fix proposal %s status=%s patches=%d",
            proposal["proposal_id"], proposal["status"], len(validated),
        )
    except Exception as exc:
        proposal["status"] = "error"
        proposal["error"] = str(exc)
        logger.warning(
            "supervisor: auto-fix proposal %s failed: %s",
            proposal["proposal_id"], exc,
        )

    try:
        persist_proposal(project_id, proposal, runtime_root)
    except Exception as exc:
        logger.error("supervisor: failed to persist proposal %s: %s", proposal["proposal_id"], exc)


@app.post("/auto-fix/{project_id}/propose")
def auto_fix_propose(project_id: str, body: AutoFixProposeRequest):
    from fastapi.responses import JSONResponse

    if not _auto_fix_available:
        return JSONResponse(
            status_code=503,
            content={"ok": False, "error": "auto_fix_proposer not available"},
        )

    mapped_root = mapper.map(body.project_root)
    runtime_root = _auto_fix_runtime_root()

    proposal_id = uuid.uuid4().hex[:12]
    proposal = make_proposal(
        proposal_id=proposal_id,
        project_id=project_id,
        sandbox_id=body.sandbox_id,
        failing_step=body.failing_step,
    )
    persist_proposal(project_id, proposal, runtime_root)

    threading.Thread(
        target=_run_proposal_bg,
        args=(proposal, Path(mapped_root), body.exec_cmd, runtime_root),
        daemon=True,
    ).start()

    logger.info(
        "supervisor: auto-fix proposal %s started project_id=%s sandbox_id=%s",
        proposal_id, project_id, body.sandbox_id,
    )
    return {"ok": True, "proposal_id": proposal_id}


@app.get("/auto-fix/{project_id}/proposal/{proposal_id}")
def auto_fix_get_proposal(project_id: str, proposal_id: str):
    from fastapi.responses import JSONResponse

    if not _auto_fix_available:
        return JSONResponse(status_code=503, content={"error": "auto_fix_proposer not available"})

    runtime_root = _auto_fix_runtime_root()
    proposal = load_proposal(project_id, proposal_id, runtime_root)
    if proposal is None:
        return JSONResponse(status_code=404, content={"error": f"proposal not found: {proposal_id}"})
    return proposal


@app.get("/auto-fix/{project_id}/proposals")
def auto_fix_list_proposals(project_id: str):
    from fastapi.responses import JSONResponse

    if not _auto_fix_available:
        return JSONResponse(status_code=503, content={"error": "auto_fix_proposer not available"})

    runtime_root = _auto_fix_runtime_root()
    proposals = _list_proposals_disk(project_id, runtime_root)
    return {"proposals": proposals}


# ── auto-fix loop endpoints ───────────────────────────────────────────────────
#
# The loop applies patches and reruns validation in-place, iterating up to
# max_retries. Each session persists iteration history to disk.

try:
    from auto_fix_loop import (  # noqa: E402
        make_session as _make_session,
        persist_session as _persist_session,
        load_session as _load_session,
        list_sessions as _list_sessions_disk,
        run_auto_fix_loop as _run_auto_fix_loop,
    )
    _auto_fix_loop_available = True
except ImportError:
    _auto_fix_loop_available = False


class AutoFixLoopStartRequest(BaseModel):
    project_root: str
    exec_cmd: str
    sandbox_id: str | None = None
    max_retries: int = Field(default=3, ge=1, le=50)
    failing_step: str | None = None


def _run_loop_bg(
    session: dict,
    project_root: Path,
    exec_cmd: str,
    runtime_root: Path,
) -> None:
    """Background thread: run the full auto-fix loop."""
    try:
        _run_auto_fix_loop(session, project_root, exec_cmd, runtime_root)
    except Exception as exc:
        session["status"] = "error"
        session["error"] = str(exc)
        session["finished_at"] = datetime.datetime.now(
            datetime.timezone.utc
        ).strftime("%Y-%m-%dT%H:%M:%SZ")
        try:
            _persist_session(session["project_id"], session, runtime_root)
        except Exception as persist_exc:
            logger.error(
                "supervisor: failed to persist loop session %s: %s",
                session.get("session_id"), persist_exc,
            )
        logger.error("supervisor: auto-fix loop crashed session=%s: %s", session.get("session_id"), exc)


@app.post("/auto-fix/{project_id}/loop/start")
def auto_fix_loop_start(project_id: str, body: AutoFixLoopStartRequest):
    from fastapi.responses import JSONResponse

    if not _auto_fix_loop_available:
        return JSONResponse(
            status_code=503,
            content={"ok": False, "error": "auto_fix_loop not available"},
        )

    mapped_root = mapper.map(body.project_root)
    runtime_root = _auto_fix_runtime_root()

    session = _make_session(
        project_id=project_id,
        sandbox_id=body.sandbox_id,
        max_retries=body.max_retries,
        failing_step=body.failing_step,
    )
    _persist_session(project_id, session, runtime_root)

    threading.Thread(
        target=_run_loop_bg,
        args=(session, Path(mapped_root), body.exec_cmd, runtime_root),
        daemon=True,
    ).start()

    logger.info(
        "supervisor: auto-fix loop %s started project_id=%s max_retries=%d",
        session["session_id"], project_id, body.max_retries,
    )
    return {"ok": True, "session_id": session["session_id"]}


@app.get("/auto-fix/{project_id}/loop/{session_id}")
def auto_fix_loop_get(project_id: str, session_id: str):
    from fastapi.responses import JSONResponse

    if not _auto_fix_loop_available:
        return JSONResponse(status_code=503, content={"error": "auto_fix_loop not available"})

    runtime_root = _auto_fix_runtime_root()
    session = _load_session(project_id, session_id, runtime_root)
    if session is None:
        return JSONResponse(status_code=404, content={"error": f"session not found: {session_id}"})
    return session


@app.get("/auto-fix/{project_id}/loops")
def auto_fix_loop_list(project_id: str):
    from fastapi.responses import JSONResponse

    if not _auto_fix_loop_available:
        return JSONResponse(status_code=503, content={"error": "auto_fix_loop not available"})

    runtime_root = _auto_fix_runtime_root()
    sessions = _list_sessions_disk(project_id, runtime_root)
    return {"sessions": sessions}


# ── workspace ─────────────────────────────────────────────────────────────────
#
# Architecture:
#   Frontend → Control API /projects/{id}/workspace/* (proxy)
#            → Supervisor /workspace/projects/{id}/* (this section)
#            → Anthropic API (httpx, ANTHROPIC_API_KEY)
#            → existing Supervisor capabilities for confirmed actions
#
# Security:
#   - Deny by default: only explicitly listed capabilities may be executed.
#   - Every mutating action requires an opaque action_id issued at proposal time.
#   - Action IDs are validated for project match before execution.
#   - Secrets are never forwarded to AI prompts or returned in responses.

_pending_workspace_actions: dict[str, dict] = {}
_pending_workspace_issues: dict[str, dict] = {}
_workspace_lock = threading.Lock()

# Per-project redeployment locks (in-memory; protects one Supervisor process/worker only)
_workspace_redeploy_locks: dict[str, threading.Lock] = {}
_workspace_redeploy_locks_mutex = threading.Lock()

# Background deployment job registry keyed by deployment_id (UUID)
_deployment_jobs: dict[str, dict] = {}
_deployment_jobs_lock = threading.Lock()

# Recovery session state — keyed by ticket_id / proposal_id / session_id
_active_sessions: dict[str, RecoverySession] = {}   # ticket_id → session
_proposals: dict[str, object] = {}                   # proposal_id → RecoveryProposal
_results: dict[str, RecoveryResult] = {}             # session_id → RecoveryResult
_session_lock = threading.Lock()


def _load_workspace_projects_config() -> dict:
    """Load workspace_projects.yml; return {} on missing file or parse error."""
    config_path = os.environ.get(
        "WORKSPACE_PROJECTS_CONFIG",
        str(Path(__file__).parent / "workspace_projects.yml"),
    )
    try:
        import yaml as _yaml
        with open(config_path, encoding="utf-8") as fh:
            data = _yaml.safe_load(fh)
            return data if isinstance(data, dict) else {}
    except FileNotFoundError:
        return {}
    except Exception as exc:
        logger.warning("workspace: failed to load projects config %s: %s", config_path, exc)
        return {}


def _git_has_local_changes(repo_path: str) -> bool:
    """Return True if the repo has uncommitted changes. Raises on error."""
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=repo_path,
        timeout=10,
        capture_output=True,
        text=True,
    )
    return bool(result.stdout.strip())

_WORKSPACE_CAPABILITIES: dict[str, dict] = {
    "restart_daemon": {
        "description": "Restart the project daemon",
        "confirmation_required": True,
    },
    "rerun_dependency_analysis": {
        "description": "Rerun dependency analysis for the project",
        "confirmation_required": True,
    },
    "resume_execution": {
        "description": "Resume ticket execution (restart daemon)",
        "confirmation_required": True,
    },
    "redeploy_project": {
        "description": "Pull the latest code and rebuild/restart selected services",
        "confirmation_required": True,
    },
    "recover_ticket": {
        "description": "Diagnose and recover a blocked ticket",
        "confirmation_required": True,
    },
}

_WORKSPACE_SYSTEM_PROMPT = """\
You are an AI assistant embedded in AI Dev Factory, a platform that manages \
AI-driven software development workflows through GitHub issues and a controlled pipeline.
Your role is to help users understand and operate their project.

ALLOWED:
- Answer questions about project status, tickets, workflow, configuration, and logs.
- Diagnose blocked tickets or execution problems.
- Propose GitHub issue creation for feature requests or bug fixes (never implement directly).
- Propose platform actions from the ALLOWED_CAPABILITIES list (require user confirmation).

FORBIDDEN:
- Do not write, suggest, or generate production source code.
- Do not create commits, branches, or pull requests.
- Do not bypass the GitHub issue workflow.
- Do not include secrets, tokens, or credentials in any response.
- Do not invent capability names not listed in ALLOWED_CAPABILITIES.

ALLOWED_CAPABILITIES:
- restart_daemon: Restart the project daemon
- rerun_dependency_analysis: Rerun dependency analysis
- resume_execution: Resume ticket execution
- redeploy_project: Pull latest code and rebuild/restart backend and/or frontend services.
  The branch is always the project's configured default branch (do not include a branch param).
  Params: pull (bool, default true), components (array, values: "backend", "frontend").
  proposed_action format: {"capability": "redeploy_project", "description": "...",
    "params": {"pull": true, "components": ["backend", "frontend"]}}
- recover_ticket: Diagnose and recover a blocked ticket (use when user says "unblock", "stuck", "blocked ticket", or similar)

RESPONSE FORMAT — respond with a valid JSON object and nothing else:
{
  "reply": "<natural language response to the user>",
  "intent": "informational" | "actionable" | "functional_dev",
  "proposed_action": null | {"capability": "<key>", "description": "<what will happen>",
                              "params": <optional object, only for redeploy_project>},
  "issue_draft": null | {"title": "<short title>", "body": "<markdown body>"},
  "confirmation_required": false | true
}

Rules:
- intent=informational: answer the question; proposed_action=null, issue_draft=null, confirmation_required=false.
- intent=actionable: describe the action; proposed_action={capability, description}, confirmation_required=true, issue_draft=null.
- intent=functional_dev: explain this belongs in an issue; issue_draft={title, body}, confirmation_required=true, proposed_action=null.
- For requests outside ALLOWED_CAPABILITIES: use intent=informational and explain why it cannot be done.
"""


class WorkspaceChatRequest(BaseModel):
    message: str
    conversation_history: list[dict] = Field(default_factory=list)


class WorkspaceActionConfirmRequest(BaseModel):
    action_id: str


class WorkspaceIssueConfirmRequest(BaseModel):
    draft_id: str


def _workspace_project_context(project_id: str) -> str:
    """Build a compact project context string for the AI system prompt."""
    parts: list[str] = [f"project_id: {project_id}"]

    state = _project_daemon_states.get(project_id)
    if state is not None:
        running = state.pid is not None and _is_alive(state.pid)
        parts.append(f"daemon: {'running (pid=' + str(state.pid) + ')' if running else 'stopped'}")
    else:
        parts.append("daemon: unknown")

    project_root_str = _lookup_project_root_from_control_api(project_id)
    if project_root_str:
        project_root = Path(mapper.map(project_root_str))
        parts.append(f"project_root: {project_root}")

        tickets_dir = project_root / "tickets"
        if tickets_dir.exists():
            ticket_files = sorted(tickets_dir.glob("*.md"))
            parts.append(f"tickets: {len(ticket_files)} total")
            for tf in ticket_files[:10]:
                try:
                    first = tf.read_text(encoding="utf-8", errors="replace").splitlines()[0][:80]
                    parts.append(f'  - ticket "{tf.stem}": {first}')
                except OSError:
                    parts.append(f'  - ticket "{tf.stem}": (unreadable)')

    # Active ticket and recovery state
    active_ticket_id = _resolve_active_ticket_id(project_id)
    if active_ticket_id:
        parts.append(f"active_ticket_id: {active_ticket_id}")
        if project_root_str:
            project_root = Path(mapper.map(project_root_str))
            state_file = project_root / "runs" / active_ticket_id / "state.json"
            try:
                state_data = json.loads(state_file.read_text(encoding="utf-8"))
                parts.append(f"ticket_state: {state_data.get('state', 'unknown')}")
                if state_data.get("blocked_stage"):
                    parts.append(f"blocked_stage: {state_data['blocked_stage']}")
            except (OSError, json.JSONDecodeError):
                pass
        with _session_lock:
            if active_ticket_id in _active_sessions:
                parts.append(f"recovery_in_progress: true")

    return "\n".join(parts)


def _resolve_active_ticket_id(project_id: str) -> str | None:
    """Return the ticket_id of the currently active (non-terminal) ticket, or None."""
    runs_dir = _project_runs_dir(project_id)
    if not runs_dir.exists():
        return None

    # Prefer a ticket with a daemon.lock (actively running)
    for ticket_dir in runs_dir.iterdir():
        if not ticket_dir.is_dir():
            continue
        if (ticket_dir / "daemon.lock").exists():
            state_file = ticket_dir / "state.json"
            try:
                state_data = json.loads(state_file.read_text(encoding="utf-8"))
                if state_data.get("state") not in _TERMINAL_TICKET_STATES:
                    return ticket_dir.name
            except (OSError, json.JSONDecodeError):
                pass

    # Fall back to most recently updated non-terminal ticket
    candidates: list[tuple[float, str]] = []
    for ticket_dir in runs_dir.iterdir():
        if not ticket_dir.is_dir():
            continue
        state_file = ticket_dir / "state.json"
        try:
            state_data = json.loads(state_file.read_text(encoding="utf-8"))
            if state_data.get("state") not in _TERMINAL_TICKET_STATES:
                candidates.append((state_file.stat().st_mtime, ticket_dir.name))
        except (OSError, json.JSONDecodeError):
            pass

    if candidates:
        candidates.sort(reverse=True)
        return candidates[0][1]
    return None


def _read_ticket_artifacts(project_root: Path, ticket_id: str) -> dict[str, bool]:
    """Return a mapping of artifact name → exists (bool) for the ticket."""
    artifact_paths = _artifact_paths_for_ticket(project_root, ticket_id)
    return {name: path.exists() for name, path in artifact_paths.items()}


def _read_ticket_logs(project_root: Path, ticket_id: str) -> str:
    """Return the last 4000 chars of the runtime log for the ticket."""
    log_file = _ticket_run_dir(project_root, ticket_id) / "runtime.log"
    try:
        return log_file.read_text(encoding="utf-8", errors="replace")[-4000:]
    except OSError:
        return ""


def _prepare_recovery(project_id: str, project_root: Path) -> dict:
    """Diagnose the blocked ticket and build a recovery proposal.

    Returns a proposed_action dict on success, or {"error": "<code>"} on failure.
    Performs zero disk mutations.
    """
    import uuid as _uuid
    from recovery import RecoveryProposal  # local import to avoid circular at module level

    ticket_id = _resolve_active_ticket_id(project_id)
    if ticket_id is None:
        return {"error": "NO_ACTIVE_TICKET"}

    # Atomic check-and-create
    with _session_lock:
        if ticket_id in _active_sessions:
            existing = _active_sessions[ticket_id]
            return {"error": "RECOVERY_IN_PROGRESS", "session_id": existing.session_id}
        session = RecoverySession(
            session_id=str(_uuid.uuid4()),
            proposal_id=None,
            ticket_id=ticket_id,
            stage=RecoveryStage.DIAGNOSING,
            iteration_count=0,
            operations_log=[],
        )
        _active_sessions[ticket_id] = session

    try:
        # Read state — no mutations
        run_dir = _ticket_run_dir(project_root, ticket_id)
        state_file = run_dir / "state.json"
        try:
            state_data = json.loads(state_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            state_data = {}

        artifacts = _read_ticket_artifacts(project_root, ticket_id)
        logs = _read_ticket_logs(project_root, ticket_id)

        blocker = classify_blocker(state_data, artifacts, logs)
        ops = build_recovery_plan(blocker, state_data)
        fingerprint = compute_state_fingerprint(ticket_id, project_root, ops)

        proposal_id = str(_uuid.uuid4())
        proposal = RecoveryProposal(
            proposal_id=proposal_id,
            project_id=project_id,
            ticket_id=ticket_id,
            blocker_class=blocker,
            operations=ops,
            state_fingerprint=fingerprint,
            created_at=datetime.datetime.now(datetime.timezone.utc),
            status=ProposalStatus.AWAITING_CONFIRMATION,
        )

        with _session_lock:
            _proposals[proposal_id] = proposal
            session.proposal_id = proposal_id
            session.stage = RecoveryStage.PLAN_READY

        logger.info(
            "recovery: prepared session=%s ticket=%s blocker=%s ops=%d",
            session.session_id, ticket_id, blocker.value, len(ops),
        )

        return {
            "capability": "recover_ticket",
            "action_id": proposal_id,
            "ticket_id": ticket_id,
            "blocker_class": blocker.value,
            "operations": [
                {"name": op.name, "description": op.description, "risk_level": op.risk_level, "params": op.params}
                for op in ops
            ],
            "current_state": state_data.get("state", ""),
            "blocked_stage": fingerprint.blocked_stage,
        }

    except Exception as exc:
        logger.error("recovery: prepare failed ticket=%s: %s", ticket_id, exc, exc_info=True)
        with _session_lock:
            _active_sessions.pop(ticket_id, None)
        return {"error": "PREPARE_FAILED", "detail": str(exc)}


def _execute_recovery(proposal_id: str, project_root: Path) -> dict:
    """Revalidate the proposal and execute recovery operations.

    Returns a recovery_report dict or {"error": "<code>"} dict.
    Callers should return HTTP 409 when error == "PROPOSAL_STALE".
    """
    from recovery import RecoveryProposal  # local import

    proposal = _proposals.get(proposal_id)
    if proposal is None:
        return {"error": "PROPOSAL_NOT_FOUND"}
    if proposal.status != ProposalStatus.AWAITING_CONFIRMATION:
        return {"error": "PROPOSAL_NOT_FOUND"}

    ticket_id = proposal.ticket_id

    with _session_lock:
        session = _active_sessions.get(ticket_id)
        if session is None:
            return {"error": "SESSION_NOT_FOUND"}

    # Revalidate fingerprint
    new_fingerprint = compute_state_fingerprint(ticket_id, project_root, list(proposal.operations))
    if new_fingerprint.version != proposal.state_fingerprint.version:
        proposal.status = ProposalStatus.INVALIDATED
        session.stage = RecoveryStage.FAILED
        with _session_lock:
            _active_sessions.pop(ticket_id, None)
        _results[session.session_id] = RecoveryResult(
            session_id=session.session_id,
            proposal_id=proposal_id,
            ticket_id=ticket_id,
            stage=RecoveryStage.FAILED,
            root_cause="Ticket state changed after preparation",
            ops_performed=[],
            new_ticket_state=new_fingerprint.ticket_state,
            bug_issue_url=None,
            error="PROPOSAL_STALE",
        )
        return {
            "error": "PROPOSAL_STALE",
            "detail": "Ticket state changed after preparation. Re-run diagnosis.",
        }

    with _session_lock:
        proposal.status = ProposalStatus.EXECUTING
    session.stage = RecoveryStage.APPLYING_FIX

    bug_issue_url: str | None = None
    last_error: str | None = None

    try:
        # Execute operations from the immutable stored proposal
        has_retry_op = any(op.name == "retry_stage" for op in proposal.operations)
        all_ops_succeeded = True

        for op in proposal.operations:
            # Double-check allowlist (defence in depth)
            if op.name not in ALLOWLISTED_RECOVERY_OPS:
                raise ValueError(f"op {op.name!r} not in allowlist")

            op_result = apply_recovery_op(op, project_root, proposal.project_id, ticket_id)
            session.operations_log.append({
                "op_name": op_result.op_name,
                "success": op_result.success,
                "detail": op_result.detail,
                "mutated": op_result.mutated,
            })

            if not op_result.success:
                all_ops_succeeded = False
                session.iteration_count += 1
                last_error = op_result.detail
                if session.iteration_count >= MAX_RECOVERY_ITERATIONS:
                    session.stage = RecoveryStage.FAILED
                    break

        # If any op failed, treat the recovery as failed regardless of iteration count
        if session.stage != RecoveryStage.FAILED and not all_ops_succeeded:
            session.stage = RecoveryStage.FAILED

        if has_retry_op and session.stage != RecoveryStage.FAILED:
            session.stage = RecoveryStage.RETRYING_STAGE

        if session.stage not in (RecoveryStage.FAILED,):
            session.stage = RecoveryStage.VERIFYING
            expected_next = proposal.state_fingerprint.ticket_state
            advanced, current_state = verify_ticket_progress(ticket_id, project_root, expected_next)

            if advanced:
                session.stage = RecoveryStage.RECOVERED

                # Bug issue creation for PRODUCT_BUG blocker
                if proposal.blocker_class == BlockerClass.PRODUCT_BUG:
                    sig = compute_bug_signature(
                        project_id=proposal.project_id,
                        blocker_class=proposal.blocker_class,
                        failed_stage=proposal.state_fingerprint.blocked_stage,
                        error_code=None,
                        affected_component=None,
                    )
                    project_root_str = _lookup_project_root_from_control_api(proposal.project_id)
                    repo = None
                    if project_root_str:
                        try:
                            r = subprocess.run(
                                ["gh", "repo", "view", "--json", "nameWithOwner", "-q", ".nameWithOwner"],
                                cwd=str(project_root),
                                capture_output=True, text=True, timeout=10,
                            )
                            if r.returncode == 0:
                                repo = r.stdout.strip()
                        except Exception:
                            pass
                    if repo:
                        existing_url = search_existing_bug_issues(repo, sig)
                        if existing_url:
                            bug_issue_url = existing_url
                        else:
                            error_summary = last_error or "See operations log"
                            try:
                                bug_issue_url = create_bug_issue(repo, session, proposal, error_summary)
                            except Exception as exc:
                                logger.error("recovery: create_bug_issue failed: %s", exc)
                        if bug_issue_url:
                            session.stage = RecoveryStage.BUG_REPORTED
            else:
                # State did not advance
                needs_user = proposal.blocker_class in (
                    BlockerClass.MISSING_APPROVAL,
                    BlockerClass.USER_DECISION_REQUIRED,
                    BlockerClass.WORKING_TREE_CONFLICT,
                )
                session.stage = RecoveryStage.NEEDS_USER_INPUT if needs_user else RecoveryStage.FAILED

        # Determine final state
        final_state_file = _ticket_run_dir(project_root, ticket_id) / "state.json"
        try:
            final_state = json.loads(final_state_file.read_text(encoding="utf-8")).get("state")
        except (OSError, json.JSONDecodeError):
            final_state = None

        result = RecoveryResult(
            session_id=session.session_id,
            proposal_id=proposal_id,
            ticket_id=ticket_id,
            stage=session.stage,
            root_cause=proposal.blocker_class.value,
            ops_performed=list(session.operations_log),
            new_ticket_state=final_state,
            bug_issue_url=bug_issue_url,
            error=last_error,
        )

    except ValueError as exc:
        session.stage = RecoveryStage.FAILED
        result = RecoveryResult(
            session_id=session.session_id,
            proposal_id=proposal_id,
            ticket_id=ticket_id,
            stage=RecoveryStage.FAILED,
            root_cause=proposal.blocker_class.value,
            ops_performed=list(session.operations_log),
            new_ticket_state=None,
            bug_issue_url=None,
            error=str(exc),
        )
    finally:
        proposal.status = ProposalStatus.COMPLETED if session.stage not in (RecoveryStage.FAILED,) else ProposalStatus.INVALIDATED
        with _session_lock:
            _active_sessions.pop(ticket_id, None)
        _results[session.session_id] = result

    return {
        "recovery_report": {
            "session_id": result.session_id,
            "ticket_id": result.ticket_id,
            "stage": result.stage.value,
            "root_cause": result.root_cause,
            "ops_performed": result.ops_performed,
            "new_ticket_state": result.new_ticket_state,
            "bug_issue_url": result.bug_issue_url,
            "error": result.error,
        }
    }


def _call_workspace_ai(project_context: str, messages: list[dict]) -> dict:
    """Call the Anthropic API via httpx and return a parsed workspace response."""
    try:
        import httpx as _httpx
    except ImportError:
        return {
            "reply": "httpx is not installed; cannot reach the AI provider.",
            "intent": "informational",
            "proposed_action": None,
            "issue_draft": None,
            "confirmation_required": False,
        }

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return {
            "reply": "ANTHROPIC_API_KEY is not configured; AI workspace unavailable.",
            "intent": "informational",
            "proposed_action": None,
            "issue_draft": None,
            "confirmation_required": False,
        }

    model = os.environ.get("WORKSPACE_AI_MODEL", "claude-sonnet-4-6")
    system = f"{_WORKSPACE_SYSTEM_PROMPT}\n\n## Live project context\n\n{project_context}"

    try:
        resp = _httpx.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={"model": model, "max_tokens": 2048, "system": system, "messages": messages},
            timeout=60.0,
        )
        resp.raise_for_status()
        text = resp.json()["content"][0]["text"]
    except Exception as exc:
        logger.error("workspace: AI call failed: %s", exc, exc_info=True)
        return {
            "reply": "The AI assistant is temporarily unavailable. Please try again in a moment.",
            "intent": "informational",
            "proposed_action": None,
            "issue_draft": None,
            "confirmation_required": False,
        }

    import re as _re
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        m = _re.search(r"\{[\s\S]*\}", text)
        if m:
            try:
                return json.loads(m.group())
            except json.JSONDecodeError:
                pass
    return {
        "reply": text,
        "intent": "informational",
        "proposed_action": None,
        "issue_draft": None,
        "confirmation_required": False,
    }


def _execute_workspace_capability(project_id: str, capability: str) -> tuple[bool, str]:
    """Execute an allowlisted capability. Returns (ok, message)."""
    if capability in ("restart_daemon", "resume_execution"):
        state = _project_daemon_states.get(project_id)
        if state and state.pid and _is_alive(state.pid):
            try:
                os.kill(state.pid, signal.SIGTERM)
            except OSError:
                pass
            state.pid = None
            _remove_project_pid_file(project_id)

        project_root_str = _lookup_project_root_from_control_api(project_id)
        if not project_root_str:
            return False, "project not found in registry"

        project_root = Path(mapper.map(project_root_str))
        project_runtime_root = _project_runtime_root(project_id)
        exec_cmd = _project_daemon_exec_cmds.get(project_id, _daemon_exec_cmd)
        logs_dir = _project_logs_dir(project_id)
        logs_dir.mkdir(parents=True, exist_ok=True)
        log = _project_log_path(project_id)
        worktrees_dir = _project_worktrees_dir(project_id)
        started_at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        cmd = [
            sys.executable, str(_run_daemon_path()),
            "--exec-cmd", exec_cmd,
            "--poll-issues", "--issue-label", "ai-ready",
            "--auto-commit", "--auto-push", "--auto-include-code",
            "--worktrees-dir", str(worktrees_dir),
            "--project-root", str(project_root),
            "--project", project_id,
        ]
        tools_dir = _project_root_dir / "tools" / "agent_runner"
        if str(tools_dir) not in sys.path:
            sys.path.insert(0, str(tools_dir))
        import runtime_settings as _rs
        cmd += _rs.daemon_max_workers_argv_for_project(project_id, project_runtime_root=project_runtime_root)

        try:
            env = {
                **os.environ,
                "PYTHONDONTWRITEBYTECODE": "1",
                "AI_DEV_FACTORY_RUNTIME_ROOT": str(project_runtime_root),
                "PROJECT_NAME": project_id,
            }
            with open(log, "a", encoding="utf-8") as fh:
                fh.write(f"[{started_at}] workspace: (re)starting daemon for {project_id}\n")
                proc = subprocess.Popen(
                    cmd, cwd=str(project_root), stdout=fh, stderr=fh,
                    start_new_session=True, env=env,
                )
            _project_daemon_procs[project_id] = proc
            new_state = _project_daemon_states.setdefault(project_id, DaemonState())
            new_state.pid = proc.pid
            new_state.started_at = started_at
            new_state.exit_unexpected = False
            _write_project_pid_file(project_id, proc.pid, started_at, exec_cmd, new_state.restart_policy)
            logger.info("workspace: daemon started pid=%d project_id=%s", proc.pid, project_id)
            return True, f"daemon started (pid={proc.pid})"
        except OSError as exc:
            return False, str(exc)

    elif capability == "rerun_dependency_analysis":
        project_root_str = _lookup_project_root_from_control_api(project_id)
        if not project_root_str:
            return False, "project not found in registry"
        exec_cmd = _project_daemon_exec_cmds.get(project_id, _daemon_exec_cmd)
        lock = _get_analysis_lock(project_id)
        if not lock.acquire(blocking=False):
            return False, "analysis already running"
        try:
            if _analysis_current_pid(project_id) is not None:
                return False, "analysis already running"
            started_at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            log = _analysis_log_path(project_id)
            cmd = [
                sys.executable, str(_run_analysis_path()),
                "--project-root", mapper.map(project_root_str),
                "--project-id", project_id,
                "--exec-cmd", exec_cmd,
                "--worktrees-dir", str(_worktrees_dir()),
            ]
            env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
            with open(log, "a", encoding="utf-8") as fh:
                fh.write(f"[{started_at}] workspace: rerunning dependency analysis for {project_id}\n")
                proc = subprocess.Popen(
                    cmd, cwd=str(_project_root()), stdout=fh, stderr=fh,
                    start_new_session=True, env=env,
                )
            pid_path = _analysis_pid_path(project_id)
            pid_path.parent.mkdir(parents=True, exist_ok=True)
            pid_path.write_text(json.dumps({"pid": proc.pid, "started_at": started_at}), encoding="utf-8")
            logger.info("workspace: analysis started pid=%d project_id=%s", proc.pid, project_id)
            return True, f"dependency analysis started (pid={proc.pid})"
        except OSError as exc:
            return False, str(exc)
        finally:
            lock.release()

    return False, f"unknown capability: {capability!r}"


@app.post("/workspace/projects/{project_id}/chat")
def workspace_chat(project_id: str, body: WorkspaceChatRequest):
    messages: list[dict] = []
    for turn in body.conversation_history[-20:]:
        role = turn.get("role", "")
        content = turn.get("content", "")
        if role in ("user", "assistant") and isinstance(content, str) and content.strip():
            messages.append({"role": role, "content": content})
    messages.append({"role": "user", "content": body.message})

    context = _workspace_project_context(project_id)
    result = _call_workspace_ai(context, messages)

    intent = result.get("intent", "informational")
    proposed_action = result.get("proposed_action")
    issue_draft = result.get("issue_draft")

    if intent == "actionable" and isinstance(proposed_action, dict):
        capability = proposed_action.get("capability", "")
        if capability not in _WORKSPACE_CAPABILITIES:
            result["reply"] += f"\n\n(Capability '{capability}' is not in the allowlist.)"
            result["proposed_action"] = None
            result["confirmation_required"] = False
            result["intent"] = "informational"
        elif capability == "redeploy_project":
            config = _load_workspace_projects_config()
            project_block = config.get("projects", {}).get(project_id)
            if project_block is None or "redeploy" not in project_block:
                result["reply"] += "\n\n(Project not configured for redeployment.)"
                result["proposed_action"] = None
                result["confirmation_required"] = False
                result["intent"] = "informational"
            else:
                configured_components = set(project_block["redeploy"].keys())
                raw_params = proposed_action.get("params") or {}
                raw_components = raw_params.get("components")
                if not raw_components or not isinstance(raw_components, list):
                    raw_components = list(configured_components)
                unknown = [c for c in raw_components if c not in configured_components]
                if unknown:
                    result["reply"] += f"\n\n(Requested component(s) {unknown} not configured for this project.)"
                    result["proposed_action"] = None
                    result["confirmation_required"] = False
                    result["intent"] = "informational"
                else:
                    pull = raw_params.get("pull", True)
                    if not isinstance(pull, bool):
                        pull = True
                    components = [c for c in raw_components if c in configured_components]

                    has_dirty_warning = None
                    repo_path = project_block.get("repository_path", "")
                    try:
                        has_dirty_warning = _git_has_local_changes(repo_path)
                    except Exception:
                        has_dirty_warning = None

                    configured_branch = project_block.get("default_branch", "")
                    safe_identifier = project_block.get("display_name") or project_id

                    action_id = str(uuid.uuid4())
                    with _workspace_lock:
                        _pending_workspace_actions[action_id] = {
                            "project_id": project_id,
                            "capability": "redeploy_project",
                            "description": proposed_action.get("description", ""),
                            "params": {"pull": pull, "components": components},
                            "has_dirty_warning": has_dirty_warning,
                            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                        }
                    result["proposed_action"] = {
                        "capability": "redeploy_project",
                        "description": proposed_action.get("description", ""),
                        "action_id": action_id,
                        "project_id": project_id,
                        "safe_identifier": safe_identifier,
                        "configured_branch": configured_branch,
                        "pull": pull,
                        "components": components,
                        "has_dirty_warning": has_dirty_warning,
                    }
                    result["confirmation_required"] = True
        elif capability == "recover_ticket":
            # Run diagnosis immediately; proposal_id becomes the action_id
            project_root_str = _lookup_project_root_from_control_api(project_id)
            if not project_root_str:
                result["reply"] += "\n\n(Project not found; cannot diagnose.)"
                result["proposed_action"] = None
                result["intent"] = "informational"
                result["confirmation_required"] = False
            else:
                project_root = Path(mapper.map(project_root_str))
                prep = _prepare_recovery(project_id, project_root)
                if "error" in prep:
                    err = prep["error"]
                    result["reply"] += f"\n\n(Recovery unavailable: {err}.)"
                    result["proposed_action"] = None
                    result["intent"] = "informational"
                    result["confirmation_required"] = False
                else:
                    proposal_id = prep["action_id"]
                    result["proposed_action"] = prep
                    result["confirmation_required"] = True
                    with _workspace_lock:
                        _pending_workspace_actions[proposal_id] = {
                            "project_id": project_id,
                            "capability": "recover_ticket",
                            "proposal_id": proposal_id,
                            "description": proposed_action.get("description", "Diagnose and recover blocked ticket"),
                            "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                        }
        else:
            action_id = str(uuid.uuid4())
            with _workspace_lock:
                _pending_workspace_actions[action_id] = {
                    "project_id": project_id,
                    "capability": capability,
                    "description": proposed_action.get("description", ""),
                    "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                }
            result["proposed_action"]["action_id"] = action_id
            result["confirmation_required"] = True

    if intent == "functional_dev" and isinstance(issue_draft, dict):
        draft_id = str(uuid.uuid4())
        with _workspace_lock:
            _pending_workspace_issues[draft_id] = {
                "project_id": project_id,
                "title": issue_draft.get("title", ""),
                "body": issue_draft.get("body", ""),
                "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            }
        result["issue_draft"]["draft_id"] = draft_id
        result["confirmation_required"] = True

    logger.info(
        "workspace: chat project_id=%s intent=%s confirmation_required=%s",
        project_id, intent, result.get("confirmation_required"),
    )
    return result


@app.post("/workspace/projects/{project_id}/actions/confirm")
def workspace_action_confirm(project_id: str, body: WorkspaceActionConfirmRequest):
    from fastapi.responses import JSONResponse

    with _workspace_lock:
        action = _pending_workspace_actions.get(body.action_id)

    if action is None:
        return JSONResponse(status_code=404, content={"detail": "action not found or expired"})
    if action["project_id"] != project_id:
        return JSONResponse(status_code=403, content={"detail": "action project mismatch"})

    capability = action["capability"]
    if capability not in _WORKSPACE_CAPABILITIES:
        return JSONResponse(status_code=403, content={"detail": f"capability '{capability}' not allowed"})

    logger.info(
        "workspace: confirming capability=%s project_id=%s action_id=%s",
        capability, project_id, body.action_id,
    )

    if capability == "redeploy_project":
        params = action.get("params", {})
        components = params.get("components", [])
        pull = params.get("pull", True)

        lock = _get_redeploy_lock(project_id)
        acquired = lock.acquire(blocking=False)
        if not acquired:
            return JSONResponse(status_code=409, content={"detail": "deployment already running for project"})

        deployment_id = str(uuid.uuid4())
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with _deployment_jobs_lock:
            _deployment_jobs[deployment_id] = {
                "deployment_id": deployment_id,
                "project_id": project_id,
                "status": "RUNNING",
                "stage": None,
                "started_at": now,
                "completed_at": None,
                "result_message": None,
                "deployed_sha": None,
                "preview_url": None,
                "error_stage": None,
                "error_excerpt": None,
            }

        with _workspace_lock:
            _pending_workspace_actions.pop(body.action_id, None)

        threading.Thread(
            target=_run_redeploy_job,
            args=(deployment_id, project_id, components, pull, lock),
            daemon=True,
        ).start()

        return {"ok": True, "deployment_id": deployment_id, "status": "RUNNING"}

    elif capability == "recover_ticket":
        proposal_id = action.get("proposal_id", body.action_id)
        project_root_str = _lookup_project_root_from_control_api(project_id)
        if not project_root_str:
            return JSONResponse(status_code=404, content={"detail": f"project {project_id!r} not found"})
        project_root = Path(mapper.map(project_root_str))
        exec_result = _execute_recovery(proposal_id, project_root)
        with _workspace_lock:
            _pending_workspace_actions.pop(body.action_id, None)
        if exec_result.get("error") == "PROPOSAL_STALE":
            return JSONResponse(status_code=409, content=exec_result)
        if exec_result.get("error"):
            return JSONResponse(status_code=500, content={"detail": exec_result["error"]})
        return {"ok": True, "capability": capability, **exec_result}

    ok, message = _execute_workspace_capability(project_id, capability)

    with _workspace_lock:
        _pending_workspace_actions.pop(body.action_id, None)

    if ok:
        return {"ok": True, "capability": capability, "result": message}
    return JSONResponse(status_code=500, content={"detail": message})


def _run_redeploy_job(
    deployment_id: str,
    project_id: str,
    components: list,
    pull: bool,
    lock: threading.Lock,
) -> None:
    """Background deployment job. Holds *lock* on entry; always releases in finally."""

    def _fail(stage: str, excerpt: str = "") -> None:
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with _deployment_jobs_lock:
            _deployment_jobs[deployment_id].update({
                "status": "FAILED",
                "error_stage": stage,
                "error_excerpt": excerpt[:500],
                "completed_at": now,
            })

    def _set_stage(stage: str) -> None:
        with _deployment_jobs_lock:
            _deployment_jobs[deployment_id]["stage"] = stage

    try:
        config = _load_workspace_projects_config()
        project_block = config.get("projects", {}).get(project_id)
        if project_block is None:
            _fail("CONFIG_MISSING")
            return

        repo_path = project_block["repository_path"]
        default_branch = project_block["default_branch"]
        allow_dirty = project_block.get("allow_dirty", False)
        service_map = {k: v["service"] for k, v in project_block["redeploy"].items()}
        preview_url = project_block.get("preview_url")

        if not Path(repo_path).exists():
            _fail("PATH_NOT_FOUND", f"repository path does not exist: {repo_path}")
            return

        unknown_components = [c for c in components if c not in service_map]
        if unknown_components:
            _fail("INVALID_COMPONENT", f"unknown components: {unknown_components}")
            return

        # Branch check
        try:
            branch_result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=repo_path,
                timeout=10,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError:
            _fail("GIT_NOT_FOUND", "git executable not found")
            return
        except subprocess.TimeoutExpired:
            _fail("BRANCH_CHECK_TIMEOUT", "git branch --show-current timed out")
            return
        if branch_result.returncode != 0:
            _fail("BRANCH_CHECK", branch_result.stderr[:500])
            return
        current_branch = branch_result.stdout.strip()
        if current_branch != default_branch:
            _fail(
                "BRANCH_MISMATCH",
                f"current branch '{current_branch}' differs from configured branch '{default_branch}'",
            )
            return

        # Dirty check
        try:
            dirty = _git_has_local_changes(repo_path)
        except FileNotFoundError:
            _fail("GIT_NOT_FOUND", "git executable not found")
            return
        except subprocess.TimeoutExpired:
            _fail("DIRTY_CHECK_TIMEOUT", "git status timed out")
            return
        if dirty and not allow_dirty:
            _fail("DIRTY_CHECK", "uncommitted changes detected")
            return

        # Pull
        if pull:
            _set_stage("PULLING")
            logger.info("redeploy %s: stage=PULLING", project_id)
            try:
                pull_result = subprocess.run(
                    ["git", "pull", "--ff-only", "origin", default_branch],
                    cwd=repo_path,
                    timeout=120,
                    capture_output=True,
                    text=True,
                )
            except subprocess.TimeoutExpired:
                _fail("PULLING", "git pull timed out after 120 s")
                return
            except FileNotFoundError:
                _fail("PULLING", "git executable not found")
                return
            if pull_result.returncode != 0:
                _fail("PULLING", pull_result.stderr[:500])
                return

        # Build/restart each component
        for component in components:
            service = service_map[component]
            stage = f"BUILDING_{component}"
            _set_stage(stage)
            logger.info("redeploy %s: stage=%s service=%s", project_id, stage, service)
            try:
                compose_result = subprocess.run(
                    ["docker", "compose", "up", "-d", "--build", service],
                    cwd=repo_path,
                    timeout=300,
                    capture_output=True,
                    text=True,
                )
            except subprocess.TimeoutExpired:
                _fail(stage, "docker compose timed out after 300 s")
                return
            except FileNotFoundError:
                _fail(stage, "docker executable not found")
                return
            if compose_result.returncode != 0:
                _fail(stage, compose_result.stderr[:500])
                return

        # Get deployed SHA (non-fatal)
        deployed_sha = None
        try:
            sha_result = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                cwd=repo_path,
                timeout=10,
                capture_output=True,
                text=True,
            )
            if sha_result.returncode == 0:
                deployed_sha = sha_result.stdout.strip()
        except Exception:
            pass

        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        component_list = ", ".join(components)
        with _deployment_jobs_lock:
            _deployment_jobs[deployment_id].update({
                "status": "SUCCEEDED",
                "stage": "SUCCEEDED",
                "completed_at": now,
                "deployed_sha": deployed_sha,
                "preview_url": preview_url,
                "result_message": f"Deployed {component_list} (sha={deployed_sha})",
            })
        logger.info("redeploy %s: stage=SUCCEEDED sha=%s", project_id, deployed_sha)

    except Exception as exc:
        logger.exception("redeploy %s: unexpected exception", project_id)
        now = datetime.datetime.now(datetime.timezone.utc).isoformat()
        with _deployment_jobs_lock:
            job = _deployment_jobs.get(deployment_id, {})
            if job.get("status") != "FAILED":
                _deployment_jobs[deployment_id].update({
                    "status": "FAILED",
                    "error_stage": "INTERNAL_ERROR",
                    "error_excerpt": str(exc)[:500],
                    "completed_at": now,
                })
    finally:
        lock.release()


@app.get("/workspace/projects/{project_id}/deployments/{deployment_id}")
def workspace_get_deployment(project_id: str, deployment_id: str):
    from fastapi.responses import JSONResponse as _JSONResponse

    with _deployment_jobs_lock:
        job = _deployment_jobs.get(deployment_id)

    if job is None or job.get("project_id") != project_id:
        return _JSONResponse(status_code=404, content={"detail": "deployment not found"})
    return job


@app.post("/workspace/projects/{project_id}/issues/confirm")
def workspace_issue_confirm(project_id: str, body: WorkspaceIssueConfirmRequest):
    from fastapi.responses import JSONResponse

    with _workspace_lock:
        draft = _pending_workspace_issues.get(body.draft_id)

    if draft is None:
        return JSONResponse(status_code=404, content={"detail": "issue draft not found or expired"})
    if draft["project_id"] != project_id:
        return JSONResponse(status_code=403, content={"detail": "draft project mismatch"})

    title = draft.get("title", "").strip()
    body_text = draft.get("body", "").strip()
    if not title or not body_text:
        return JSONResponse(status_code=422, content={"detail": "issue draft has empty title or body"})

    project_root_str = _lookup_project_root_from_control_api(project_id)
    if project_root_str is None:
        return JSONResponse(status_code=404, content={"detail": f"project {project_id!r} not found"})
    project_root = Path(mapper.map(project_root_str))

    logger.info(
        "workspace: creating GitHub issue project_id=%s draft_id=%s title=%r",
        project_id, body.draft_id, title,
    )

    try:
        result = subprocess.run(
            ["gh", "issue", "create", "--title", title, "--body", body_text],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        return JSONResponse(status_code=504, content={"detail": "gh issue create timed out"})
    except FileNotFoundError:
        return JSONResponse(status_code=503, content={"detail": "gh CLI not found"})

    if result.returncode != 0:
        return JSONResponse(
            status_code=500,
            content={"detail": f"gh issue create failed: {result.stderr.strip()}"},
        )

    issue_url = result.stdout.strip()
    import re as _re
    issue_number = None
    m = _re.search(r"/(\d+)$", issue_url)
    if m:
        issue_number = int(m.group(1))

    with _workspace_lock:
        _pending_workspace_issues.pop(body.draft_id, None)

    logger.info("workspace: issue created url=%s project_id=%s", issue_url, project_id)
    return {"ok": True, "issue_url": issue_url, "issue_number": issue_number}


@app.get("/api/recovery/{session_id}")
def recovery_result(session_id: str):
    """Poll for a recovery session result. Returns 404 while in progress, 200 when terminal."""
    from fastapi.responses import JSONResponse

    result = _results.get(session_id)
    if result is None:
        return JSONResponse(status_code=404, content={"detail": "session in progress or not found"})

    return {
        "session_id": result.session_id,
        "proposal_id": result.proposal_id,
        "ticket_id": result.ticket_id,
        "stage": result.stage.value,
        "root_cause": result.root_cause,
        "ops_performed": result.ops_performed,
        "new_ticket_state": result.new_ticket_state,
        "bug_issue_url": result.bug_issue_url,
        "error": result.error,
    }
