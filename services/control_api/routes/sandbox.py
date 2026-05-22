"""Routes for the two sandbox subsystems.

This module exposes two FastAPI routers that share the word "sandbox"
but address different operational concerns:

* ``router`` (mounted at ``/sandboxes``) — from T133/T136. Manages
  long-lived sandboxes used to isolate AI ticket workers. Backed by
  :class:`services.control_api.services.sandbox_manager.SandboxManager`.

* ``project_router`` (mounted at ``/projects/{project_id}/sandbox``) —
  from T134. One-shot deploy-validation pipeline that runs the
  generated operational scripts (``bootstrap → build → start →
  healthcheck``) in an isolated worktree and reports per-step status.
  Backed by :mod:`services.control_api.services.sandbox_runner`.

Class and function names are intentionally distinct between the two so
that imports and call sites never silently shadow each other.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from ..dependencies import resolve_project
from ..models.sandbox import SandboxState
from ..models.schemas import (
    ActionResult,
    SandboxValidationLogsResponse,
    SandboxValidationStatus,
)
from ..services import sandbox_runner
from ..services.sandbox_manager import SandboxManager, SandboxNotFoundError


def _supervisor_url() -> str | None:
    return os.environ.get("AI_DEV_FACTORY_SUPERVISOR_URL", "").rstrip("/") or None

logger = logging.getLogger("control-api")

# ── T133/T136: SandboxManager router ──────────────────────────────────────────

router = APIRouter(prefix="/sandboxes", tags=["sandbox"])


def _get_manager(request: Request) -> SandboxManager:
    if not hasattr(request.app.state, "_sandbox_manager"):
        request.app.state._sandbox_manager = SandboxManager()
    return request.app.state._sandbox_manager


class CreateSandboxRequest(BaseModel):
    ticket_id: str
    project_root: str


class SandboxManagerLogsResponse(BaseModel):
    """Response shape for the SandboxManager logs endpoint.

    Distinct from :class:`SandboxValidationLogsResponse` (T134), which
    returns a list of log lines for the deploy-validation pipeline.
    """
    logs: str


class CleanupResponse(BaseModel):
    destroyed: int


@router.post("", response_model=SandboxState, status_code=201)
def create_sandbox(body: CreateSandboxRequest, request: Request) -> SandboxState:
    logger.info("api: POST /sandboxes ticket=%s", body.ticket_id)
    return _get_manager(request).create(body.ticket_id, body.project_root)


@router.get("", response_model=list[SandboxState])
def list_sandboxes(request: Request) -> list[SandboxState]:
    return _get_manager(request).list()


# cleanup must be defined before /{sandbox_id} so "cleanup" is not matched as a sandbox_id
@router.post("/cleanup", response_model=CleanupResponse)
def cleanup_sandboxes(
    request: Request,
    max_age_days: int = Query(default=7, ge=0),
) -> CleanupResponse:
    logger.info("api: POST /sandboxes/cleanup max_age_days=%d", max_age_days)
    destroyed = _get_manager(request).cleanup_old(max_age_days)
    return CleanupResponse(destroyed=destroyed)


@router.get("/{sandbox_id}", response_model=SandboxState)
def get_sandbox(sandbox_id: str, request: Request) -> SandboxState:
    try:
        return _get_manager(request).status(sandbox_id)
    except SandboxNotFoundError:
        raise HTTPException(status_code=404, detail=f"sandbox not found: {sandbox_id}")


@router.post("/{sandbox_id}/start", response_model=SandboxState)
def start_sandbox(sandbox_id: str, request: Request) -> SandboxState:
    logger.info("api: POST /sandboxes/%s/start", sandbox_id)
    try:
        return _get_manager(request).start(sandbox_id)
    except SandboxNotFoundError:
        raise HTTPException(status_code=404, detail=f"sandbox not found: {sandbox_id}")


@router.post("/{sandbox_id}/stop", response_model=SandboxState)
def stop_sandbox(sandbox_id: str, request: Request) -> SandboxState:
    logger.info("api: POST /sandboxes/%s/stop", sandbox_id)
    try:
        return _get_manager(request).stop(sandbox_id)
    except SandboxNotFoundError:
        raise HTTPException(status_code=404, detail=f"sandbox not found: {sandbox_id}")


@router.delete("/{sandbox_id}", status_code=204)
def destroy_sandbox(sandbox_id: str, request: Request) -> None:
    logger.info("api: DELETE /sandboxes/%s", sandbox_id)
    try:
        _get_manager(request).destroy(sandbox_id)
    except SandboxNotFoundError:
        raise HTTPException(status_code=404, detail=f"sandbox not found: {sandbox_id}")


@router.get("/{sandbox_id}/logs", response_model=SandboxManagerLogsResponse)
def get_sandbox_logs(
    sandbox_id: str,
    request: Request,
    component: str | None = Query(default=None),
) -> SandboxManagerLogsResponse:
    try:
        logs = _get_manager(request).logs(sandbox_id, component)
        return SandboxManagerLogsResponse(logs=logs)
    except SandboxNotFoundError:
        raise HTTPException(status_code=404, detail=f"sandbox not found: {sandbox_id}")


# ── T134: per-project deploy-validation router ────────────────────────────────

project_router = APIRouter(prefix="/projects", tags=["sandbox"])


@project_router.get(
    "/{project_id}/sandbox/status",
    response_model=SandboxValidationStatus,
)
def get_project_sandbox_status(
    project_id: str,
    project_root: Path = Depends(resolve_project),  # registry validation only
) -> SandboxValidationStatus:
    # The host-side supervisor is the source of truth; project_root is
    # resolved by the dependency purely for registry validation (404 if
    # the project is unknown).
    state = sandbox_runner.get_sandbox_state(project_id, _supervisor_url())
    return SandboxValidationStatus(
        state=state.state,
        project_id=project_id,
        sandbox_id=state.sandbox_id,
        started_at=state.started_at,
        finished_at=state.finished_at,
        error=state.error,
        last_step=state.last_step,
        steps=state.steps,
    )


@project_router.post(
    "/{project_id}/sandbox/start",
    response_model=ActionResult,
    status_code=202,
)
def start_project_sandbox(
    project_id: str,
    project_root: Path = Depends(resolve_project),
) -> ActionResult:
    supervisor_url = _supervisor_url()
    logger.info(
        "api: POST /projects/%s/sandbox/start (supervisor=%s)",
        project_id, supervisor_url or "<not configured>",
    )
    # Pass the project_root the dashboard sees (which is the API's view —
    # potentially a container path like /app). The supervisor will map it
    # to the corresponding host path before spawning the worker.
    result = sandbox_runner.start_sandbox_validation(
        project_id, str(project_root), supervisor_url
    )
    if result.error == "locked":
        raise HTTPException(status_code=409, detail="sandbox already running")
    if result.error == "no_supervisor_url":
        raise HTTPException(
            status_code=503,
            detail=(
                "supervisor not configured — set AI_DEV_FACTORY_SUPERVISOR_URL "
                "and ensure the host supervisor is running"
            ),
        )
    if result.error == "supervisor_unreachable":
        raise HTTPException(
            status_code=503,
            detail="supervisor unreachable — is the host supervisor running?",
        )
    return result


@project_router.get(
    "/{project_id}/sandbox/logs",
    response_model=SandboxValidationLogsResponse,
)
def get_project_sandbox_logs(
    project_id: str,
    project_root: Path = Depends(resolve_project),  # registry validation only
    lines: int = Query(default=100, ge=1, le=10000),
) -> SandboxValidationLogsResponse:
    log_lines = sandbox_runner.get_sandbox_logs(project_id, _supervisor_url(), lines)
    return SandboxValidationLogsResponse(lines=log_lines)
