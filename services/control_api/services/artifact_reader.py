"""Read-only access to runs/ artifacts. Never writes."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from ..models.schemas import RetryInfo, TicketSummary, TimelineStep, TimelineResponse
from .runtime_resolver import resolve_ticket_run_dir, resolve_runs_dir


TICKET_ID_RE = re.compile(r"^T\d{3,}$")


def _runs_root(project_root: Path) -> Path:
    return resolve_runs_dir(project_root)


def _last_log_line(log_file: Path) -> str | None:
    if not log_file.exists():
        return None
    try:
        text = log_file.read_text(encoding="utf-8")
        for line in reversed(text.splitlines()):
            stripped = line.strip()
            if stripped:
                return stripped
    except OSError:
        pass
    return None


def _read_retry_state(run_dir: Path) -> RetryInfo | None:
    path = run_dir / "retry-state.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return RetryInfo(
            failure_class=data.get("failure_class"),
            retry_count=int(data.get("retry_count", 0)),
            cooldown_until=data.get("cooldown_until"),
        )
    except (json.JSONDecodeError, OSError, ValueError):
        return None


def _read_last_error(run_dir: Path) -> str | None:
    log_file = run_dir / "runtime.log"
    if not log_file.exists():
        return None
    try:
        text = log_file.read_text(encoding="utf-8")
        for line in reversed(text.splitlines()):
            if "ERROR" in line and line.strip():
                return line.strip()
    except OSError:
        pass
    return None


_CONFLICT_STATES = frozenset({
    "CONFLICT_RESOLUTION_NEEDED",
    "CONFLICT_RESOLVING",
    "CONFLICT_RESOLVED_REVIEW_NEEDED",
    "CONFLICT_RESOLUTION_FAILED",
})


def _conflict_fields(data: dict, run_dir: Path | None = None) -> dict:
    """Extract conflict metadata from a state.json dict. All fields nullable."""
    state = data.get("state", "")
    conflict_status = state if state in _CONFLICT_STATES else None

    resolution_summary: str | None = None
    conflict_test_result: str | None = None
    if run_dir is not None:
        res_path = run_dir / "conflict" / "resolution.md"
        if res_path.exists():
            try:
                resolution_summary = res_path.read_text(encoding="utf-8")
            except OSError:
                pass
        test_path = run_dir / "conflict" / "test-report.md"
        if test_path.exists():
            try:
                conflict_test_result = test_path.read_text(encoding="utf-8")
            except OSError:
                pass

    return {
        "conflict_status": conflict_status,
        "conflicted_files": data.get("conflicted_files") or None,
        "conflict_detected_at": data.get("conflict_detected_at") or None,
        "pre_conflict_state": data.get("pre_conflict_state") or None,
        "resolution_summary": resolution_summary,
        "conflict_test_result": conflict_test_result,
    }


def validate_ticket_id(ticket_id: str) -> None:
    if not TICKET_ID_RE.fullmatch(ticket_id):
        raise ValueError(f"invalid ticket_id: {ticket_id!r}")


def _get_run_dir(project_root: Path, ticket_id: str, worktrees_dir: Path | None) -> Path:
    return resolve_ticket_run_dir(ticket_id, _runs_root(project_root), worktrees_dir)


def list_tickets(project_root: Path, worktrees_dir: Path | None = None) -> list[TicketSummary]:
    runs = _runs_root(project_root)
    seen: dict[str, TicketSummary] = {}

    # Worktrees first — most current state for active tickets
    if worktrees_dir and worktrees_dir.exists():
        for wt_dir in sorted(worktrees_dir.iterdir()):
            if not wt_dir.is_dir() or not TICKET_ID_RE.fullmatch(wt_dir.name):
                continue
            ticket_id = wt_dir.name
            run_dir = wt_dir / "runs" / ticket_id
            state_file = run_dir / "state.json"
            if not state_file.exists():
                continue
            try:
                data = json.loads(state_file.read_text(encoding="utf-8"))
                seen[ticket_id] = TicketSummary(
                    ticket_id=data.get("ticket_id", ticket_id),
                    state=data.get("state", "UNKNOWN"),
                    branch=data.get("branch"),
                    issue_number=data.get("issue_number"),
                    updated_at=data.get("updated_at"),
                    last_log=_last_log_line(run_dir / "runtime.log"),
                    **_conflict_fields(data, run_dir),
                )
            except (json.JSONDecodeError, OSError):
                continue

    # Main repo runs/ — tickets without worktrees
    if runs.exists():
        for entry in sorted(runs.iterdir()):
            if not entry.is_dir() or not TICKET_ID_RE.fullmatch(entry.name):
                continue
            if entry.name in seen:
                continue
            state_file = entry / "state.json"
            if not state_file.exists():
                continue
            try:
                data = json.loads(state_file.read_text(encoding="utf-8"))
                seen[entry.name] = TicketSummary(
                    ticket_id=data.get("ticket_id", entry.name),
                    state=data.get("state", "UNKNOWN"),
                    branch=data.get("branch"),
                    issue_number=data.get("issue_number"),
                    updated_at=data.get("updated_at"),
                    last_log=_last_log_line(entry / "runtime.log"),
                    **_conflict_fields(data, entry),
                )
            except (json.JSONDecodeError, OSError):
                continue

    return list(seen.values())


def get_ticket(project_root: Path, ticket_id: str, worktrees_dir: Path | None = None) -> TicketSummary | None:
    validate_ticket_id(ticket_id)
    run_dir = _get_run_dir(project_root, ticket_id, worktrees_dir)
    state_file = run_dir / "state.json"
    if not state_file.exists():
        return None
    try:
        data = json.loads(state_file.read_text(encoding="utf-8"))
        return TicketSummary(
            ticket_id=data.get("ticket_id", ticket_id),
            state=data.get("state", "UNKNOWN"),
            branch=data.get("branch"),
            issue_number=data.get("issue_number"),
            updated_at=data.get("updated_at"),
            retry_info=_read_retry_state(run_dir),
            **_conflict_fields(data, run_dir),
        )
    except (json.JSONDecodeError, OSError):
        return None


def get_ticket_state(project_root: Path, ticket_id: str, worktrees_dir: Path | None = None) -> dict[str, Any] | None:
    validate_ticket_id(ticket_id)
    run_dir = _get_run_dir(project_root, ticket_id, worktrees_dir)
    state_file = run_dir / "state.json"
    if not state_file.exists():
        return None
    try:
        return json.loads(state_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def get_ticket_logs(project_root: Path, ticket_id: str, worktrees_dir: Path | None = None) -> str | None:
    validate_ticket_id(ticket_id)
    run_dir = _get_run_dir(project_root, ticket_id, worktrees_dir)
    log_file = run_dir / "runtime.log"
    if not log_file.exists():
        return None
    try:
        return log_file.read_text(encoding="utf-8")
    except OSError:
        return None


def get_ticket_artifacts(project_root: Path, ticket_id: str, worktrees_dir: Path | None = None) -> dict[str, Any]:
    validate_ticket_id(ticket_id)
    run_dir = _get_run_dir(project_root, ticket_id, worktrees_dir)
    if not run_dir.exists():
        return {}
    artifacts: dict[str, Any] = {}
    for path in sorted(run_dir.rglob("*")):
        if path.is_file():
            rel = str(path.relative_to(run_dir))
            artifacts[rel] = True
    return artifacts


def _read_artifact(project_root: Path, ticket_id: str, filename: str, worktrees_dir: Path | None = None) -> str | None:
    validate_ticket_id(ticket_id)
    run_dir = _get_run_dir(project_root, ticket_id, worktrees_dir)
    path = run_dir / filename
    if not path.exists() or not path.is_file():
        return None
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return None


_STEPS = [
    ("issue_intake", "Issue intake"),
    ("plan", "Plan"),
    ("plan_review", "Plan review"),
    ("implementation", "Implementation"),
    ("implementation_review", "Implementation review"),
    ("fix_loop", "Fix loop"),
    ("tests", "Tests"),
]

_STEP_AGENTS = [None, "planner", None, "coder", "reviewer", "coder", "tester"]

# Maps state -> (statuses list, human_gate)
_STATUS_MAP: dict[str, tuple[list[str], bool]] = {
    "INIT": (
        ["done", "running", "pending", "pending", "pending", "pending", "pending"], False),
    "PLAN_REVIEW_NEEDED": (
        ["done", "done", "waiting_human", "pending", "pending", "pending", "pending"], True),
    "PLAN_FIX_REQUIRED": (
        ["done", "running", "pending", "pending", "pending", "pending", "pending"], False),
    "PLAN_APPROVED": (
        ["done", "done", "done", "running", "pending", "pending", "pending"], False),
    "IMPLEMENTATION_REVIEW_NEEDED": (
        ["done", "done", "done", "done", "running", "pending", "pending"], False),
    "IMPLEMENTATION_FIX_REQUIRED": (
        ["done", "done", "done", "done", "done", "running", "pending"], False),
    "IMPLEMENTATION_APPROVED": (
        ["done", "done", "done", "done", "done", "skipped", "running"], False),
    "CONFLICT_RESOLUTION_NEEDED": (
        ["done", "done", "done", "done", "done", "done", "waiting_human"], True),
    "CONFLICT_RESOLVING": (
        ["done", "done", "done", "done", "done", "done", "running"], False),
    "CONFLICT_RESOLVED_REVIEW_NEEDED": (
        ["done", "done", "done", "done", "done", "done", "waiting_human"], True),
    "CONFLICT_RESOLUTION_FAILED": (
        ["done", "done", "done", "done", "done", "done", "failed"], True),
}


def _build_steps(statuses: list[str]) -> tuple[list[TimelineStep], str | None]:
    steps = []
    current_agent = None
    for i, (step_id, label) in enumerate(_STEPS):
        st = statuses[i]
        agent = _STEP_AGENTS[i] if st == "running" else None
        if agent:
            current_agent = agent
        steps.append(TimelineStep(id=step_id, label=label, status=st, agent=agent))
    return steps, current_agent


def get_ticket_timeline(project_root: Path, ticket_id: str, worktrees_dir: Path | None = None) -> TimelineResponse | None:
    validate_ticket_id(ticket_id)
    run_dir = _get_run_dir(project_root, ticket_id, worktrees_dir)
    state_file = run_dir / "state.json"
    if not state_file.exists():
        return None
    try:
        data = json.loads(state_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None

    state = data.get("state", "UNKNOWN")
    last_event = _last_log_line(run_dir / "runtime.log")

    if state == "TEST_COMPLETE":
        has_retry = (run_dir / "retry-state.json").exists()
        fix_status = "done" if has_retry else "skipped"
        statuses = ["done", "done", "done", "done", "done", fix_status, "done"]
        steps, current_agent = _build_steps(statuses)
        human_gate = True
    elif state in _STATUS_MAP:
        statuses, human_gate = _STATUS_MAP[state]
        steps, current_agent = _build_steps(statuses)
    else:
        statuses = ["done"] + ["pending"] * 6
        steps, current_agent = _build_steps(statuses)
        human_gate = False

    return TimelineResponse(
        ticket_id=ticket_id,
        current_state=state,
        current_agent=current_agent,
        human_gate=human_gate,
        last_event=last_event,
        steps=steps,
        retry_info=_read_retry_state(run_dir),
        last_error=_read_last_error(run_dir),
    )


def get_ticket_plan(project_root: Path, ticket_id: str, worktrees_dir: Path | None = None) -> str | None:
    return _read_artifact(project_root, ticket_id, "plan.md", worktrees_dir)


def get_ticket_review(project_root: Path, ticket_id: str, worktrees_dir: Path | None = None) -> str | None:
    return _read_artifact(project_root, ticket_id, "reviews/review.md", worktrees_dir)


def get_ticket_tests(project_root: Path, ticket_id: str, worktrees_dir: Path | None = None) -> str | None:
    return _read_artifact(project_root, ticket_id, "tests/test-report.md", worktrees_dir)
