from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, Depends

from ..dependencies import resolve_project
from ..models.schemas import DeployerStatus, ScanResult
from ..services import project_scanner

logger = logging.getLogger("control-api")

project_router = APIRouter(prefix="/projects", tags=["deployer"])


@project_router.get("/{project_id}/deployer/status", response_model=DeployerStatus)
def get_deployer_status(
    project_id: str,
    project_root: Path = Depends(resolve_project),
) -> DeployerStatus:
    profile_present = (project_root / ".ai-dev-factory" / "deploy.yml").exists()
    return DeployerStatus(state="idle", profile_present=profile_present, project_id=project_id)


@project_router.post("/{project_id}/deployer/scan", response_model=ScanResult)
def scan_project(
    project_id: str,
    project_root: Path = Depends(resolve_project),
) -> ScanResult:
    logger.info("api: POST /projects/%s/deployer/scan", project_id)
    return project_scanner.scan_project(project_root)
