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
import os
import sys
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request

from ..dependencies import resolve_project, resolve_project_runtime_root
from ..models.schemas import (
    OperationDescriptor,
    OperationListResponse,
    OperationRequest,
    OperationResult,
)
from ..services.artifact_reader import get_ticket
from ..services.container_paths import to_container_path
from ..services.project_id import normalize_project_id
from ..services.runtime_resolver import resolve_worktrees_dir

_TOOLS_DIR = Path(__file__).resolve().parents[3] / "tools" / "agent_runner"
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))
import runtime_db  # noqa: E402
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


def _resolve_db_for_project(request: Request, project_id: str | None):
    """Return the project-scoped DB handle, falling back to the global one."""
    if not project_id:
        return _db_path(request)

    project_runtime_root = None
    registry = getattr(request.app.state, "project_registry", None)
    if registry is not None:
        prt = registry.resolve_runtime_root(project_id)
        if prt is not None:
            project_runtime_root = to_container_path(prt)

    runtime_configured = bool(
        project_runtime_root is not None
        or os.environ.get("RUNTIME_BASE_ROOT")
        or os.environ.get("AI_DEV_FACTORY_RUNTIME_ROOT")
    )
    if not runtime_configured:
        return _db_path(request)

    try:
        db = runtime_db.resolve_db_path_for_project(project_id, project_runtime_root)
    except Exception:
        db = None

    if db is not None:
        if isinstance(db, Path):
            mapped = to_container_path(db)
            if mapped is not None and mapped.exists():
                return mapped
        elif getattr(db, "exists", lambda: True)():
            return db

    return _db_path(request)


def _scoped_runtime_root(project_runtime_root: Path | None) -> Path | None:
    return to_container_path(project_runtime_root) if project_runtime_root is not None else None


def _scoped_worktrees(
    request: Request,
    project_root: Path,
    *,
    project_id: str | None = None,
    project_runtime_root: Path | None = None,
) -> Path | None:
    if project_id is not None or project_runtime_root is not None:
        return resolve_worktrees_dir(
            project_root,
            project_id=project_id,
            project_runtime_root=_scoped_runtime_root(project_runtime_root),
        )
    return _worktrees_dir(request)


def _require_ticket(
    request: Request,
    ticket_id: str,
    *,
    project_root: Path | None = None,
    project_id: str | None = None,
    project_runtime_root: Path | None = None,
) -> None:
    root = project_root or _root(request)
    wt_dir = _scoped_worktrees(
        request,
        root,
        project_id=project_id,
        project_runtime_root=project_runtime_root,
    )
    scoped_runtime = _scoped_runtime_root(project_runtime_root)
    ticket = get_ticket(
        root,
        ticket_id,
        worktrees_dir=wt_dir,
        project_runtime_root=scoped_runtime,
    )
    if ticket is None:
        raise HTTPException(status_code=404, detail=f"ticket {ticket_id} not found")


def _requested_by(request: Request) -> str:
    header = request.headers.get("X-Operator-Name") or request.headers.get("X-User-Name")
    return (header or "operator").strip() or "operator"


def _list_operations(
    request: Request,
    ticket_id: str,
    *,
    project_root: Path | None = None,
    project_id: str | None = None,
    project_runtime_root: Path | None = None,
) -> OperationListResponse:
    _require_ticket(
        request,
        ticket_id,
        project_root=project_root,
        project_id=project_id,
        project_runtime_root=project_runtime_root,
    )
    root = project_root or _root(request)
    db = _resolve_db_for_project(request, project_id) if project_id else _db_path(request)
    wt_dir = _scoped_worktrees(
        request,
        root,
        project_id=project_id,
        project_runtime_root=project_runtime_root,
    )
    resolved_pid = _resolve_project_id(request, project_id)
    items = _ops.list_operations(
        db,
        root,
        ticket_id,
        project_id=resolved_pid,
        worktrees_dir=wt_dir,
    )
    return OperationListResponse(
        ticket_id=ticket_id,
        operations=[OperationDescriptor(**item) for item in items],
    )


def _run_operation(
    request: Request,
    ticket_id: str,
    operation_key: str,
    payload: OperationRequest,
    *,
    project_root: Path | None = None,
    project_id: str | None = None,
    project_runtime_root: Path | None = None,
) -> OperationResult:
    if operation_key not in _ops.OPERATIONS:
        raise HTTPException(status_code=404, detail=f"unknown operation {operation_key!r}")
    _require_ticket(
        request,
        ticket_id,
        project_root=project_root,
        project_id=project_id,
        project_runtime_root=project_runtime_root,
    )
    root = project_root or _root(request)
    db = _resolve_db_for_project(request, project_id) if project_id else _db_path(request)
    wt_dir = _scoped_worktrees(
        request,
        root,
        project_id=project_id,
        project_runtime_root=project_runtime_root,
    )
    requested_by = _requested_by(request)
    resolved_pid = _resolve_project_id(request, project_id)
    try:
        result = _ops.execute_operation(
            db,
            root,
            ticket_id,
            operation_key,
            payload=payload.model_dump(),
            requested_by=requested_by,
            project_id=resolved_pid,
            worktrees_dir=wt_dir,
        )
    except _ops.OperationError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message) from exc
    return OperationResult(**result)


@router.get("/{ticket_id}/operations", response_model=OperationListResponse)
def get_operations(ticket_id: str, request: Request) -> OperationListResponse:
    logger.info("api: GET /tickets/%s/operations", ticket_id)
    return _list_operations(request, ticket_id)


@router.post(
    "/{ticket_id}/operations/{operation_key}",
    response_model=OperationResult,
)
def run_operation(
    ticket_id: str,
    operation_key: str,
    payload: OperationRequest,
    request: Request,
) -> OperationResult:
    logger.info("api: POST /tickets/%s/operations/%s", ticket_id, operation_key)
    return _run_operation(request, ticket_id, operation_key, payload)


@project_router.get(
    "/{project_id}/tickets/{ticket_id}/operations",
    response_model=OperationListResponse,
)
def get_operations_project(
    project_id: str,
    ticket_id: str,
    request: Request,
    project_root: Path = Depends(resolve_project),
    project_runtime_root: Path | None = Depends(resolve_project_runtime_root),
) -> OperationListResponse:
    logger.info("api: GET /projects/%s/tickets/%s/operations", project_id, ticket_id)
    return _list_operations(
        request,
        ticket_id,
        project_root=project_root,
        project_id=project_id,
        project_runtime_root=project_runtime_root,
    )


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
    project_root: Path = Depends(resolve_project),
    project_runtime_root: Path | None = Depends(resolve_project_runtime_root),
) -> OperationResult:
    logger.info(
        "api: POST /projects/%s/tickets/%s/operations/%s",
        project_id,
        ticket_id,
        operation_key,
    )
    return _run_operation(
        request,
        ticket_id,
        operation_key,
        payload,
        project_root=project_root,
        project_id=project_id,
        project_runtime_root=project_runtime_root,
    )
