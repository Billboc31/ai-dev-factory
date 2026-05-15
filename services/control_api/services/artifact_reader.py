"""Read-only access to runs/ artifacts. Never writes."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from ..models.schemas import TicketSummary, TimelineStep, TimelineResponse


TICKET_ID_RE = re.compile(r"^T\d{3,}$")


def _runs_root(project_root: Path) -> Path:
    return project_root / "runs"


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


def validate_ticket_id(ticket_id: str) -> None:
    if not TICKET_ID_RE.fullmatch(ticket_id):
        raise ValueError(f"invalid ticket_id: {ticket_id!r}")


def list_tickets(project_root: Path) -> list[TicketSummary]:
    runs = _runs_root(project_root)
    tickets: list[TicketSummary] = []
    if not runs.exists():
        return tickets
    for entry in sorted(runs.iterdir()):
        if not entry.is_dir() or not TICKET_ID_RE.fullmatch(entry.name):
            continue
        state_file = entry / "state.json"
        if not state_file.exists():
            continue
        try:
            data = json.loads(state_file.read_text(encoding="utf-8"))
            tickets.append(TicketSummary(
                ticket_id=data.get("ticket_id", entry.name),
                state=data.get("state", "UNKNOWN"),
                branch=data.get("branch"),
                issue_number=data.get("issue_number"),
                updated_at=data.get("updated_at"),
                last_log=_last_log_line(entry / "runtime.log"),
            ))
        except (json.JSONDecodeError, OSError):
            continue
    return tickets


def get_ticket(project_root: Path, ticket_id: str) -> TicketSummary | None:
    validate_ticket_id(ticket_id)
    state_file = _runs_root(project_root) / ticket_id / "state.json"
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
        )
    except (json.JSONDecodeError, OSError):
        return None


def get_ticket_state(project_root: Path, ticket_id: str) -> dict[str, Any] | None:
    validate_ticket_id(ticket_id)
    state_file = _runs_root(project_root) / ticket_id / "state.json"
    if not state_file.exists():
        return None
    try:
        return json.loads(state_file.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def get_ticket_logs(project_root: Path, ticket_id: str) -> str | None:
    validate_ticket_id(ticket_id)
    log_file = _runs_root(project_root) / ticket_id / "runtime.log"
    if not log_file.exists():
        return None
    try:
        return log_file.read_text(encoding="utf-8")
    except OSError:
        return None


def get_ticket_artifacts(project_root: Path, ticket_id: str) -> dict[str, Any]:
    validate_ticket_id(ticket_id)
    run_dir = _runs_root(project_root) / ticket_id
    if not run_dir.exists():
        return {}
    artifacts: dict[str, Any] = {}
    for path in sorted(run_dir.rglob("*")):
        if path.is_file():
            rel = str(path.relative_to(run_dir))
            artifacts[rel] = True
    return artifacts


def _read_artifact(project_root: Path, ticket_id: str, filename: str) -> str | None:
    validate_ticket_id(ticket_id)
    path = _runs_root(project_root) / ticket_id / filename
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

_STEP_AGENTS = [None, "planner", None, "coder", None, "coder", "tester"]

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
        ["done", "done", "done", "done", "waiting_human", "pending", "pending"], True),
    "IMPLEMENTATION_FIX_REQUIRED": (
        ["done", "done", "done", "done", "done", "running", "pending"], False),
    "IMPLEMENTATION_APPROVED": (
        ["done", "done", "done", "done", "done", "skipped", "running"], False),
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


def get_ticket_timeline(project_root: Path, ticket_id: str) -> TimelineResponse | None:
    validate_ticket_id(ticket_id)
    run_dir = _runs_root(project_root) / ticket_id
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
        human_gate = False
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
    )


def get_ticket_plan(project_root: Path, ticket_id: str) -> str | None:
    return _read_artifact(project_root, ticket_id, "plan.md")


def get_ticket_review(project_root: Path, ticket_id: str) -> str | None:
    return _read_artifact(project_root, ticket_id, "reviews/review.md")


def get_ticket_tests(project_root: Path, ticket_id: str) -> str | None:
    return _read_artifact(project_root, ticket_id, "tests/test-report.md")
