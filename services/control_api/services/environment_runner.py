"""HTTP client for host-side environment provisioning via the supervisor.

Architecture::

    Dashboard → Control API (routes/environments.py)
              → this module
              → supervisor ``/environments/*`` endpoints
              → environment_provision + SandboxManager on the host
"""
from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from ..models.sandbox import SandboxState

logger = logging.getLogger("control-api")

_PROVISION_TIMEOUT = 300.0
_DEFAULT_TIMEOUT = 30.0


class ProvisionError(Exception):
    """Raised when supervisor environment provisioning fails."""

    def __init__(self, detail: str, status_code: int = 500) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


def resolve_supervisor_url(explicit: str | None = None) -> str | None:
    if explicit:
        return explicit.rstrip("/")
    env = os.environ.get("AI_DEV_FACTORY_SUPERVISOR_URL", "").strip()
    return env or None


def _state_from_response(data: dict[str, Any]) -> SandboxState:
    raw = data.get("state")
    if not isinstance(raw, dict):
        raise ProvisionError("invalid supervisor response: missing state", 502)
    return SandboxState.model_validate(raw)


def _raise_for_response(resp: httpx.Response) -> dict[str, Any]:
    try:
        data = resp.json()
    except Exception as exc:
        raise ProvisionError(
            f"supervisor returned non-JSON response ({resp.status_code})",
            502,
        ) from exc
    if resp.status_code >= 400 or not data.get("ok", True):
        err = data.get("error") or data.get("detail") or resp.text or "unknown error"
        raise ProvisionError(str(err), resp.status_code)
    return data


def provision_environment(
    body: dict[str, Any],
    supervisor_url: str | None = None,
) -> SandboxState:
    url = resolve_supervisor_url(supervisor_url)
    if not url:
        raise ProvisionError(
            "supervisor not configured — set AI_DEV_FACTORY_SUPERVISOR_URL",
            503,
        )
    try:
        resp = httpx.post(
            f"{url}/environments/provision",
            json=body,
            timeout=_PROVISION_TIMEOUT,
        )
    except httpx.ConnectError as exc:
        raise ProvisionError("supervisor unreachable", 503) from exc
    except httpx.TimeoutException as exc:
        raise ProvisionError("supervisor provisioning timed out", 504) from exc
    data = _raise_for_response(resp)
    return _state_from_response(data)


def list_environments(supervisor_url: str | None = None) -> list[SandboxState]:
    url = resolve_supervisor_url(supervisor_url)
    if not url:
        return []
    try:
        resp = httpx.get(f"{url}/environments", timeout=_DEFAULT_TIMEOUT)
        data = _raise_for_response(resp)
        items = data.get("environments") or []
        return [SandboxState.model_validate(item) for item in items]
    except httpx.ConnectError:
        raise ProvisionError("supervisor unreachable", 503)


def get_environment(
    env_id: str, supervisor_url: str | None = None
) -> SandboxState:
    url = resolve_supervisor_url(supervisor_url)
    if not url:
        raise ProvisionError("supervisor not configured", 503)
    try:
        resp = httpx.get(f"{url}/environments/{env_id}", timeout=_DEFAULT_TIMEOUT)
    except httpx.ConnectError as exc:
        raise ProvisionError("supervisor unreachable", 503) from exc
    data = _raise_for_response(resp)
    return _state_from_response(data)


def redeploy_environment(
    env_id: str, supervisor_url: str | None = None
) -> SandboxState:
    return _post_state(f"/environments/{env_id}/redeploy", supervisor_url)


def stop_environment(env_id: str, supervisor_url: str | None = None) -> SandboxState:
    return _post_state(f"/environments/{env_id}/stop", supervisor_url)


def refresh_environment(
    env_id: str, supervisor_url: str | None = None
) -> SandboxState:
    return _post_state(f"/environments/{env_id}/refresh", supervisor_url)


def delete_environment(env_id: str, supervisor_url: str | None = None) -> None:
    url = resolve_supervisor_url(supervisor_url)
    if not url:
        raise ProvisionError("supervisor not configured", 503)
    try:
        resp = httpx.delete(
            f"{url}/environments/{env_id}",
            timeout=_PROVISION_TIMEOUT,
        )
    except httpx.ConnectError as exc:
        raise ProvisionError("supervisor unreachable", 503) from exc
    if resp.status_code == 404:
        raise ProvisionError(f"environment not found: {env_id}", 404)
    if resp.status_code >= 400:
        try:
            err = resp.json().get("error") or resp.text
        except Exception:
            err = resp.text
        raise ProvisionError(str(err), resp.status_code)


def get_environment_logs(
    env_id: str,
    supervisor_url: str | None = None,
) -> str:
    url = resolve_supervisor_url(supervisor_url)
    if not url:
        raise ProvisionError("supervisor not configured", 503)
    try:
        resp = httpx.get(
            f"{url}/environments/{env_id}/logs",
            timeout=_DEFAULT_TIMEOUT,
        )
    except httpx.ConnectError as exc:
        raise ProvisionError("supervisor unreachable", 503) from exc
    data = _raise_for_response(resp)
    return str(data.get("logs") or "")


def _post_state(path: str, supervisor_url: str | None) -> SandboxState:
    url = resolve_supervisor_url(supervisor_url)
    if not url:
        raise ProvisionError("supervisor not configured", 503)
    try:
        resp = httpx.post(f"{url}{path}", timeout=_PROVISION_TIMEOUT)
    except httpx.ConnectError as exc:
        raise ProvisionError("supervisor unreachable", 503) from exc
    if resp.status_code == 404:
        raise ProvisionError(f"environment not found", 404)
    data = _raise_for_response(resp)
    return _state_from_response(data)
