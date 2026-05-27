from __future__ import annotations

import logging
import os
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from ..dependencies import resolve_project
from ..models.schemas import (
    ActionResult,
    AnalysisStatus,
    DeployLogsResponse,
    DeployerStatus,
    ScanResult,
    ScriptsStatus,
)
from ..services import analysis_manager, deployer_runner, project_scanner, scripts_manager

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
        smoke_status=state.smoke_status,
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


@project_router.post(
    "/{project_id}/deployer/analyze",
    response_model=AnalysisStatus,
    status_code=202,
)
def analyze_project(
    project_id: str,
    request: Request,
    project_root: Path = Depends(resolve_project),
) -> AnalysisStatus:
    logger.info("api: POST /projects/%s/deployer/analyze", project_id)
    exec_cmd = getattr(request.app.state, "daemon_exec_cmd", "claude --dangerously-skip-permissions")
    supervisor_url = os.environ.get("AI_DEV_FACTORY_SUPERVISOR_URL", "").rstrip("/") or None

    result = analysis_manager.start_analysis(
        project_id, str(project_root), exec_cmd, supervisor_url
    )
    if result.error in ("no_supervisor_url", "supervisor_unreachable"):
        raise HTTPException(status_code=503, detail=result.message)
    if result.error == "locked":
        raise HTTPException(status_code=409, detail="analysis already in progress")
    if not result.ok:
        raise HTTPException(status_code=500, detail=result.message)

    return analysis_manager.get_analysis_status(project_id, supervisor_url)


@project_router.get(
    "/{project_id}/deployer/analysis/status",
    response_model=AnalysisStatus,
)
def get_analysis_status(
    project_id: str,
    project_root: Path = Depends(resolve_project),
) -> AnalysisStatus:
    supervisor_url = os.environ.get("AI_DEV_FACTORY_SUPERVISOR_URL", "").rstrip("/") or None
    return analysis_manager.get_analysis_status(project_id, supervisor_url)


@project_router.get(
    "/{project_id}/deployer/analysis/logs",
    response_model=DeployLogsResponse,
)
def get_analysis_logs(
    project_id: str,
    project_root: Path = Depends(resolve_project),
    lines: int = Query(default=100, ge=1, le=10000),
) -> DeployLogsResponse:
    supervisor_url = os.environ.get("AI_DEV_FACTORY_SUPERVISOR_URL", "").rstrip("/") or None
    log_lines = analysis_manager.get_analysis_logs(project_id, supervisor_url, lines)
    return DeployLogsResponse(lines=log_lines)


@project_router.post(
    "/{project_id}/deployer/generate-scripts",
    response_model=ScriptsStatus,
    status_code=202,
)
def generate_scripts(
    project_id: str,
    request: Request,
    project_root: Path = Depends(resolve_project),
) -> ScriptsStatus:
    logger.info("api: POST /projects/%s/deployer/generate-scripts", project_id)
    exec_cmd = getattr(request.app.state, "daemon_exec_cmd", "claude --dangerously-skip-permissions")
    supervisor_url = os.environ.get("AI_DEV_FACTORY_SUPERVISOR_URL", "").rstrip("/") or None

    result = scripts_manager.start_scripts(
        project_id, str(project_root), exec_cmd, supervisor_url
    )
    if result.error in ("no_supervisor_url", "supervisor_unreachable"):
        raise HTTPException(status_code=503, detail=result.message)
    if result.error == "locked":
        raise HTTPException(status_code=409, detail="scripts generation already in progress")
    if not result.ok:
        raise HTTPException(status_code=500, detail=result.message)

    return scripts_manager.get_scripts_status(project_id, supervisor_url)


@project_router.get(
    "/{project_id}/deployer/scripts/status",
    response_model=ScriptsStatus,
)
def get_scripts_status(
    project_id: str,
    project_root: Path = Depends(resolve_project),
) -> ScriptsStatus:
    supervisor_url = os.environ.get("AI_DEV_FACTORY_SUPERVISOR_URL", "").rstrip("/") or None
    return scripts_manager.get_scripts_status(project_id, supervisor_url)


@project_router.get(
    "/{project_id}/deployer/scripts/logs",
    response_model=DeployLogsResponse,
)
def get_scripts_logs(
    project_id: str,
    project_root: Path = Depends(resolve_project),
    lines: int = Query(default=100, ge=1, le=10000),
) -> DeployLogsResponse:
    supervisor_url = os.environ.get("AI_DEV_FACTORY_SUPERVISOR_URL", "").rstrip("/") or None
    log_lines = scripts_manager.get_scripts_logs(project_id, supervisor_url, lines)
    return DeployLogsResponse(lines=log_lines)
