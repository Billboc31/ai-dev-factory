"""Host-side supervisor — manages the AI dev factory daemon on the host.

Binds to 127.0.0.1:8090 (localhost only). No auth — localhost trust.
Start via deploy/start_supervisor.sh.
"""

from __future__ import annotations

import datetime
import json
import logging
import os
import signal
import subprocess
import sys
import threading
from pathlib import Path

from fastapi import FastAPI, Query
from pydantic import BaseModel

logger = logging.getLogger("supervisor")

_PID_FILENAME = "daemon.pid"
_LOG_FILENAME = "daemon.log"


def _project_root() -> Path:
    return Path(os.environ.get("AI_DEV_FACTORY_PROJECT_ROOT", Path.cwd()))


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


def _pid_path() -> Path:
    return _runs_dir() / _PID_FILENAME


def _log_path() -> Path:
    return _logs_dir() / _LOG_FILENAME


def _read_pid_file() -> dict | None:
    path = _pid_path()
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _write_pid_file(pid: int, started_at: str) -> None:
    path = _pid_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({"pid": pid, "started_at": started_at}),
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


def _current_pid() -> int | None:
    data = _read_pid_file()
    if data is None:
        return None
    pid = data.get("pid")
    if not isinstance(pid, int):
        return None
    if not _is_alive(pid):
        _remove_pid_file()
        return None
    return pid


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
    return {"status": "ok", "daemon_pid": _current_pid()}


@app.get("/daemon/status")
def daemon_status():
    data = _read_pid_file()
    if data is None:
        return {"running": False, "pid": None, "started_at": None}
    pid = data.get("pid")
    if not isinstance(pid, int) or not _is_alive(pid):
        _remove_pid_file()
        return {"running": False, "pid": None, "started_at": None}
    return {"running": True, "pid": pid, "started_at": data.get("started_at")}


class StartRequest(BaseModel):
    exec_cmd: str = "claude --dangerously-skip-permissions"


@app.post("/daemon/start")
def daemon_start(body: StartRequest = None):  # noqa: B008
    if body is None:
        body = StartRequest()

    pid = _current_pid()
    if pid is not None:
        return {"ok": False, "pid": pid, "error": "already_running"}

    started_at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    log = _log_path()
    log.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        sys.executable,
        str(_run_daemon_path()),
        "--exec-cmd", body.exec_cmd,
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
        _write_pid_file(proc.pid, started_at)
        logger.info("supervisor: daemon started pid=%d", proc.pid)
        return {"ok": True, "pid": proc.pid}
    except OSError as exc:
        return {"ok": False, "pid": None, "error": str(exc)}


@app.post("/daemon/stop")
def daemon_stop():
    data = _read_pid_file()
    if data is None:
        return {"ok": False, "error": "not_running"}
    pid = data.get("pid")
    if not isinstance(pid, int) or not _is_alive(pid):
        _remove_pid_file()
        return {"ok": False, "error": "not_running"}
    try:
        os.kill(pid, signal.SIGTERM)
        _remove_pid_file()
        logger.info("supervisor: daemon stopped pid=%d", pid)
        return {"ok": True}
    except OSError as exc:
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

        started_at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        log = _analysis_log_path(body.project_id)
        cmd = [
            sys.executable,
            str(_run_analysis_path()),
            "--project-root", body.project_root,
            "--project-id", body.project_id,
            "--exec-cmd", body.exec_cmd,
        ]
        env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
        try:
            with open(log, "a", encoding="utf-8") as log_fh:
                log_fh.write(
                    f"[{started_at}] supervisor spawning analysis for {body.project_id}\n"
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
            pid_path = _analysis_pid_path(body.project_id)
            pid_path.parent.mkdir(parents=True, exist_ok=True)
            pid_path.write_text(
                json.dumps({"pid": proc.pid, "started_at": started_at}),
                encoding="utf-8",
            )
            logger.info("supervisor: analysis started pid=%d project_id=%s", proc.pid, body.project_id)
            return {"ok": True, "pid": proc.pid}
        except OSError as exc:
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
            return {"ok": True, "pid": proc.pid}
        except OSError as exc:
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
