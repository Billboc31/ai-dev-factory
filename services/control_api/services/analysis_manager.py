from __future__ import annotations

import logging

import httpx

from ..models.schemas import ActionResult, AnalysisStatus

logger = logging.getLogger("control-api")


def start_analysis(
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
            f"{supervisor_url}/analysis/start",
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
                message="analysis already in progress",
                error="locked",
            )
        data = resp.json()
        if data.get("ok"):
            return ActionResult(ok=True, message="analysis started")
        err = data.get("error") or "unknown error"
        return ActionResult(ok=False, message=err, error=err)
    except httpx.ConnectError:
        return ActionResult(
            ok=False,
            message="supervisor unreachable",
            error="supervisor_unreachable",
        )


def get_analysis_status(project_id: str, supervisor_url: str | None) -> AnalysisStatus:
    if not supervisor_url:
        return AnalysisStatus()
    try:
        resp = httpx.get(
            f"{supervisor_url}/analysis/{project_id}/status",
            timeout=5.0,
        )
        return AnalysisStatus(**resp.json())
    except Exception:
        return AnalysisStatus()


def get_analysis_logs(
    project_id: str, supervisor_url: str | None, lines: int = 100
) -> list[str]:
    if not supervisor_url:
        return []
    try:
        resp = httpx.get(
            f"{supervisor_url}/analysis/{project_id}/logs",
            params={"lines": lines},
            timeout=5.0,
        )
        return resp.json().get("lines", [])
    except Exception:
        return []
