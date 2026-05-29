"""Routes for the Deployment Environments dashboard (T151/T158).

When ``AI_DEV_FACTORY_SUPERVISOR_URL`` is set, handlers proxy to the
host-side supervisor so path validation and :class:`SandboxManager`
operations run on the host filesystem (container paths are mapped via
``ContainerToHostMapper``). Without a supervisor URL, handlers use a
local :class:`SandboxManager` (unit tests and single-process dev).
"""
from __future__ import annotations

import logging
import os

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

from ..models.sandbox import EnvironmentMode, EnvironmentType, RefType, SandboxState
from ..services import environment_runner
from ..services.environment_provision import (
    provision_environment,
    validate_host_format,
)
from ..services.environment_runner import ProvisionError
from ..services.sandbox_manager import SandboxManager, SandboxNotFoundError

logger = logging.getLogger("control-api")

router = APIRouter(prefix="/environments", tags=["environments"])


def _supervisor_url() -> str | None:
    return os.environ.get("AI_DEV_FACTORY_SUPERVISOR_URL", "").strip() or None


def _use_supervisor() -> bool:
    return _supervisor_url() is not None


def _provision_error_to_http(exc: ProvisionError) -> HTTPException:
    return HTTPException(status_code=exc.status_code, detail=exc.detail)


def _destroy_silently(mgr: SandboxManager, sandbox_id: str) -> None:
    try:
        mgr.destroy(sandbox_id)
    except Exception as exc:
        logger.warning("environment cleanup failed: sandbox_id=%s error=%s", sandbox_id, exc)


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
    web_host: str | None = None
    api_host: str | None = None
    sandbox_path: str | None = None


class EnvironmentLogsResponse(BaseModel):
    logs: str


def _validate_hosts_api_only(body: CreateEnvironmentRequest) -> None:
    """DNS-format checks only — no host filesystem access in the API process."""
    for field, host in (("web_host", body.web_host), ("api_host", body.api_host)):
        if host is None:
            continue
        err = validate_host_format(host)
        if err:
            raise HTTPException(status_code=422, detail=f"{field}: {err}")


@router.post("", response_model=SandboxState, status_code=201)
def create_environment(body: CreateEnvironmentRequest, request: Request) -> SandboxState:
    logger.info("api: POST /environments env_name=%s ref=%s", body.env_name, body.ref)
    _validate_hosts_api_only(body)

    if _use_supervisor():
        try:
            return environment_runner.provision_environment(
                body.model_dump(mode="json"),
                _supervisor_url(),
            )
        except ProvisionError as exc:
            raise _provision_error_to_http(exc) from exc

    mgr = _get_manager(request)
    try:
        started = provision_environment(
            mgr,
            env_name=body.env_name,
            project_root=body.project_root,
            map_fn=lambda p: p,
            ref=body.ref,
            ref_type=body.ref_type,
            env_type=body.env_type,
            deployment_mode=body.deployment_mode,
            web_host=body.web_host,
            api_host=body.api_host,
            sandbox_path=body.sandbox_path,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return started


@router.get("", response_model=list[SandboxState])
def list_environments(request: Request) -> list[SandboxState]:
    if _use_supervisor():
        try:
            return environment_runner.list_environments(_supervisor_url())
        except ProvisionError as exc:
            raise _provision_error_to_http(exc) from exc
    mgr = _get_manager(request)
    return [s for s in mgr.list() if s.env_name is not None]


@router.get("/{env_id}", response_model=SandboxState)
def get_environment(env_id: str, request: Request) -> SandboxState:
    if _use_supervisor():
        try:
            return environment_runner.get_environment(env_id, _supervisor_url())
        except ProvisionError as exc:
            raise _provision_error_to_http(exc) from exc
    mgr = _get_manager(request)
    try:
        return mgr.status(env_id)
    except SandboxNotFoundError:
        raise HTTPException(status_code=404, detail=f"environment not found: {env_id}")


@router.post("/{env_id}/redeploy", response_model=SandboxState)
def redeploy_environment(env_id: str, request: Request) -> SandboxState:
    if _use_supervisor():
        try:
            return environment_runner.redeploy_environment(env_id, _supervisor_url())
        except ProvisionError as exc:
            raise _provision_error_to_http(exc) from exc
    mgr = _get_manager(request)
    try:
        return mgr.restart(env_id)
    except SandboxNotFoundError:
        raise HTTPException(status_code=404, detail=f"environment not found: {env_id}")


@router.post("/{env_id}/stop", response_model=SandboxState)
def stop_environment(env_id: str, request: Request) -> SandboxState:
    if _use_supervisor():
        try:
            return environment_runner.stop_environment(env_id, _supervisor_url())
        except ProvisionError as exc:
            raise _provision_error_to_http(exc) from exc
    mgr = _get_manager(request)
    try:
        return mgr.stop(env_id)
    except SandboxNotFoundError:
        raise HTTPException(status_code=404, detail=f"environment not found: {env_id}")


@router.delete("/{env_id}", status_code=204)
def delete_environment(env_id: str, request: Request) -> Response:
    if _use_supervisor():
        try:
            environment_runner.delete_environment(env_id, _supervisor_url())
        except ProvisionError as exc:
            raise _provision_error_to_http(exc) from exc
        return Response(status_code=204)
    mgr = _get_manager(request)
    try:
        mgr.destroy(env_id)
    except SandboxNotFoundError:
        raise HTTPException(status_code=404, detail=f"environment not found: {env_id}")
    return Response(status_code=204)


@router.post("/{env_id}/refresh", response_model=SandboxState)
def refresh_environment(env_id: str, request: Request) -> SandboxState:
    if _use_supervisor():
        try:
            return environment_runner.refresh_environment(env_id, _supervisor_url())
        except ProvisionError as exc:
            raise _provision_error_to_http(exc) from exc
    mgr = _get_manager(request)
    try:
        return mgr.refresh(env_id)
    except SandboxNotFoundError:
        raise HTTPException(status_code=404, detail=f"environment not found: {env_id}")


@router.get("/{env_id}/logs", response_model=EnvironmentLogsResponse)
def get_environment_logs(env_id: str, request: Request) -> EnvironmentLogsResponse:
    if _use_supervisor():
        try:
            logs = environment_runner.get_environment_logs(env_id, _supervisor_url())
            return EnvironmentLogsResponse(logs=logs)
        except ProvisionError as exc:
            raise _provision_error_to_http(exc) from exc
    mgr = _get_manager(request)
    try:
        logs = mgr.logs(env_id)
        return EnvironmentLogsResponse(logs=logs)
    except SandboxNotFoundError:
        raise HTTPException(status_code=404, detail=f"environment not found: {env_id}")
