"""Workspace routes — authenticated proxy to the Supervisor workspace endpoints (T225/T227).

Endpoints:
    POST /projects/{project_id}/workspace/chat
    POST /projects/{project_id}/workspace/actions/confirm
    POST /projects/{project_id}/workspace/issues/confirm
    GET  /projects/{project_id}/workspace/deployments/{deployment_id}

Every request is forwarded to the Supervisor. This module must not invoke any
AI provider, GitHub API, or internal operational service directly.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from ..dependencies import resolve_project

logger = logging.getLogger("control-api")
project_router = APIRouter(prefix="/projects", tags=["workspace"])


def _supervisor_url() -> str:
    return os.environ.get("AI_DEV_FACTORY_SUPERVISOR_URL", "http://127.0.0.1:8090").rstrip("/")


def _forward(path: str, body: dict) -> dict:
    """POST *body* to the Supervisor workspace endpoint. Raises HTTPException on failure."""
    url = f"{_supervisor_url()}{path}"
    try:
        resp = httpx.post(url, json=body, timeout=90.0)
    except httpx.ConnectError as exc:
        logger.error("workspace: supervisor unreachable at %s: %s", url, exc)
        raise HTTPException(status_code=503, detail="Supervisor is not reachable")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Supervisor request timed out")

    if resp.status_code >= 400:
        detail = _extract_detail(resp)
        raise HTTPException(status_code=resp.status_code, detail=detail)

    return resp.json()


def _forward_get(path: str) -> dict:
    """GET from the Supervisor workspace endpoint. Raises HTTPException on failure."""
    url = f"{_supervisor_url()}{path}"
    try:
        resp = httpx.get(url, timeout=10.0)
    except httpx.ConnectError as exc:
        logger.error("workspace: supervisor unreachable at %s: %s", url, exc)
        raise HTTPException(status_code=503, detail="Supervisor is not reachable")
    except httpx.TimeoutException:
        raise HTTPException(status_code=504, detail="Supervisor request timed out")

    if resp.status_code >= 400:
        detail = _extract_detail(resp)
        raise HTTPException(status_code=resp.status_code, detail=detail)

    return resp.json()


def _extract_detail(resp: httpx.Response) -> str:
    if resp.headers.get("content-type", "").startswith("application/json"):
        try:
            return resp.json().get("detail", resp.text)
        except Exception:
            pass
    return resp.text


class _ChatBody(BaseModel):
    message: str
    conversation_history: list[dict] = Field(default_factory=list)


class _ActionConfirmBody(BaseModel):
    action_id: str


class _IssueConfirmBody(BaseModel):
    draft_id: str


@project_router.post("/{project_id}/workspace/chat")
def workspace_chat(
    project_id: str,
    body: _ChatBody,
    project_root: Path = Depends(resolve_project),
) -> dict:
    logger.info("workspace: forwarding chat project_id=%s", project_id)
    return _forward(
        f"/workspace/projects/{project_id}/chat",
        body.model_dump(),
    )


@project_router.post("/{project_id}/workspace/actions/confirm")
def workspace_action_confirm(
    project_id: str,
    body: _ActionConfirmBody,
    project_root: Path = Depends(resolve_project),
) -> dict:
    logger.info("workspace: forwarding action confirm project_id=%s action_id=%s", project_id, body.action_id)
    return _forward(
        f"/workspace/projects/{project_id}/actions/confirm",
        body.model_dump(),
    )


@project_router.post("/{project_id}/workspace/issues/confirm")
def workspace_issue_confirm(
    project_id: str,
    body: _IssueConfirmBody,
    project_root: Path = Depends(resolve_project),
) -> dict:
    logger.info("workspace: forwarding issue confirm project_id=%s draft_id=%s", project_id, body.draft_id)
    return _forward(
        f"/workspace/projects/{project_id}/issues/confirm",
        body.model_dump(),
    )


@project_router.get("/{project_id}/workspace/deployments/{deployment_id}")
def workspace_get_deployment(
    project_id: str,
    deployment_id: str,
    project_root: Path = Depends(resolve_project),
) -> dict:
    logger.info(
        "workspace: forwarding deployment status project_id=%s deployment_id=%s",
        project_id, deployment_id,
    )
    return _forward_get(f"/workspace/projects/{project_id}/deployments/{deployment_id}")
