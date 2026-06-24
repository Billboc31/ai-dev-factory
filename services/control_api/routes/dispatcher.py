"""Ticket Dispatcher routes (T212).

Read-only endpoints that expose the advisory dispatcher's mode and current
recommendations. None of these endpoints start a ticket, modify the runtime
DB, or touch the daemon/runner/scheduler.
"""

from __future__ import annotations

import logging
import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request

from ..models.schemas import DispatcherResponse, DispatcherStatus

_TOOLS_DIR = Path(__file__).resolve().parents[3] / "tools" / "agent_runner"
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

import ticket_dispatcher as _dispatcher  # noqa: E402

logger = logging.getLogger("control-api")
router = APIRouter(prefix="/dispatcher", tags=["dispatcher"])
project_router = APIRouter(prefix="/projects", tags=["dispatcher"])


def _root(request: Request) -> Path:
    return request.app.state.project_root


def _db_path(request: Request):
    return getattr(request.app.state, "db_path", None)


def _compute(
    request: Request,
    *,
    project_id: str | None = None,
    mode_override: str | None = None,
) -> DispatcherResponse:
    db = _db_path(request)
    if db is None:
        raise HTTPException(status_code=503, detail="database not available")

    payload = _dispatcher.get_recommended_tickets(
        db,
        _root(request),
        project_id=project_id,
        mode=mode_override,
    )
    return DispatcherResponse(**payload)


@router.get("/status", response_model=DispatcherStatus)
def get_status() -> DispatcherStatus:
    mode = _dispatcher.get_dispatcher_mode()
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
    project_id: str, request: Request, mode: str | None = None
) -> DispatcherResponse:
    logger.info(
        "api: GET /projects/%s/dispatcher/recommendations (mode_override=%s)",
        project_id,
        mode,
    )
    return _compute(request, project_id=project_id, mode_override=mode)
