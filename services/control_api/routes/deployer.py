from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query

from ..dependencies import resolve_project
from ..models.schemas import ActionResult, DeployerStatus, DeployLogsResponse, ScanResult
from ..services import deployer_runner, project_scanner

logger = logging.getLogger("control-api")

project_router = APIRouter(prefix="/projects", tags=["deployer"])


@project_router.get("/{project_id}/deployer/status", response_model=DeployerStatus)
def get_deployer_status(
    project_id: str,
    project_root: Path = Depends(resolve_project),
) -> DeployerStatus:
    profile_present = (project_root / ".ai-dev-factory" / "deploy.yml").exists()
    state = deployer_runner.get_deploy_state(project_root)
    return DeployerStatus(
        state=state.state,
        profile_present=profile_present,
        project_id=project_id,
        started_at=state.started_at,
        finished_at=state.finished_at,
        error=state.error,
        last_step=state.last_step,
    )


@project_router.post("/{project_id}/deployer/deploy", response_model=ActionResult)
def trigger_deploy(
    project_id: str,
    project_root: Path = Depends(resolve_project),
) -> ActionResult:
    logger.info("api: POST /projects/%s/deployer/deploy", project_id)
    result = deployer_runner.run_deploy(project_id, project_root)
    if result.error == "locked":
        raise HTTPException(status_code=409, detail="deploy already in progress")
    return result


@project_router.post("/{project_id}/deployer/restart", response_model=ActionResult)
def trigger_restart(
    project_id: str,
    project_root: Path = Depends(resolve_project),
) -> ActionResult:
    logger.info("api: POST /projects/%s/deployer/restart", project_id)
    result = deployer_runner.run_restart(project_id, project_root)
    if result.error == "locked":
        raise HTTPException(status_code=409, detail="deploy already in progress")
    return result


@project_router.get("/{project_id}/deployer/logs", response_model=DeployLogsResponse)
def get_deploy_logs(
    project_id: str,
    project_root: Path = Depends(resolve_project),
    lines: int = Query(default=100, ge=1, le=10000),
) -> DeployLogsResponse:
    log_lines = deployer_runner.get_deploy_logs(project_root, lines)
    return DeployLogsResponse(lines=log_lines)


@project_router.post("/{project_id}/deployer/scan", response_model=ScanResult)
def scan_project(
    project_id: str,
    project_root: Path = Depends(resolve_project),
) -> ScanResult:
    logger.info("api: POST /projects/%s/deployer/scan", project_id)
    return project_scanner.scan_project(project_root)
