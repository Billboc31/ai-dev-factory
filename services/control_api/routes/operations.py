"""Ticket Operations routes — guarded manual recovery actions (T204).

Endpoints:
    GET  /tickets/{ticket_id}/operations
    POST /tickets/{ticket_id}/operations/{operation_key}

Project-scoped variants:
    GET  /projects/{project_id}/tickets/{ticket_id}/operations
    POST /projects/{project_id}/tickets/{ticket_id}/operations/{operation_key}

Every operation runs only on explicit operator action and is audited in
``ticket_operation_audit`` and ``runtime_events`` whether it succeeds, is
rejected, or errors.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request

from ..models.schemas import (
    OperationDescriptor,
    OperationListResponse,
    OperationRequest,
    OperationResult,
)
from ..services.artifact_reader import get_ticket
from ..services.project_id import normalize_project_id

_TOOLS_DIR = Path(__file__).resolve().parents[3] / "tools" / "agent_runner"
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))
import ticket_operations as _ops  # noqa: E402


logger = logging.getLogger("control-api")
router = APIRouter(prefix="/tickets", tags=["operations"])
project_router = APIRouter(prefix="/projects", tags=["operations"])


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


def _require_ticket(request: Request, ticket_id: str) -> None:
    ticket = get_ticket(_root(request), ticket_id, worktrees_dir=_worktrees_dir(request))
    if ticket is None:
        raise HTTPException(status_code=404, detail=f"ticket {ticket_id} not found")


def _requested_by(request: Request) -> str:
    header = request.headers.get("X-Operator-Name") or request.headers.get("X-User-Name")
    return (header or "operator").strip() or "operator"


@router.get("/{ticket_id}/operations", response_model=OperationListResponse)
def get_operations(ticket_id: str, request: Request) -> OperationListResponse:
    logger.info("api: GET /tickets/%s/operations", ticket_id)
    _require_ticket(request, ticket_id)
    db = _db_path(request)
    items = _ops.list_operations(
        db,
        _root(request),
        ticket_id,
        project_id=_resolve_project_id(request),
        worktrees_dir=_worktrees_dir(request),
    )
    return OperationListResponse(
        ticket_id=ticket_id,
        operations=[OperationDescriptor(**item) for item in items],
    )


@router.post(
    "/{ticket_id}/operations/{operation_key}",
    response_model=OperationResult,
)
def run_operation(
    ticket_id: str,
    operation_key: str,
    payload: OperationRequest,
    request: Request,
    project_id: str | None = None,
) -> OperationResult:
    logger.info("api: POST /tickets/%s/operations/%s", ticket_id, operation_key)
    if operation_key not in _ops.OPERATIONS:
        raise HTTPException(status_code=404, detail=f"unknown operation {operation_key!r}")
    _require_ticket(request, ticket_id)
    db = _db_path(request)
    requested_by = _requested_by(request)
    resolved_pid = _resolve_project_id(request, project_id)
    try:
        result = _ops.execute_operation(
            db,
            _root(request),
            ticket_id,
            operation_key,
            payload=payload.model_dump(),
            requested_by=requested_by,
            project_id=resolved_pid,
            worktrees_dir=_worktrees_dir(request),
        )
    except _ops.OperationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return OperationResult(**result)


@project_router.get(
    "/{project_id}/tickets/{ticket_id}/operations",
    response_model=OperationListResponse,
)
def get_operations_project(
    project_id: str, ticket_id: str, request: Request,
) -> OperationListResponse:
    return get_operations(ticket_id, request)


@project_router.post(
    "/{project_id}/tickets/{ticket_id}/operations/{operation_key}",
    response_model=OperationResult,
)
def run_operation_project(
    project_id: str,
    ticket_id: str,
    operation_key: str,
    payload: OperationRequest,
    request: Request,
) -> OperationResult:
    return run_operation(ticket_id, operation_key, payload, request, project_id=project_id)
