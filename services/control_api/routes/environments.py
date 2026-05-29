"""Routes for the Deployment Environments dashboard (T151/T158).

All handlers delegate to :class:`SandboxManager`. Environments are sandboxes
that carry ``env_name`` and related deployment metadata.
"""
from __future__ import annotations

import logging
import re
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

from ..models.sandbox import EnvironmentMode, EnvironmentType, RefType, SandboxState, SandboxStatus
from ..services.sandbox_manager import SandboxManager, SandboxNotFoundError

logger = logging.getLogger("control-api")

router = APIRouter(prefix="/environments", tags=["environments"])

# --- host validation helpers ---

_DNS_LABEL_RE = re.compile(r"^[a-z0-9]([a-z0-9\-]{0,61}[a-z0-9])?$|^[a-z0-9]$")
_RESERVED_PREFIXES = ("traefik.", "_")
_RESERVED_EXACT = {"localhost"}
_HOST_RULE_RE = re.compile(r"Host\(`([^`]+)`\)")


def _validate_host_format(host: str) -> str | None:
    """Return an error message if *host* is invalid, else None."""
    if not host:
        return "host cannot be empty"
    if host in _RESERVED_EXACT:
        return f"reserved host: {host!r}"
    for prefix in _RESERVED_PREFIXES:
        if host.startswith(prefix):
            return f"reserved host prefix in {host!r}"
    for label in host.split("."):
        if not _DNS_LABEL_RE.match(label):
            return f"invalid DNS label {label!r} in {host!r} — use lowercase alphanumeric and hyphens only"
    return None


def _declared_hosts(routes_dir: Path) -> set[str]:
    """Collect all hostnames already declared in Traefik route files."""
    hosts: set[str] = set()
    for yml in routes_dir.glob("*.yml"):
        if yml.stem.startswith("_"):
            continue
        try:
            for m in _HOST_RULE_RE.finditer(yml.read_text(encoding="utf-8")):
                hosts.add(m.group(1))
        except OSError:
            pass
    return hosts


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


class EnvironmentLogsResponse(BaseModel):
    logs: str


@router.post("", response_model=SandboxState, status_code=201)
def create_environment(body: CreateEnvironmentRequest, request: Request) -> SandboxState:
    logger.info("api: POST /environments env_name=%s ref=%s", body.env_name, body.ref)

    mgr = _get_manager(request)

    # Validate custom hosts before touching any sandbox state.
    for field, host in (("web_host", body.web_host), ("api_host", body.api_host)):
        if host is None:
            continue
        err = _validate_host_format(host)
        if err:
            raise HTTPException(status_code=422, detail=f"{field}: {err}")

    if body.web_host or body.api_host:
        # Use the same routes dir as the proxy manager for consistency.
        declared = _declared_hosts(mgr._proxy.routes_dir)
        for field, host in (("web_host", body.web_host), ("api_host", body.api_host)):
            if host and host in declared:
                raise HTTPException(
                    status_code=422,
                    detail=f"{field}: host already in use: {host!r}",
                )
    state = mgr.create(
        ticket_id=body.env_name,
        project_root=body.project_root,
        env_name=body.env_name,
        env_type=body.env_type,
        ref=body.ref,
        ref_type=body.ref_type,
        deployment_mode=body.deployment_mode,
        web_host=body.web_host,
        api_host=body.api_host,
    )
    try:
        started = mgr.start(state.id)
    except Exception as exc:
        _destroy_silently(mgr, state.id)
        raise HTTPException(status_code=500, detail=f"environment provisioning failed: {exc}")
    if started.status == SandboxStatus.error:
        _destroy_silently(mgr, started.id)
        raise HTTPException(status_code=500, detail="environment provisioning failed: docker compose up failed")
    return started


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
