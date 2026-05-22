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
from pydantic import BaseModel

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


@app.post("/sandbox/start")
def sandbox_start(body: SandboxStartRequest):
    from fastapi.responses import JSONResponse

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
        sandbox_root = str(_runtime_root() / "sandboxes")
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
        cmd = [
            sys.executable,
            str(_run_sandbox_path()),
            "--project-root", mapped_root,
            "--project-id", body.project_id,
        ]
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}

        try:
            with open(log, "a", encoding="utf-8") as log_fh:
                log_fh.write(
                    f"[{started_at}] supervisor spawning sandbox validation for {body.project_id}\n"
                    f"  project_root(container)={body.project_root}\n"
                    f"  project_root(host)={mapped_root}\n"
                    f"  sandbox_root(host)={sandbox_root}\n"
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
                "supervisor: sandbox started pid=%d project_id=%s",
                proc.pid, body.project_id,
            )
            return {"ok": True, "pid": proc.pid}
        except OSError as exc:
            return {"ok": False, "error": str(exc)}
    finally:
        lock.release()


@app.get("/sandbox/{project_id}/status")
def sandbox_status_endpoint(project_id: str):
    state = _read_sandbox_state(project_id)
    if state.get("state") == "running":
        if _sandbox_current_pid(project_id) is None:
            # Worker process disappeared without finalising state. Don't
            # let the dashboard poll a phantom "running" forever.
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


@app.post("/sandbox/{project_id}/stop")
def sandbox_stop(project_id: str):
    pid = _sandbox_current_pid(project_id)
    if pid is None:
        return {"ok": False, "error": "not_running"}
    try:
        os.kill(pid, signal.SIGTERM)
        try:
            _sandbox_pid_path(project_id).unlink()
        except OSError:
            pass
        logger.info(
            "supervisor: sandbox stopped pid=%d project_id=%s", pid, project_id
        )
        return {"ok": True}
    except OSError as exc:
        return {"ok": False, "error": str(exc)}


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
    exec_cmd: str = "claude --dangerously-skip-permissions"
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

        any_invalid = any(not p["valid"] for p in validated)
        proposal["status"] = "rejected" if any_invalid else "ready"
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
