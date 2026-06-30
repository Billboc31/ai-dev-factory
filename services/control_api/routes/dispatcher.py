"""Ticket Dispatcher routes (T212).

Read-only endpoints that expose the advisory dispatcher's mode and current
recommendations. None of these endpoints start a ticket, modify the runtime
DB, or touch the daemon/runner/scheduler.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request

from ..dependencies import resolve_project
from ..models.schemas import DispatcherResponse, DispatcherStatus
from ..services.container_paths import to_container_path

_TOOLS_DIR = Path(__file__).resolve().parents[3] / "tools" / "agent_runner"
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

import runtime_db  # noqa: E402
import ticket_dispatcher as _dispatcher  # noqa: E402

logger = logging.getLogger("control-api")
router = APIRouter(prefix="/dispatcher", tags=["dispatcher"])
project_router = APIRouter(prefix="/projects", tags=["dispatcher"])


def _root(request: Request) -> Path:
    return request.app.state.project_root


def _db_path(request: Request):
    return getattr(request.app.state, "db_path", None)


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


def _compute(
    request: Request,
    *,
    project_root: Path | None = None,
    project_id: str | None = None,
    mode_override: str | None = None,
) -> DispatcherResponse:
    db = _resolve_db_for_project(request, project_id) if project_id else _db_path(request)
    if db is None:
        raise HTTPException(status_code=503, detail="database not available")

    payload = _dispatcher.get_recommended_tickets(
        db,
        project_root or _root(request),
        project_id=project_id,
        mode=mode_override,
    )
    return DispatcherResponse(**payload)


@router.get("/status", response_model=DispatcherStatus)
def get_status(request: Request) -> DispatcherStatus:
    mode = _dispatcher.get_dispatcher_mode(_db_path(request))
    logger.info("api: GET /dispatcher/status (mode=%s)", mode)
    return DispatcherStatus(
        mode=mode,
        available_modes=list(_dispatcher.DISPATCHER_MODES),
        auto_enabled=False,
    )


@router.get("/recommendations", response_model=DispatcherResponse)
def get_recommendations(
    request: Request, mode: str | None = None
) -> DispatcherResponse:
    logger.info("api: GET /dispatcher/recommendations (mode_override=%s)", mode)
    return _compute(request, mode_override=mode)


@project_router.get(
    "/{project_id}/dispatcher/recommendations",
    response_model=DispatcherResponse,
)
def get_recommendations_project(
    project_id: str,
    request: Request,
    mode: str | None = None,
    project_root: Path = Depends(resolve_project),
) -> DispatcherResponse:
    logger.info(
        "api: GET /projects/%s/dispatcher/recommendations (mode_override=%s)",
        project_id,
        mode,
    )
    return _compute(
        request,
        project_root=project_root,
        project_id=project_id,
        mode_override=mode,
    )
