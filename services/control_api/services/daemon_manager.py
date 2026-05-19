"""Daemon lifecycle management via PID file at runs/daemon.pid."""

from __future__ import annotations

import datetime
import json
import logging
import os
import re
import signal
import subprocess
import sys
from pathlib import Path

from ..models.schemas import ActionResult, DaemonStatus


logger = logging.getLogger("control-api")

_TOOLS_DIR = Path(__file__).resolve().parents[3] / "tools" / "agent_runner"
_RUN_DAEMON = _TOOLS_DIR / "run_daemon.py"

_PID_FILENAME = "daemon.pid"
_LOG_FILENAME = "daemon.log"
_TICKET_RE = re.compile(r"^T\d{3,}$")


def _pid_path(project_root: Path) -> Path:
    return project_root / "runs" / _PID_FILENAME


def _log_path(project_root: Path) -> Path:
    return project_root / "runs" / _LOG_FILENAME


def _read_pid_file(project_root: Path) -> dict | None:
    path = _pid_path(project_root)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _write_pid_file(project_root: Path, pid: int, started_at: str) -> None:
    path = _pid_path(project_root)
    path.write_text(
        json.dumps({"pid": pid, "started_at": started_at}),
        encoding="utf-8",
    )


def _remove_pid_file(project_root: Path) -> None:
    try:
        _pid_path(project_root).unlink()
    except OSError:
        pass


def _is_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False


def _last_heartbeat(project_root: Path) -> str | None:
    path = _log_path(project_root)
    if not path.exists():
        return None
    try:
        mtime = path.stat().st_mtime
        return datetime.datetime.fromtimestamp(mtime, tz=datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except OSError:
        return None


def _current_ticket(project_root: Path) -> str | None:
    runs = project_root / "runs"
    if not runs.exists():
        return None
    for ticket_dir in sorted(runs.iterdir(), reverse=True):
        if not _TICKET_RE.match(ticket_dir.name):
            continue
        state_file = ticket_dir / "state.json"
        if not state_file.exists():
            continue
        try:
            data = json.loads(state_file.read_text(encoding="utf-8"))
            if "RUNNING" in (data.get("state") or ""):
                return ticket_dir.name
        except (json.JSONDecodeError, OSError):
            continue
    return None


def get_status(project_root: Path) -> DaemonStatus:
    data = _read_pid_file(project_root)
    if data is None:
        return DaemonStatus(running=False)
    pid = data.get("pid")
    if not isinstance(pid, int):
        _remove_pid_file(project_root)
        return DaemonStatus(running=False)
    if not _is_alive(pid):
        _remove_pid_file(project_root)
        return DaemonStatus(running=False)
    return DaemonStatus(
        running=True,
        pid=pid,
        started_at=data.get("started_at"),
        last_heartbeat=_last_heartbeat(project_root),
        current_ticket=_current_ticket(project_root),
    )


def get_activity(project_root: Path, lines: int = 50) -> list[str]:
    path = _log_path(project_root)
    if not path.exists():
        return []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
        all_lines = [ln for ln in text.splitlines() if ln.strip()]
        return all_lines[-lines:]
    except OSError:
        return []


def start(project_root: Path, exec_cmd: str) -> ActionResult:
    logger.info("api: daemon start requested")
    status = get_status(project_root)
    if status.running:
        return ActionResult(ok=False, message=f"daemon already running (pid={status.pid})")

    started_at = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    log = _log_path(project_root)
    try:
        with open(log, "a", encoding="utf-8") as log_fh:
            proc = subprocess.Popen(
                [
                    sys.executable,
                    str(_RUN_DAEMON),
                    "--exec-cmd",
                    exec_cmd,
                    "--poll-issues",
                    "--issue-label",
                    "ai-ready",
                    "--auto-commit",
                    "--auto-push",
                    "--worktrees-dir",
                    str(project_root / "worktrees"),
                ],
                cwd=project_root,
                stdout=log_fh,
                stderr=log_fh,
                start_new_session=True,
            )
        _write_pid_file(project_root, proc.pid, started_at)
        logger.info("api: daemon started pid=%d", proc.pid)
        return ActionResult(ok=True, message=f"daemon started (pid={proc.pid})")
    except OSError as exc:
        return ActionResult(ok=False, message=str(exc))


def stop(project_root: Path) -> ActionResult:
    logger.info("api: daemon stop requested")
    status = get_status(project_root)
    if not status.running or status.pid is None:
        return ActionResult(ok=False, message="daemon is not running")
    try:
        os.kill(status.pid, signal.SIGTERM)
        _remove_pid_file(project_root)
        logger.info("api: daemon stopped pid=%d", status.pid)
        return ActionResult(ok=True, message=f"daemon stopped (pid={status.pid})")
    except OSError as exc:
        return ActionResult(ok=False, message=str(exc))


def restart(project_root: Path, exec_cmd: str) -> ActionResult:
    logger.info("api: daemon restart requested")
    stop_result = stop(project_root)
    if not stop_result.ok and "not running" not in stop_result.message:
        return stop_result
    return start(project_root, exec_cmd)
