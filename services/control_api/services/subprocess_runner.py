"""Controlled subprocess calls to existing workflow scripts."""

from __future__ import annotations

import json
import logging
import re
import subprocess
import sys
from pathlib import Path

from ..models.schemas import ActionResult
from .runtime_resolver import resolve_ticket_cwd, resolve_ticket_run_dir


logger = logging.getLogger("control-api")

TICKET_ID_RE = re.compile(r"^T\d{3,}$")

_TOOLS_DIR = Path(__file__).resolve().parents[3] / "tools" / "agent_runner"
_RUN_TICKET = _TOOLS_DIR / "run_ticket.py"
_RUN_ISSUE_INTAKE = _TOOLS_DIR / "run_issue_intake.py"
_RUN_CONFLICT_RESOLVER = _TOOLS_DIR / "run_conflict_resolver.py"


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


def _resolve_action_cwd(
    ticket_id: str,
    project_root: Path,
    worktrees_dir: Path | None,
) -> tuple[Path, str | None]:
    """Return (cwd, error_message). error_message is set if the context is unsafe.

    If no worktree exists and the repo is on the wrong branch, refuses with an
    actionable message instead of letting run_ticket.py fail mid-flight.
    """
    cwd = resolve_ticket_cwd(ticket_id, project_root, worktrees_dir)

    if cwd == project_root:
        # Legacy fallback — verify current branch matches state.branch
        runs_dir = project_root / "runs"
        run_dir = resolve_ticket_run_dir(ticket_id, runs_dir, worktrees_dir)
        state_file = run_dir / "state.json"
        if state_file.exists():
            try:
                state = json.loads(state_file.read_text(encoding="utf-8"))
                expected_branch = state.get("branch", "")
                if expected_branch and expected_branch != "main":
                    result = subprocess.run(
                        ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                        capture_output=True, text=True, check=False,
                        cwd=str(project_root),
                    )
                    if result.returncode == 0:
                        current = result.stdout.strip()
                        if current != expected_branch:
                            return project_root, (
                                f"no active worktree for {ticket_id} — "
                                f"current branch {current!r} does not match "
                                f"state branch {expected_branch!r}; "
                                f"start a worktree or checkout {expected_branch!r} manually"
                            )
            except (json.JSONDecodeError, OSError):
                pass

    return cwd, None


def run_next(ticket_id: str, project_root: Path, worktrees_dir: Path | None = None) -> ActionResult:
    _validate_ticket_id(ticket_id)
    logger.info("api: run-next requested for %s", ticket_id)
    cwd, error = _resolve_action_cwd(ticket_id, project_root, worktrees_dir)
    if error:
        return ActionResult(ok=False, message=error, returncode=-1)
    return _run(
        [sys.executable, str(_RUN_TICKET), ticket_id, "--auto"],
        cwd=cwd,
    )


def approve_plan(ticket_id: str, project_root: Path, worktrees_dir: Path | None = None) -> ActionResult:
    _validate_ticket_id(ticket_id)
    logger.info("api: POST /tickets/%s/approve-plan", ticket_id)
    cwd, error = _resolve_action_cwd(ticket_id, project_root, worktrees_dir)
    if error:
        return ActionResult(ok=False, message=error, returncode=-1)
    return _run(
        [sys.executable, str(_RUN_TICKET), ticket_id, "--approve-plan"],
        cwd=cwd,
    )


def request_plan_fix(ticket_id: str, project_root: Path, worktrees_dir: Path | None = None) -> ActionResult:
    _validate_ticket_id(ticket_id)
    logger.info("api: POST /tickets/%s/request-plan-fix", ticket_id)
    cwd, error = _resolve_action_cwd(ticket_id, project_root, worktrees_dir)
    if error:
        return ActionResult(ok=False, message=error, returncode=-1)
    return _run(
        [sys.executable, str(_RUN_TICKET), ticket_id, "--request-plan-fix"],
        cwd=cwd,
    )


def approve_implementation(ticket_id: str, project_root: Path, worktrees_dir: Path | None = None) -> ActionResult:
    _validate_ticket_id(ticket_id)
    logger.info("api: POST /tickets/%s/approve-implementation", ticket_id)
    cwd, error = _resolve_action_cwd(ticket_id, project_root, worktrees_dir)
    if error:
        return ActionResult(ok=False, message=error, returncode=-1)
    return _run(
        [sys.executable, str(_RUN_TICKET), ticket_id, "--approve-implementation"],
        cwd=cwd,
    )


