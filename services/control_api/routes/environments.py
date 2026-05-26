"""Routes for the Deployment Environments dashboard (T151).

All handlers delegate to :class:`SandboxManager`. Environments are sandboxes
that carry ``env_name`` and related deployment metadata.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

from ..models.sandbox import EnvironmentMode, EnvironmentType, RefType, SandboxState
from ..services.sandbox_manager import SandboxManager, SandboxNotFoundError

logger = logging.getLogger("control-api")

router = APIRouter(prefix="/environments", tags=["environments"])


def _get_manager(request: Request) -> SandboxManager:
    if not hasattr(request.app.state, "_sandbox_manager"):
        request.app.state._sandbox_manager = SandboxManager()
    return request.app.state._sandbox_manager


class CreateEnvironmentRequest(BaseModel):
    env_name: str
    project_root: str
    ref: str | None = None
    ref_type: RefType | None = None
    env_type: EnvironmentType | None = None
    deployment_mode: EnvironmentMode | None = None


class EnvironmentLogsResponse(BaseModel):
    logs: str


@router.post("", response_model=SandboxState, status_code=201)
def create_environment(body: CreateEnvironmentRequest, request: Request) -> SandboxState:
    logger.info("api: POST /environments env_name=%s ref=%s", body.env_name, body.ref)
    mgr = _get_manager(request)
    state = mgr.create(
        ticket_id=body.env_name,
        project_root=body.project_root,
        env_name=body.env_name,
        env_type=body.env_type,
        ref=body.ref,
        ref_type=body.ref_type,
        deployment_mode=body.deployment_mode,
    )
    try:
        state = mgr.start(state.id)
    except Exception as exc:
        logger.warning("environment start failed after create: %s", exc)
    return state


@router.get("", response_model=list[SandboxState])
def list_environments(request: Request) -> list[SandboxState]:
    mgr = _get_manager(request)
    return [s for s in mgr.list() if s.env_name is not None]


@router.get("/{env_id}", response_model=SandboxState)
def get_environment(env_id: str, request: Request) -> SandboxState:
    mgr = _get_manager(request)
    try:
        return mgr.status(env_id)
    except SandboxNotFoundError:
        raise HTTPException(status_code=404, detail=f"environment not found: {env_id}")


@router.post("/{env_id}/redeploy", response_model=SandboxState)
def redeploy_environment(env_id: str, request: Request) -> SandboxState:
    mgr = _get_manager(request)
    try:
        return mgr.restart(env_id)
    except SandboxNotFoundError:
        raise HTTPException(status_code=404, detail=f"environment not found: {env_id}")


@router.post("/{env_id}/stop", response_model=SandboxState)
def stop_environment(env_id: str, request: Request) -> SandboxState:
    mgr = _get_manager(request)
    try:
        return mgr.stop(env_id)
    except SandboxNotFoundError:
        raise HTTPException(status_code=404, detail=f"environment not found: {env_id}")


@router.delete("/{env_id}", status_code=204)
def delete_environment(env_id: str, request: Request) -> Response:
    mgr = _get_manager(request)
    try:
        mgr.destroy(env_id)
    except SandboxNotFoundError:
        raise HTTPException(status_code=404, detail=f"environment not found: {env_id}")
    return Response(status_code=204)


@router.post("/{env_id}/refresh", response_model=SandboxState)
def refresh_environment(env_id: str, request: Request) -> SandboxState:
    mgr = _get_manager(request)
    try:
        return mgr.refresh(env_id)
    except SandboxNotFoundError:
        raise HTTPException(status_code=404, detail=f"environment not found: {env_id}")


@router.get("/{env_id}/logs", response_model=EnvironmentLogsResponse)
def get_environment_logs(env_id: str, request: Request) -> EnvironmentLogsResponse:
    mgr = _get_manager(request)
    try:
        logs = mgr.logs(env_id)
        return EnvironmentLogsResponse(logs=logs)
    except SandboxNotFoundError:
        raise HTTPException(status_code=404, detail=f"environment not found: {env_id}")
