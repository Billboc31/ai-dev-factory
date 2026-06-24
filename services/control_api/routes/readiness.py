"""Ticket Readiness routes — GET /readiness + POST /evaluate-readiness.

Readiness answers only: *can this ticket ENTER the workflow now?* These
endpoints surface ``blocking_reasons`` (workflow-entry blockers only) and
``warnings`` (advisory, non-blocking — including future plan/execution
approvals). They never feed plan-approval, execution-approval, planner-review
or rule-engine state back into the evaluator. See
``tools/agent_runner/ticket_readiness_evaluator.py`` for the contract.
"""

from __future__ import annotations

import logging
import sys
import threading
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request

from ..models.schemas import TicketReadiness, TicketReadinessQueued
from ..services.artifact_reader import get_ticket
from ..services.runtime_resolver import resolve_runs_dir, resolve_ticket_run_dir

_TOOLS_DIR = Path(__file__).resolve().parents[3] / "tools" / "agent_runner"
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))
import runtime_db  # noqa: E402
import ticket_readiness_evaluator as _evaluator  # noqa: E402

logger = logging.getLogger("control-api")
router = APIRouter(prefix="/tickets", tags=["readiness"])
project_router = APIRouter(prefix="/projects", tags=["readiness"])


def _root(request: Request) -> Path:
    return request.app.state.project_root


def _db_path(request: Request):
    return getattr(request.app.state, "db_path", None)


def _worktrees_dir(request: Request) -> Path | None:
    return getattr(request.app.state, "worktrees_dir", None)


def _bool_or_none(val) -> bool | None:
    if val is None:
        return None
    return bool(val)


def _parse_row(row: dict) -> TicketReadiness:
    """Convert a raw DB row into a ``TicketReadiness`` response model."""
    return TicketReadiness(
        ticket_id=row["ticket_id"],
        readiness_status=row["readiness_status"],
        ready_candidate=bool(row.get("ready_candidate")),
        blocking_reasons=row.get("blocking_reasons_json") or [],
        warnings=row.get("warnings_json") or [],
        dependency_check_status=row.get("dependency_check_status"),
        approval_check_status=row.get("approval_check_status"),
        context_freshness_status=row.get("context_freshness_status"),
        human_approval_required=_bool_or_none(row.get("human_approval_required")),
        human_approval_present=_bool_or_none(row.get("human_approval_present")),
        main_sha_when_evaluated=row.get("main_sha_when_evaluated"),
        evaluated_at=row.get("evaluated_at"),
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
    )


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


@router.get("/{ticket_id}/readiness", response_model=TicketReadiness)
def get_readiness(ticket_id: str, request: Request) -> TicketReadiness:
    logger.info("api: GET /tickets/%s/readiness", ticket_id)
    project_root = _root(request)
    wt_dir = _worktrees_dir(request)

    ticket = get_ticket(project_root, ticket_id, worktrees_dir=wt_dir)
    if ticket is None:
        raise HTTPException(status_code=404, detail=f"ticket {ticket_id} not found")

    db = _db_path(request)
    if db is None:
        raise HTTPException(status_code=503, detail="database not available")

    row = runtime_db.get_ticket_readiness(db, ticket_id)
    if row is None:
        raise HTTPException(
            status_code=404,
            detail=f"no readiness evaluation found for ticket {ticket_id}",
        )

    return _parse_row(row)


@router.post(
    "/{ticket_id}/evaluate-readiness",
    response_model=TicketReadinessQueued,
    status_code=202,
)
def evaluate_readiness(ticket_id: str, request: Request) -> TicketReadinessQueued:
    logger.info("api: POST /tickets/%s/evaluate-readiness", ticket_id)
    project_root = _root(request)
    wt_dir = _worktrees_dir(request)

    ticket = get_ticket(project_root, ticket_id, worktrees_dir=wt_dir)
    if ticket is None:
        raise HTTPException(status_code=404, detail=f"ticket {ticket_id} not found")

    db = _db_path(request)
    if db is None:
        raise HTTPException(status_code=503, detail="database not available")

    existing = runtime_db.get_ticket_readiness(db, ticket_id)
    if existing and existing.get("readiness_status") in {"queued", "running"}:
        return TicketReadinessQueued(
            ticket_id=ticket_id,
            readiness_status=existing["readiness_status"],
        )

    ticket_content = _read_ticket_content(project_root, ticket_id, wt_dir)

    runtime_db.upsert_ticket_readiness(db, ticket_id, readiness_status="queued")

    def _bg() -> None:
        try:
            _evaluator.run_evaluation(db, ticket_id, ticket_content, project_root)
        except Exception:
            logger.exception("readiness evaluation background error for %s", ticket_id)

    t = threading.Thread(target=_bg, daemon=True)
    t.start()

    return TicketReadinessQueued(ticket_id=ticket_id, readiness_status="queued")


@project_router.get(
    "/{project_id}/tickets/{ticket_id}/readiness",
    response_model=TicketReadiness,
)
def get_readiness_project(project_id: str, ticket_id: str, request: Request) -> TicketReadiness:
    return get_readiness(ticket_id, request)


@project_router.post(
    "/{project_id}/tickets/{ticket_id}/evaluate-readiness",
    response_model=TicketReadinessQueued,
    status_code=202,
)
def evaluate_readiness_project(
    project_id: str, ticket_id: str, request: Request
) -> TicketReadinessQueued:
    return evaluate_readiness(ticket_id, request)
