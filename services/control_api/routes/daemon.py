import os
from pathlib import Path

import httpx
from fastapi import APIRouter, Depends, Query, Request

from ..dependencies import resolve_project, resolve_project_runtime_root
from ..models.schemas import ActionResult, DaemonActivity, DaemonStartRequest, DaemonStatus, BoardResponse, RuntimeStatus
from ..services import daemon_manager, board_service
from ..services.runtime_resolver import resolve_worktrees_dir

router = APIRouter(prefix="/daemon", tags=["daemon"])
project_router = APIRouter(prefix="/projects", tags=["daemon"])


def _root(request: Request):
    return request.app.state.project_root


def _enrich_with_supervisor(status: DaemonStatus) -> DaemonStatus:
    """Ping the supervisor health endpoint and set supervisor_available/supervisor_url."""
    sup_url = os.environ.get("AI_DEV_FACTORY_SUPERVISOR_URL", "").rstrip("/") or None
    if sup_url is None:
        return status
    status.supervisor_url = sup_url
    try:
        resp = httpx.get(f"{sup_url}/health", timeout=2.0)
        status.supervisor_available = resp.status_code == 200
    except Exception:
        status.supervisor_available = False
    return status


@router.get("/status", response_model=DaemonStatus)
def daemon_status(request: Request) -> DaemonStatus:
    status = daemon_manager.get_status(_root(request))
    return _enrich_with_supervisor(status)


@router.post("/start", response_model=ActionResult)
def daemon_start(request: Request, body: DaemonStartRequest = None) -> ActionResult:
    exec_cmd = getattr(request.app.state, "daemon_exec_cmd", "claude --dangerously-skip-permissions")
    restart_policy = body.restart_policy if body else "no-restart"
    return daemon_manager.start(_root(request), exec_cmd, restart_policy)


@router.post("/stop", response_model=ActionResult)
def daemon_stop(request: Request) -> ActionResult:
    return daemon_manager.stop(_root(request))


@router.post("/restart", response_model=ActionResult)
def daemon_restart(request: Request, body: DaemonStartRequest = None) -> ActionResult:
    exec_cmd = getattr(request.app.state, "daemon_exec_cmd", "claude --dangerously-skip-permissions")
    restart_policy = body.restart_policy if body else "no-restart"
    return daemon_manager.restart(_root(request), exec_cmd, restart_policy)


@router.get("/activity", response_model=DaemonActivity)
def daemon_activity(request: Request, lines: int = Query(default=50, ge=1, le=500)) -> DaemonActivity:
    return DaemonActivity(lines=daemon_manager.get_activity(_root(request), lines))


@router.post("/sync-main", response_model=ActionResult)
def daemon_sync_main(request: Request) -> ActionResult:
    return daemon_manager.sync_main(_root(request))


@router.get("/board", response_model=BoardResponse)
def daemon_board(request: Request) -> BoardResponse:
    worktrees_dir = getattr(request.app.state, "worktrees_dir", None)
    return board_service.get_board(_root(request), worktrees_dir=worktrees_dir)


@router.get("/runtime-status", response_model=RuntimeStatus)
def daemon_runtime_status(request: Request) -> RuntimeStatus:
    return daemon_manager.get_runtime_status(_root(request))


# ── project-scoped routes ─────────────────────────────────────────────────────

@project_router.get("/{project_id}/daemon/status", response_model=DaemonStatus)
def project_daemon_status(project_root: Path = Depends(resolve_project)) -> DaemonStatus:
    status = daemon_manager.get_status(project_root)
    return _enrich_with_supervisor(status)


@project_router.post("/{project_id}/daemon/start", response_model=ActionResult)
def project_daemon_start(request: Request, body: DaemonStartRequest = None, project_root: Path = Depends(resolve_project)) -> ActionResult:
    exec_cmd = getattr(request.app.state, "daemon_exec_cmd", "claude --dangerously-skip-permissions")
    restart_policy = body.restart_policy if body else "no-restart"
    return daemon_manager.start(project_root, exec_cmd, restart_policy)


@project_router.post("/{project_id}/daemon/stop", response_model=ActionResult)
def project_daemon_stop(project_root: Path = Depends(resolve_project)) -> ActionResult:
    return daemon_manager.stop(project_root)


@project_router.post("/{project_id}/daemon/restart", response_model=ActionResult)
def project_daemon_restart(request: Request, body: DaemonStartRequest = None, project_root: Path = Depends(resolve_project)) -> ActionResult:
    exec_cmd = getattr(request.app.state, "daemon_exec_cmd", "claude --dangerously-skip-permissions")
    restart_policy = body.restart_policy if body else "no-restart"
    return daemon_manager.restart(project_root, exec_cmd, restart_policy)


@project_router.get("/{project_id}/daemon/activity", response_model=DaemonActivity)
def project_daemon_activity(
    project_root: Path = Depends(resolve_project),
    lines: int = Query(default=50, ge=1, le=500),
) -> DaemonActivity:
    return DaemonActivity(lines=daemon_manager.get_activity(project_root, lines))


@project_router.post("/{project_id}/daemon/sync-main", response_model=ActionResult)
def project_daemon_sync_main(project_root: Path = Depends(resolve_project)) -> ActionResult:
    return daemon_manager.sync_main(project_root)


@project_router.get("/{project_id}/daemon/board", response_model=BoardResponse)
def project_daemon_board(
    request: Request,
    project_root: Path = Depends(resolve_project),
    project_runtime_root: Path | None = Depends(resolve_project_runtime_root),
) -> BoardResponse:
    worktrees_dir = resolve_worktrees_dir(project_root, project_runtime_root=project_runtime_root)
    return board_service.get_board(project_root, worktrees_dir=worktrees_dir)


@project_router.get("/{project_id}/daemon/runtime-status", response_model=RuntimeStatus)
def project_daemon_runtime_status(project_root: Path = Depends(resolve_project)) -> RuntimeStatus:
    return daemon_manager.get_runtime_status(project_root)