def request_implementation_fix(ticket_id: str, project_root: Path, worktrees_dir: Path | None = None) -> ActionResult:
    _validate_ticket_id(ticket_id)
    logger.info("api: POST /tickets/%s/request-implementation-fix", ticket_id)
    cwd, error = _resolve_action_cwd(ticket_id, project_root, worktrees_dir)
    if error:
        return ActionResult(ok=False, message=error, returncode=-1)
    return _run(
        [sys.executable, str(_RUN_TICKET), ticket_id, "--request-implementation-fix"],
        cwd=cwd,
    )


def commit_ticket(ticket_id: str, project_root: Path, worktrees_dir: Path | None = None) -> ActionResult:
    _validate_ticket_id(ticket_id)
    logger.info("api: POST /tickets/%s/commit", ticket_id)
    cwd, error = _resolve_action_cwd(ticket_id, project_root, worktrees_dir)
    if error:
        return ActionResult(ok=False, message=error, returncode=-1)
    return _run(
        [sys.executable, str(_RUN_TICKET), ticket_id, "--commit", "--include-code"],
        cwd=cwd,
    )


def push_ticket(ticket_id: str, project_root: Path, worktrees_dir: Path | None = None) -> ActionResult:
    _validate_ticket_id(ticket_id)
    logger.info("api: POST /tickets/%s/push", ticket_id)
    cwd, error = _resolve_action_cwd(ticket_id, project_root, worktrees_dir)
    if error:
        return ActionResult(ok=False, message=error, returncode=-1)
    return _run(
        [sys.executable, str(_RUN_TICKET), ticket_id, "--push"],
        cwd=cwd,
    )


def checkpoint_ticket(ticket_id: str, project_root: Path, worktrees_dir: Path | None = None) -> ActionResult:
    _validate_ticket_id(ticket_id)
    logger.info("api: checkpoint requested for %s", ticket_id)
    cwd, error = _resolve_action_cwd(ticket_id, project_root, worktrees_dir)
    if error:
        return ActionResult(ok=False, message=error, returncode=-1)
    return _run(
        [sys.executable, str(_RUN_TICKET), ticket_id, "--commit", "--include-code"],
        cwd=cwd,
    )


def archive_ticket(ticket_id: str, project_root: Path, worktrees_dir: Path | None = None) -> ActionResult:
    _validate_ticket_id(ticket_id)
    logger.info("api: POST /tickets/%s/archive", ticket_id)
    cwd, error = _resolve_action_cwd(ticket_id, project_root, worktrees_dir)
    if error:
        return ActionResult(ok=False, message=error, returncode=-1)
    return _run(
        [sys.executable, str(_RUN_TICKET), ticket_id, "--archive-daemon"],
        cwd=cwd,
    )


def resolve_conflicts(
    ticket_id: str,
    project_root: Path,
    worktrees_dir: Path | None = None,
    exec_cmd: str = "claude --dangerously-skip-permissions",
) -> ActionResult:
    _validate_ticket_id(ticket_id)
    logger.info("api: resolve-conflicts for %s", ticket_id)
    cwd, error = _resolve_action_cwd(ticket_id, project_root, worktrees_dir)
    if error:
        return ActionResult(ok=False, message=error, returncode=-1)
    return _run(
        [sys.executable, str(_RUN_CONFLICT_RESOLVER), ticket_id, "--exec-cmd", exec_cmd],
        cwd=cwd,
    )


def approve_conflict_resolution(
    ticket_id: str, project_root: Path, worktrees_dir: Path | None = None
) -> ActionResult:
    _validate_ticket_id(ticket_id)
    logger.info("api: approve-conflict-resolution for %s", ticket_id)
    cwd, error = _resolve_action_cwd(ticket_id, project_root, worktrees_dir)
    if error:
        return ActionResult(ok=False, message=error, returncode=-1)
    return _run(
        [sys.executable, str(_RUN_TICKET), ticket_id, "--approve-conflict-resolution"],
        cwd=cwd,
    )


def reject_conflict_resolution(
    ticket_id: str, project_root: Path, worktrees_dir: Path | None = None
) -> ActionResult:
    _validate_ticket_id(ticket_id)
    logger.info("api: reject-conflict-resolution for %s", ticket_id)
    cwd, error = _resolve_action_cwd(ticket_id, project_root, worktrees_dir)
    if error:
        return ActionResult(ok=False, message=error, returncode=-1)
    return _run(
        [sys.executable, str(_RUN_TICKET), ticket_id, "--reject-conflict-resolution"],
        cwd=cwd,
    )


def run_issue_intake(issue_number: int, project_root: Path) -> ActionResult:
    logger.info("api: POST /issues/intake issue=%d", issue_number)
    return _run(
        [sys.executable, str(_RUN_ISSUE_INTAKE), str(issue_number)],
        cwd=project_root,
    )
