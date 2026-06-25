"""Ticket Execution Eligibility routes (T211).

Single read-only endpoint that aggregates Intelligence + Readiness + Approval
+ dependency state into one ``READY_TO_TAKE`` decision per ticket.

The endpoint never writes to the DB, never starts a worker, and never imports
the scheduler/daemon code paths.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request

from ..models.schemas import TicketExecutionEligibility
from ..services.artifact_reader import get_ticket
from ..services.runtime_resolver import resolve_runs_dir, resolve_ticket_run_dir

_TOOLS_DIR = Path(__file__).resolve().parents[3] / "tools" / "agent_runner"
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))
import ticket_execution_eligibility as _eligibility  # noqa: E402

logger = logging.getLogger("control-api")
router = APIRouter(prefix="/tickets", tags=["eligibility"])
project_router = APIRouter(prefix="/projects", tags=["eligibility"])


def _root(request: Request) -> Path:
    return request.app.state.project_root


def _db_path(request: Request):
    return getattr(request.app.state, "db_path", None)


def _worktrees_dir(request: Request) -> Path | None:
    return getattr(request.app.state, "worktrees_dir", None)


def _read_ticket_content(project_root: Path, ticket_id: str, worktrees_dir: Path | None) -> str:
    try:
        runs_dir = resolve_runs_dir(project_root)
        run_dir = resolve_ticket_run_dir(ticket_id, runs_dir, worktrees_dir)
        ticket_path = run_dir / "ticket.md"
        if ticket_path.exists():
            return ticket_path.read_text(encoding="utf-8")
    except Exception as exc:
        logger.warning("could not read ticket.md for %s: %s", ticket_id, exc)
    return ""


def _compute(
    ticket_id: str, request: Request, project_id: str | None = None
) -> TicketExecutionEligibility:
    project_root = _root(request)
    wt_dir = _worktrees_dir(request)

    ticket = get_ticket(project_root, ticket_id, worktrees_dir=wt_dir)
    if ticket is None:
        raise HTTPException(status_code=404, detail=f"ticket {ticket_id} not found")

    db = _db_path(request)
    if db is None:
        raise HTTPException(status_code=503, detail="database not available")

    ticket_content = _read_ticket_content(project_root, ticket_id, wt_dir)

    payload = _eligibility.evaluate_eligibility(
        db,
        project_root,
        ticket_id,
        ticket_content=ticket_content,
        project_id=project_id,
    )
    return TicketExecutionEligibility(**payload)


@router.get("/{ticket_id}/eligibility", response_model=TicketExecutionEligibility)
def get_eligibility(ticket_id: str, request: Request) -> TicketExecutionEligibility:
    logger.info("api: GET /tickets/%s/eligibility", ticket_id)
    return _compute(ticket_id, request)


@project_router.get(
    "/{project_id}/tickets/{ticket_id}/eligibility",
    response_model=TicketExecutionEligibility,
)
def get_eligibility_project(
    project_id: str, ticket_id: str, request: Request
) -> TicketExecutionEligibility:
    logger.info(
        "api: GET /projects/%s/tickets/%s/eligibility", project_id, ticket_id
    )
    return _compute(ticket_id, request, project_id=project_id)
