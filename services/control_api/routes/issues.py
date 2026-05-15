import logging

from fastapi import APIRouter, Request
from ..models.schemas import ActionResult, IntakeRequest, IntakeStatusResponse
from ..services import subprocess_runner

logger = logging.getLogger("control-api")
router = APIRouter(prefix="/issues", tags=["issues"])


def _root(request: Request):
    return request.app.state.project_root


@router.post("/intake", response_model=ActionResult)
def run_intake(body: IntakeRequest, request: Request) -> ActionResult:
    logger.info("api: POST /issues/intake issue=%d", body.issue_number)
    return subprocess_runner.run_issue_intake(body.issue_number, _root(request))


@router.get("/intake/status", response_model=IntakeStatusResponse)
def intake_status() -> IntakeStatusResponse:
    return IntakeStatusResponse(status="idle", detail="no intake currently running")
