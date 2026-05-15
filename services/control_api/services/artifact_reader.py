"""Read-only access to runs/ artifacts. Never writes."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from ..models.schemas import TicketSummary


TICKET_ID_RE = re.compile(r"^T\d{3,}$")


def _runs_root(project_root: Path) -> Path:
    return project_root / "runs"


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


def get_ticket_plan(project_root: Path, ticket_id: str) -> str | None:
    return _read_artifact(project_root, ticket_id, "plan.md")


def get_ticket_review(project_root: Path, ticket_id: str) -> str | None:
    return _read_artifact(project_root, ticket_id, "reviews/review.md")


def get_ticket_tests(project_root: Path, ticket_id: str) -> str | None:
    return _read_artifact(project_root, ticket_id, "tests/test-report.md")
