from pathlib import Path

from fastapi import APIRouter, Depends, Query, Request

from ..dependencies import resolve_project
from ..models.schemas import ActionResult, DaemonActivity, DaemonStatus, BoardResponse, RuntimeStatus
from ..services import daemon_manager, board_service
from ..services.runtime_resolver import resolve_worktrees_dir

router = APIRouter(prefix="/daemon", tags=["daemon"])
project_router = APIRouter(prefix="/projects", tags=["daemon"])


def _root(request: Request):
    return request.app.state.project_root


@router.get("/status", response_model=DaemonStatus)
def daemon_status(request: Request) -> DaemonStatus:
    return daemon_manager.get_status(_root(request))


@router.post("/start", response_model=ActionResult)
def daemon_start(request: Request) -> ActionResult:
    exec_cmd = getattr(request.app.state, "daemon_exec_cmd", "claude --dangerously-skip-permissions")
    return daemon_manager.start(_root(request), exec_cmd)


@router.post("/stop", response_model=ActionResult)
def daemon_stop(request: Request) -> ActionResult:
    return daemon_manager.stop(_root(request))


@router.post("/restart", response_model=ActionResult)
def daemon_restart(request: Request) -> ActionResult:
    exec_cmd = getattr(request.app.state, "daemon_exec_cmd", "claude --dangerously-skip-permissions")
    return daemon_manager.restart(_root(request), exec_cmd)


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
    return daemon_manager.get_status(project_root)


@project_router.post("/{project_id}/daemon/start", response_model=ActionResult)
def project_daemon_start(request: Request, project_root: Path = Depends(resolve_project)) -> ActionResult:
    exec_cmd = getattr(request.app.state, "daemon_exec_cmd", "claude --dangerously-skip-permissions")
    return daemon_manager.start(project_root, exec_cmd)


@project_router.post("/{project_id}/daemon/stop", response_model=ActionResult)
def project_daemon_stop(project_root: Path = Depends(resolve_project)) -> ActionResult:
    return daemon_manager.stop(project_root)


@project_router.post("/{project_id}/daemon/restart", response_model=ActionResult)
def project_daemon_restart(request: Request, project_root: Path = Depends(resolve_project)) -> ActionResult:
    exec_cmd = getattr(request.app.state, "daemon_exec_cmd", "claude --dangerously-skip-permissions")
    return daemon_manager.restart(project_root, exec_cmd)


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
def project_daemon_board(project_root: Path = Depends(resolve_project)) -> BoardResponse:
    return board_service.get_board(project_root, worktrees_dir=resolve_worktrees_dir(project_root))


@project_router.get("/{project_id}/daemon/runtime-status", response_model=RuntimeStatus)
def project_daemon_runtime_status(project_root: Path = Depends(resolve_project)) -> RuntimeStatus:
    return daemon_manager.get_runtime_status(project_root)
