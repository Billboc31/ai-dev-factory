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
from pathlib import Path

from fastapi import FastAPI
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


def _run_daemon_path() -> Path:
    return Path(__file__).resolve().parents[2] / "tools" / "agent_runner" / "run_daemon.py"


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
