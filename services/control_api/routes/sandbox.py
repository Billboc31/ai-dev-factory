from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel

from ..models.sandbox import SandboxState
from ..services.sandbox_manager import SandboxManager, SandboxNotFoundError

logger = logging.getLogger("control-api")

router = APIRouter(prefix="/sandboxes", tags=["sandbox"])


def _get_manager(request: Request) -> SandboxManager:
    if not hasattr(request.app.state, "_sandbox_manager"):
        request.app.state._sandbox_manager = SandboxManager()
    return request.app.state._sandbox_manager


class CreateSandboxRequest(BaseModel):
    ticket_id: str
    project_root: str


class SandboxLogsResponse(BaseModel):
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


@router.get("/{sandbox_id}/logs", response_model=SandboxLogsResponse)
def get_sandbox_logs(
    sandbox_id: str,
    request: Request,
    component: str | None = Query(default=None),
) -> SandboxLogsResponse:
    try:
        logs = _get_manager(request).logs(sandbox_id, component)
        return SandboxLogsResponse(logs=logs)
    except SandboxNotFoundError:
        raise HTTPException(status_code=404, detail=f"sandbox not found: {sandbox_id}")
