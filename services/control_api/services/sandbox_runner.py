"""HTTP-client manager for the per-project deploy-validation pipeline.

This module replaces the in-container worker (PR #119) that was hitting
host-only paths it could not see. The pipeline now executes on the host
side under the supervisor; this module just proxies dashboard requests
to the supervisor over HTTP, mirroring ``scripts_manager.py`` and
``analysis_manager.py``.

Architecture::

    Dashboard
      → API container (routes/sandbox.py)
        → this module (HTTP client)
          → host supervisor (services/supervisor/main.py)
            → tools/agent_runner/run_sandbox.py

The supervisor performs the container-to-host path translation (via the
shared :class:`ContainerToHostMapper`) before spawning the worker, so
``project_root`` may contain a container path like ``/app``; the
supervisor maps it to e.g. ``/Users/…/clones/ai-dev-factory``.

Public interface (kept identical to the old in-container module so
``routes/sandbox.py`` does not have to change its signature):

* :func:`start_sandbox_validation`
* :func:`get_sandbox_state`
* :func:`get_sandbox_logs`
"""

from __future__ import annotations

import logging
import os

import httpx

from ..models.schemas import (
    ActionResult,
    SandboxValidationState,
    SandboxValidationStep,
)

logger = logging.getLogger("control-api")


def _resolve_supervisor_url(explicit: str | None) -> str | None:
    if explicit:
        return explicit.rstrip("/")
    env = os.environ.get("AI_DEV_FACTORY_SUPERVISOR_URL", "").rstrip("/")
    return env or None


def _state_from_payload(raw: dict) -> SandboxValidationState:
    steps = [
        SandboxValidationStep(
            name=s.get("name", ""),
            status=s.get("status", "skipped"),
            exit_code=s.get("exit_code"),
            started_at=s.get("started_at"),
            finished_at=s.get("finished_at"),
        )
        for s in (raw.get("steps") or [])
    ]
    return SandboxValidationState(
        state=raw.get("state", "idle"),
        sandbox_id=raw.get("sandbox_id"),
        started_at=raw.get("started_at"),
        finished_at=raw.get("finished_at"),
        error=raw.get("error"),
        last_step=raw.get("last_step"),
        steps=steps,
    )


def start_sandbox_validation(
    project_id: str,
    project_root: str,
    supervisor_url: str | None = None,
) -> ActionResult:
    """Ask the supervisor to spawn a host-side sandbox-validation worker.

    ``project_root`` is the **container-side** path. The supervisor maps
    it to its host equivalent before invoking the worker — callers do
    NOT translate it themselves.
    """
    url = _resolve_supervisor_url(supervisor_url)
    if not url:
        return ActionResult(
            ok=False,
            message="supervisor not configured — set AI_DEV_FACTORY_SUPERVISOR_URL",
            error="no_supervisor_url",
        )
    try:
        resp = httpx.post(
            f"{url}/sandbox/start",
            json={"project_root": project_root, "project_id": project_id},
            timeout=10.0,
        )
        if resp.status_code == 409:
            return ActionResult(
                ok=False, message="sandbox already running", error="locked"
            )
        data = resp.json()
        if data.get("ok"):
            return ActionResult(ok=True, message="sandbox validation started")
        err = data.get("error") or "unknown error"
        return ActionResult(ok=False, message=err, error=err)
    except httpx.ConnectError:
        return ActionResult(
            ok=False,
            message="supervisor unreachable",
            error="supervisor_unreachable",
        )


def get_sandbox_state(
    project_id: str,
    supervisor_url: str | None = None,
) -> SandboxValidationState:
    url = _resolve_supervisor_url(supervisor_url)
    if not url:
        return SandboxValidationState(state="idle")
    try:
        resp = httpx.get(
            f"{url}/sandbox/{project_id}/status",
            timeout=5.0,
        )
        return _state_from_payload(resp.json())
    except httpx.ConnectError:
        return SandboxValidationState(
            state="failed", error="supervisor_unreachable"
        )
    except Exception as exc:  # noqa: BLE001 — failure must not propagate to the API
        logger.warning("sandbox: failed to fetch status: %s", exc)
        return SandboxValidationState(state="idle")


def get_sandbox_logs(
    project_id: str,
    supervisor_url: str | None = None,
    lines: int = 100,
) -> list[str]:
    url = _resolve_supervisor_url(supervisor_url)
    if not url:
        return []
    try:
        resp = httpx.get(
            f"{url}/sandbox/{project_id}/logs",
            params={"lines": lines},
            timeout=5.0,
        )
        return resp.json().get("lines", [])
    except Exception as exc:  # noqa: BLE001
        logger.warning("sandbox: failed to fetch logs: %s", exc)
        return []
