"""Ticket Approval routes — list approvals + approve/reject execution.

Endpoints (mounted both at ``/tickets`` and ``/projects/{project_id}/tickets``):
    GET  /tickets/{ticket_id}/approvals
    POST /tickets/{ticket_id}/approve-execution
    POST /tickets/{ticket_id}/reject-execution

Status code contract:
    200 — happy path AND idempotent replay of the same decision
    404 — unknown ticket
    409 — contradictory transition or invalid state (no prior decision and
          readiness is not ``ready_candidate``)
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request

from ..models.schemas import (
    ApprovalDecision,
    TicketApproval,
    TicketApprovalHistory,
)
from ..services.artifact_reader import get_ticket

_TOOLS_DIR = Path(__file__).resolve().parents[3] / "tools" / "agent_runner"
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))
import ticket_approval_service as _service  # noqa: E402

logger = logging.getLogger("control-api")
router = APIRouter(prefix="/tickets", tags=["approvals"])
project_router = APIRouter(prefix="/projects", tags=["approvals"])


def _root(request: Request) -> Path:
    return request.app.state.project_root


def _db_path(request: Request):
    return getattr(request.app.state, "db_path", None)


def _worktrees_dir(request: Request) -> Path | None:
    return getattr(request.app.state, "worktrees_dir", None)


def _row_to_model(row: dict) -> TicketApproval:
    return TicketApproval(
        id=int(row["id"]),
        ticket_id=row["ticket_id"],
        approval_type=row["approval_type"],
        approval_status=row["approval_status"],
        approved_by=row.get("approved_by"),
        approval_comment=row.get("approval_comment"),
        approved_at=row.get("approved_at"),
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
    )


def _require_ticket(request: Request, ticket_id: str) -> None:
    ticket = get_ticket(_root(request), ticket_id, worktrees_dir=_worktrees_dir(request))
    if ticket is None:
        raise HTTPException(status_code=404, detail=f"ticket {ticket_id} not found")


def _require_db(request: Request):
    db = _db_path(request)
    if db is None:
        raise HTTPException(status_code=503, detail="database not available")
    return db


@router.get("/{ticket_id}/approvals", response_model=TicketApprovalHistory)
def get_approvals(ticket_id: str, request: Request) -> TicketApprovalHistory:
    logger.info("api: GET /tickets/%s/approvals", ticket_id)
    _require_ticket(request, ticket_id)
    db = _require_db(request)
    rows = _service.get_ticket_approvals(db, ticket_id)
    return TicketApprovalHistory(
        ticket_id=ticket_id,
        approvals=[_row_to_model(r) for r in rows],
    )


@router.post("/{ticket_id}/approve-execution", response_model=TicketApproval)
def approve_execution(
    ticket_id: str, decision: ApprovalDecision, request: Request
) -> TicketApproval:
    logger.info("api: POST /tickets/%s/approve-execution by=%s", ticket_id, decision.approved_by)
    _require_ticket(request, ticket_id)
    db = _require_db(request)
    try:
        row = _service.approve_execution(
            db, ticket_id, approved_by=decision.approved_by, comment=decision.comment
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _row_to_model(row)


@router.post("/{ticket_id}/reject-execution", response_model=TicketApproval)
def reject_execution(
    ticket_id: str, decision: ApprovalDecision, request: Request
) -> TicketApproval:
    logger.info("api: POST /tickets/%s/reject-execution by=%s", ticket_id, decision.approved_by)
    _require_ticket(request, ticket_id)
    db = _require_db(request)
    try:
        row = _service.reject_execution(
            db, ticket_id, approved_by=decision.approved_by, comment=decision.comment
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return _row_to_model(row)


# ── Project-scoped mounts ────────────────────────────────────────────────────

@project_router.get(
    "/{project_id}/tickets/{ticket_id}/approvals",
    response_model=TicketApprovalHistory,
)
def get_approvals_project(
    project_id: str, ticket_id: str, request: Request
) -> TicketApprovalHistory:
    return get_approvals(ticket_id, request)


@project_router.post(
    "/{project_id}/tickets/{ticket_id}/approve-execution",
    response_model=TicketApproval,
)
def approve_execution_project(
    project_id: str, ticket_id: str, decision: ApprovalDecision, request: Request
) -> TicketApproval:
    return approve_execution(ticket_id, decision, request)


@project_router.post(
    "/{project_id}/tickets/{ticket_id}/reject-execution",
    response_model=TicketApproval,
)
def reject_execution_project(
    project_id: str, ticket_id: str, decision: ApprovalDecision, request: Request
) -> TicketApproval:
    return reject_execution(ticket_id, decision, request)
