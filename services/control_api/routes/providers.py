import logging
import subprocess
from pathlib import Path

from fastapi import APIRouter, Request
from ..models.schemas import ProjectInfo, ProviderStatus
from ..services import artifact_reader

logger = logging.getLogger("control-api")
router = APIRouter(tags=["providers"])


def _root(request: Request):
    return request.app.state.project_root


def _check_gh() -> ProviderStatus:
    try:
        result = subprocess.run(
            ["gh", "auth", "status"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        if result.returncode == 0:
            return ProviderStatus(name="github", available=True)
        return ProviderStatus(name="github", available=False, detail=result.stderr.strip() or "not authenticated")
    except (FileNotFoundError, subprocess.TimeoutExpired) as exc:
        return ProviderStatus(name="github", available=False, detail=str(exc))


@router.get("/providers/status", response_model=list[ProviderStatus])
def providers_status() -> list[ProviderStatus]:
    return [_check_gh()]


@router.get("/projects", response_model=list[ProjectInfo])
def list_projects(request: Request) -> list[ProjectInfo]:
    root = _root(request)
    tickets = artifact_reader.list_tickets(root)
    return [
        ProjectInfo(
            name=root.name,
            root=str(root),
            tickets_count=len(tickets),
        )
    ]
