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

    Resolution order:
    1. RUNTIME_BASE_ROOT env var (explicit config)
    2. Parent of AI_DEV_FACTORY_RUNTIME_ROOT (derived from existing config)
    3. ~/runtime (safe local fallback — never /runtime)
    """
    base = os.environ.get("RUNTIME_BASE_ROOT")
    if base:
        return Path(base).expanduser().resolve()
    factory_root = os.environ.get("AI_DEV_FACTORY_RUNTIME_ROOT")
    if factory_root:
        return Path(factory_root).parent
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
_daemon_exec_cmd: str = "claude --dangerously-skip-permissions"


# ── Daemon spawn helper ───────────────────────────────────────────────────────

def _spawn_daemon(exec_cmd: str) -> tuple[int | None, str | None, str | None]:
    """Spawn the daemon. Returns (pid, started_at, error_str)."""
    global _daemon_proc
    started_at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    log = _log_path()
    log.parent.mkdir(parents=True, exist_ok=True)
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
    try:
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

    ai_dev_dir = project_root / ".ai-dev-factory"
    project_yml = ai_dev_dir / "project.yml"
    if not project_yml.exists():
        try:
            ai_dev_dir.mkdir(exist_ok=True)
            bootstrapped_at = datetime.datetime.now(datetime.timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )
            project_yml.write_text(
                f"name: {body.project_id}\nstack: {stack}\nbootstrapped_at: {bootstrapped_at}\n",
                encoding="utf-8",
            )
        except PermissionError as exc:
            return JSONResponse(
                status_code=422,
                content={"error": "permission_denied", "detail": str(exc)},
            )

    return {
        "project_id": body.project_id,
        "project_root": str(project_root),
        "runtime_root": str(project_runtime_root),
        "stack": stack,
        "runs_dir": str(runs_dir),
        "logs_dir": str(logs_dir),
        "state_dir": str(state_dir),
        "worktrees_dir": str(worktrees_dir),
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
    exec_cmd: str = "claude --dangerously-skip-permissions"
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

    project_root = Path(project_root_str)
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
    ]
    try:
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
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
