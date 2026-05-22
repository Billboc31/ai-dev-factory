"""HTTP-client proxy for the auto-fix proposal workflow (T138).

Architecture::

    Dashboard → API container (routes/auto_fix.py)
      → this module (HTTP client)
        → host supervisor (POST /auto-fix/{project_id}/propose, GET /auto-fix/…)

Mirrors ``sandbox_runner.py`` — callers do NOT translate project_root;
the supervisor performs the container-to-host path mapping.
"""
from __future__ import annotations

import logging
import os

import httpx

logger = logging.getLogger("control-api")


def _resolve_supervisor_url(explicit: str | None) -> str | None:
    if explicit:
        return explicit.rstrip("/")
    env = os.environ.get("AI_DEV_FACTORY_SUPERVISOR_URL", "").rstrip("/")
    return env or None


def propose_auto_fix(
    project_id: str,
    project_root: str,
    exec_cmd: str,
    sandbox_id: str,
    failing_step: str | None = None,
    supervisor_url: str | None = None,
) -> dict:
    """Ask the supervisor to start an auto-fix proposal for a failed sandbox."""
    url = _resolve_supervisor_url(supervisor_url)
    if not url:
        return {"ok": False, "error": "no_supervisor_url"}
    try:
        resp = httpx.post(
            f"{url}/auto-fix/{project_id}/propose",
            json={
                "project_root": project_root,
                "exec_cmd": exec_cmd,
                "sandbox_id": sandbox_id,
                "failing_step": failing_step,
            },
            timeout=10.0,
        )
        if resp.status_code == 409:
            return {"ok": False, "error": "locked"}
        return resp.json()
    except httpx.ConnectError:
        return {"ok": False, "error": "supervisor_unreachable"}


def get_proposal(
    project_id: str,
    proposal_id: str,
    supervisor_url: str | None = None,
) -> dict | None:
    """Fetch a proposal by ID. Returns None if not found or unreachable."""
    url = _resolve_supervisor_url(supervisor_url)
    if not url:
        return None
    try:
        resp = httpx.get(
            f"{url}/auto-fix/{project_id}/proposal/{proposal_id}",
            timeout=5.0,
        )
        if resp.status_code == 404:
            return None
        return resp.json()
    except Exception as exc:  # noqa: BLE001
        logger.warning("auto_fix: failed to fetch proposal %s: %s", proposal_id, exc)
        return None


def list_proposals(
    project_id: str,
    supervisor_url: str | None = None,
) -> list[dict]:
    """List all proposals for a project. Returns empty list on error."""
    url = _resolve_supervisor_url(supervisor_url)
    if not url:
        return []
    try:
        resp = httpx.get(
            f"{url}/auto-fix/{project_id}/proposals",
            timeout=5.0,
        )
        return resp.json().get("proposals", [])
    except Exception as exc:  # noqa: BLE001
        logger.warning("auto_fix: failed to list proposals for %s: %s", project_id, exc)
        return []
