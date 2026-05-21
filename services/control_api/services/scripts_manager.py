from __future__ import annotations

import logging

import httpx

from ..models.schemas import ActionResult, ScriptsStatus

logger = logging.getLogger("control-api")


def start_scripts(
    project_id: str,
    project_root: str,
    exec_cmd: str,
    supervisor_url: str | None,
) -> ActionResult:
    if not supervisor_url:
        return ActionResult(
            ok=False,
            message="supervisor not configured",
            error="no_supervisor_url",
        )
    try:
        resp = httpx.post(
            f"{supervisor_url}/scripts/start",
            json={
                "project_root": project_root,
                "project_id": project_id,
                "exec_cmd": exec_cmd,
            },
            timeout=10.0,
        )
        if resp.status_code == 409:
            return ActionResult(
                ok=False,
                message="scripts generation already in progress",
                error="locked",
            )
        data = resp.json()
        if data.get("ok"):
            return ActionResult(ok=True, message="scripts generation started")
        err = data.get("error") or "unknown error"
        return ActionResult(ok=False, message=err, error=err)
    except httpx.ConnectError:
        return ActionResult(
            ok=False,
            message="supervisor unreachable",
            error="supervisor_unreachable",
        )


def get_scripts_status(project_id: str, supervisor_url: str | None) -> ScriptsStatus:
    if not supervisor_url:
        return ScriptsStatus()
    try:
        resp = httpx.get(
            f"{supervisor_url}/scripts/{project_id}/status",
            timeout=5.0,
        )
        return ScriptsStatus(**resp.json())
    except httpx.ConnectError:
        return ScriptsStatus(state="failed", error="supervisor_unreachable")
    except Exception:
        return ScriptsStatus()


def get_scripts_logs(
    project_id: str, supervisor_url: str | None, lines: int = 100
) -> list[str]:
    if not supervisor_url:
        return []
    try:
        resp = httpx.get(
            f"{supervisor_url}/scripts/{project_id}/logs",
            params={"lines": lines},
            timeout=5.0,
        )
        return resp.json().get("lines", [])
    except Exception:
        return []
