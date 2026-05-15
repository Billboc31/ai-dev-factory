from fastapi import APIRouter, Request
from ..models.schemas import ActionResult, DaemonStatus
from ..services import daemon_manager

router = APIRouter(prefix="/daemon", tags=["daemon"])


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
