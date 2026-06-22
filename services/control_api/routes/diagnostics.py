"""Ticket Diagnostics routes — read-only diagnostic capability (T203).

Endpoints:
    GET  /tickets/{ticket_id}/diagnostics
    POST /tickets/{ticket_id}/diagnostics/run

Project-scoped variants:
    GET  /projects/{project_id}/tickets/{ticket_id}/diagnostics
    POST /projects/{project_id}/tickets/{ticket_id}/diagnostics/run

The endpoints are read-only except for persisting the latest diagnostic per
ticket. They never mutate ticket state, worktrees, branches, PRs, scheduler
reservations or daemon state, and never run an agent.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request

from ..models.schemas import (
    DiagnosticCheck,
    DiagnosticRecommendedAction,
    TicketDiagnostics,
)
from ..services.artifact_reader import get_ticket
from ..services.project_id import normalize_project_id

_TOOLS_DIR = Path(__file__).resolve().parents[3] / "tools" / "agent_runner"
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))
import runtime_db  # noqa: E402
import ticket_diagnostics as _diagnostics  # noqa: E402


logger = logging.getLogger("control-api")
router = APIRouter(prefix="/tickets", tags=["diagnostics"])
project_router = APIRouter(prefix="/projects", tags=["diagnostics"])


def _root(request: Request) -> Path:
    return request.app.state.project_root


def _db_path(request: Request):
    db = getattr(request.app.state, "db_path", None)
    if db is None:
        raise HTTPException(status_code=503, detail="database not available")
    return db


def _worktrees_dir(request: Request) -> Path | None:
    return getattr(request.app.state, "worktrees_dir", None)


def _resolve_project_id(request: Request, override: str | None = None) -> str | None:
    if override:
        try:
            return normalize_project_id(override)
        except ValueError:
            return override
    db = getattr(request.app.state, "db_path", None)
    return getattr(db, "project_id", None)


def _row_to_response(row: dict) -> TicketDiagnostics:
    return TicketDiagnostics(
        ticket_id=row["ticket_id"],
        project_id=row.get("project_id"),
        diagnostic_status=row.get("diagnostic_status") or "completed",
        is_stuck=bool(row.get("is_stuck")),
        severity=row.get("severity") or "info",
        summary=row.get("summary"),
        current_state=row.get("current_state"),
        last_known_step=row.get("last_known_step"),
        last_error=row.get("last_error"),
        checks=[DiagnosticCheck(**c) for c in row.get("checks_json") or []],
        recommended_actions=[
            DiagnosticRecommendedAction(**a)
            for a in row.get("recommended_actions_json") or []
        ],
        generated_at=row.get("generated_at"),
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
    )


def _result_to_response(result: dict, db_row: dict | None) -> TicketDiagnostics:
    return TicketDiagnostics(
        ticket_id=result["ticket_id"],
        project_id=(db_row or {}).get("project_id"),
        diagnostic_status=result.get("diagnostic_status") or "completed",
        is_stuck=bool(result.get("is_stuck")),
        severity=result.get("severity") or "info",
        summary=result.get("summary"),
        current_state=result.get("current_state"),
        last_known_step=result.get("last_known_step"),
        last_error=result.get("last_error"),
        checks=[DiagnosticCheck(**c) for c in result.get("checks") or []],
        recommended_actions=[
            DiagnosticRecommendedAction(**a)
            for a in result.get("recommended_actions") or []
        ],
        generated_at=result.get("generated_at"),
        created_at=(db_row or {}).get("created_at"),
        updated_at=(db_row or {}).get("updated_at"),
    )


# ── GET /tickets/{id}/diagnostics ────────────────────────────────────────────

@router.get(
    "/{ticket_id}/diagnostics",
    response_model=TicketDiagnostics,
)
def get_diagnostics(ticket_id: str, request: Request) -> TicketDiagnostics:
    logger.info("api: GET /tickets/%s/diagnostics", ticket_id)
    db = _db_path(request)
    row = runtime_db.get_ticket_diagnostics(db, ticket_id)
    if row is None:
        raise HTTPException(
            status_code=404,
            detail=f"no diagnostic found for ticket {ticket_id}",
        )
    return _row_to_response(row)


# ── POST /tickets/{id}/diagnostics/run ───────────────────────────────────────

@router.post(
    "/{ticket_id}/diagnostics/run",
    response_model=TicketDiagnostics,
)
def run_diagnostics(
    ticket_id: str,
    request: Request,
    project_id: str | None = None,
) -> TicketDiagnostics:
    logger.info("api: POST /tickets/%s/diagnostics/run", ticket_id)
    project_root = _root(request)
    wt_dir = _worktrees_dir(request)
    db = _db_path(request)

    ticket = get_ticket(project_root, ticket_id, worktrees_dir=wt_dir)
    runtime_row = None
    try:
        runtime_row = runtime_db.get_ticket_runtime(db, ticket_id)
    except Exception:
        runtime_row = None
    if ticket is None and runtime_row is None:
        raise HTTPException(status_code=404, detail=f"ticket {ticket_id} not found")

    resolved_pid = _resolve_project_id(request, project_id)
    result = _diagnostics.diagnose_ticket(
        db,
        project_root,
        ticket_id,
        worktrees_dir=wt_dir,
        project_id=resolved_pid,
    )
    persisted = runtime_db.get_ticket_diagnostics(db, ticket_id)
    return _result_to_response(result, persisted)


# ── Project-scoped variants ──────────────────────────────────────────────────

@project_router.get(
    "/{project_id}/tickets/{ticket_id}/diagnostics",
    response_model=TicketDiagnostics,
)
def get_diagnostics_project(
    project_id: str, ticket_id: str, request: Request,
) -> TicketDiagnostics:
    return get_diagnostics(ticket_id, request)


@project_router.post(
    "/{project_id}/tickets/{ticket_id}/diagnostics/run",
    response_model=TicketDiagnostics,
)
def run_diagnostics_project(
    project_id: str, ticket_id: str, request: Request,
) -> TicketDiagnostics:
    return run_diagnostics(ticket_id, request, project_id=project_id)
