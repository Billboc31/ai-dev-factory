import logging

from fastapi import APIRouter, BackgroundTasks, Request
from ..models.schemas import ActionResult, ProjectMapActivityResponse, ProjectMapResponse
from ..services import project_map_service

logger = logging.getLogger("control-api")
router = APIRouter(prefix="/project-map", tags=["project-map"])


def _root(request: Request):
    return request.app.state.project_root


@router.get("", response_model=ProjectMapResponse)
def get_project_map(request: Request) -> ProjectMapResponse:
    return project_map_service.get_project_map(_root(request))


@router.get("/activity", response_model=ProjectMapActivityResponse)
def get_project_map_activity(request: Request) -> ProjectMapActivityResponse:
    return project_map_service.get_project_map_activity(_root(request))


@router.post("/refresh", response_model=ActionResult)
def refresh_project_map(request: Request, background_tasks: BackgroundTasks) -> ActionResult:
    logger.info("api: POST /project-map/refresh")
    project_root = _root(request)
    worktrees_dir = request.app.state.worktrees_dir
    background_tasks.add_task(
        project_map_service.refresh_project_map,
        project_root,
        worktrees_dir=worktrees_dir,
    )
    return ActionResult(ok=True, message="issue mapper started in background")
