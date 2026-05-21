import logging
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, Request

from ..dependencies import resolve_project
from ..models.schemas import ActionResult, ProjectMapActivityResponse, ProjectMapResponse
from ..services import project_map_service
from ..services.runtime_resolver import resolve_worktrees_dir

logger = logging.getLogger("control-api")
router = APIRouter(prefix="/project-map", tags=["project-map"])
project_router = APIRouter(prefix="/projects", tags=["project-map"])


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


# ── project-scoped routes ─────────────────────────────────────────────────────

@project_router.get("/{project_id}/project-map", response_model=ProjectMapResponse)
def project_get_project_map(project_root: Path = Depends(resolve_project)) -> ProjectMapResponse:
    return project_map_service.get_project_map(project_root)


@project_router.get("/{project_id}/project-map/activity", response_model=ProjectMapActivityResponse)
def project_get_project_map_activity(project_root: Path = Depends(resolve_project)) -> ProjectMapActivityResponse:
    return project_map_service.get_project_map_activity(project_root)


@project_router.post("/{project_id}/project-map/refresh", response_model=ActionResult)
def project_refresh_project_map(
    background_tasks: BackgroundTasks,
    project_root: Path = Depends(resolve_project),
) -> ActionResult:
    logger.info("api: POST /projects/.../project-map/refresh")
    background_tasks.add_task(
        project_map_service.refresh_project_map,
        project_root,
        worktrees_dir=resolve_worktrees_dir(project_root),
    )
    return ActionResult(ok=True, message="issue mapper started in background")
