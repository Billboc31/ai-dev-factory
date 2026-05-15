"""Controlled subprocess calls to existing workflow scripts."""

from __future__ import annotations

import logging
import re
import subprocess
import sys
from pathlib import Path

from ..models.schemas import ActionResult


logger = logging.getLogger("control-api")

TICKET_ID_RE = re.compile(r"^T\d{3,}$")

_TOOLS_DIR = Path(__file__).resolve().parents[3] / "tools" / "agent_runner"
_RUN_TICKET = _TOOLS_DIR / "run_ticket.py"
_RUN_ISSUE_INTAKE = _TOOLS_DIR / "run_issue_intake.py"


def _validate_ticket_id(ticket_id: str) -> None:
    if not TICKET_ID_RE.fullmatch(ticket_id):
        raise ValueError(f"invalid ticket_id: {ticket_id!r}")


def _run(args: list[str], cwd: Path | None = None) -> ActionResult:
    try:
        result = subprocess.run(
            args,
            text=True,
            capture_output=True,
            check=False,
            cwd=cwd,
        )
        ok = result.returncode == 0
        return ActionResult(
            ok=ok,
            message="ok" if ok else "subprocess failed",
            returncode=result.returncode,
            stdout=result.stdout or None,
            stderr=result.stderr or None,
        )
    except OSError as exc:
        return ActionResult(ok=False, message=str(exc), returncode=-1)


def run_next(ticket_id: str, project_root: Path) -> ActionResult:
    _validate_ticket_id(ticket_id)
    logger.info("api: run-next requested for %s", ticket_id)
    return _run(
        [sys.executable, str(_RUN_TICKET), ticket_id, "--auto"],
        cwd=project_root,
    )


def approve_plan(ticket_id: str, project_root: Path) -> ActionResult:
    _validate_ticket_id(ticket_id)
    logger.info("api: POST /tickets/%s/approve-plan", ticket_id)
    return _run(
        [sys.executable, str(_RUN_TICKET), ticket_id, "--approve-plan"],
        cwd=project_root,
    )


def request_plan_fix(ticket_id: str, project_root: Path) -> ActionResult:
    _validate_ticket_id(ticket_id)
    logger.info("api: POST /tickets/%s/request-plan-fix", ticket_id)
    return _run(
        [sys.executable, str(_RUN_TICKET), ticket_id, "--request-plan-fix"],
        cwd=project_root,
    )


def approve_implementation(ticket_id: str, project_root: Path) -> ActionResult:
    _validate_ticket_id(ticket_id)
    logger.info("api: POST /tickets/%s/approve-implementation", ticket_id)
    return _run(
        [sys.executable, str(_RUN_TICKET), ticket_id, "--approve-implementation"],
        cwd=project_root,
    )


def request_implementation_fix(ticket_id: str, project_root: Path) -> ActionResult:
    _validate_ticket_id(ticket_id)
    logger.info("api: POST /tickets/%s/request-implementation-fix", ticket_id)
    return _run(
        [sys.executable, str(_RUN_TICKET), ticket_id, "--request-implementation-fix"],
        cwd=project_root,
    )


def commit_ticket(ticket_id: str, project_root: Path) -> ActionResult:
    _validate_ticket_id(ticket_id)
    logger.info("api: POST /tickets/%s/commit", ticket_id)
    return _run(
        [sys.executable, str(_RUN_TICKET), ticket_id, "--commit", "--include-code"],
        cwd=project_root,
    )


def push_ticket(ticket_id: str, project_root: Path) -> ActionResult:
    _validate_ticket_id(ticket_id)
    logger.info("api: POST /tickets/%s/push", ticket_id)
    return _run(
        [sys.executable, str(_RUN_TICKET), ticket_id, "--push"],
        cwd=project_root,
    )


def checkpoint_ticket(ticket_id: str, project_root: Path) -> ActionResult:
    _validate_ticket_id(ticket_id)
    logger.info("api: checkpoint requested for %s", ticket_id)
    return _run(
        [sys.executable, str(_RUN_TICKET), ticket_id, "--commit", "--include-code"],
        cwd=project_root,
    )


def archive_ticket(ticket_id: str, project_root: Path) -> ActionResult:
    _validate_ticket_id(ticket_id)
    logger.info("api: POST /tickets/%s/archive", ticket_id)
    return _run(
        [sys.executable, str(_RUN_TICKET), ticket_id, "--archive-daemon"],
        cwd=project_root,
    )


def run_issue_intake(issue_number: int, project_root: Path) -> ActionResult:
    logger.info("api: POST /issues/intake issue=%d", issue_number)
    return _run(
        [sys.executable, str(_RUN_ISSUE_INTAKE), str(issue_number)],
        cwd=project_root,
    )
