import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse

from ..models.schemas import ActionResult, TicketSummary
from ..services import artifact_reader, subprocess_runner

logger = logging.getLogger("control-api")
router = APIRouter(prefix="/tickets", tags=["tickets"])


def _root(request: Request):
    return request.app.state.project_root


def _get_or_404(project_root, ticket_id: str) -> TicketSummary:
    try:
        ticket = artifact_reader.get_ticket(project_root, ticket_id)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"invalid ticket_id: {ticket_id!r}")
    if ticket is None:
        raise HTTPException(status_code=404, detail=f"ticket {ticket_id} not found")
    return ticket


# ── read endpoints ────────────────────────────────────────────────────────────

@router.get("", response_model=list[TicketSummary])
def list_tickets(request: Request) -> list[TicketSummary]:
    return artifact_reader.list_tickets(_root(request))


@router.get("/{ticket_id}", response_model=TicketSummary)
def get_ticket(ticket_id: str, request: Request) -> TicketSummary:
    return _get_or_404(_root(request), ticket_id)


@router.get("/{ticket_id}/logs", response_class=PlainTextResponse)
def get_logs(ticket_id: str, request: Request) -> str:
    _get_or_404(_root(request), ticket_id)
    logs = artifact_reader.get_ticket_logs(_root(request), ticket_id)
    if logs is None:
        raise HTTPException(status_code=404, detail="no logs found")
    return logs


@router.get("/{ticket_id}/artifacts")
def get_artifacts(ticket_id: str, request: Request) -> dict[str, Any]:
    _get_or_404(_root(request), ticket_id)
    return artifact_reader.get_ticket_artifacts(_root(request), ticket_id)


@router.get("/{ticket_id}/plan", response_class=PlainTextResponse)
def get_plan(ticket_id: str, request: Request) -> str:
    _get_or_404(_root(request), ticket_id)
    content = artifact_reader.get_ticket_plan(_root(request), ticket_id)
    if content is None:
        raise HTTPException(status_code=404, detail="plan not found")
    return content


@router.get("/{ticket_id}/review", response_class=PlainTextResponse)
def get_review(ticket_id: str, request: Request) -> str:
    _get_or_404(_root(request), ticket_id)
    content = artifact_reader.get_ticket_review(_root(request), ticket_id)
    if content is None:
        raise HTTPException(status_code=404, detail="review not found")
    return content


@router.get("/{ticket_id}/tests", response_class=PlainTextResponse)
def get_tests(ticket_id: str, request: Request) -> str:
    _get_or_404(_root(request), ticket_id)
    content = artifact_reader.get_ticket_tests(_root(request), ticket_id)
    if content is None:
        raise HTTPException(status_code=404, detail="test report not found")
    return content


# ── workflow action endpoints ─────────────────────────────────────────────────

@router.post("/{ticket_id}/approve-plan", response_model=ActionResult)
def approve_plan(ticket_id: str, request: Request) -> ActionResult:
    logger.info("api: POST /tickets/%s/approve-plan", ticket_id)
    _get_or_404(_root(request), ticket_id)
    return subprocess_runner.approve_plan(ticket_id, _root(request))


@router.post("/{ticket_id}/request-plan-fix", response_model=ActionResult)
def request_plan_fix(ticket_id: str, request: Request) -> ActionResult:
    logger.info("api: POST /tickets/%s/request-plan-fix", ticket_id)
    _get_or_404(_root(request), ticket_id)
    return subprocess_runner.request_plan_fix(ticket_id, _root(request))


@router.post("/{ticket_id}/approve-implementation", response_model=ActionResult)
def approve_implementation(ticket_id: str, request: Request) -> ActionResult:
    logger.info("api: POST /tickets/%s/approve-implementation", ticket_id)
    _get_or_404(_root(request), ticket_id)
    return subprocess_runner.approve_implementation(ticket_id, _root(request))


@router.post("/{ticket_id}/request-implementation-fix", response_model=ActionResult)
def request_implementation_fix(ticket_id: str, request: Request) -> ActionResult:
    logger.info("api: POST /tickets/%s/request-implementation-fix", ticket_id)
    _get_or_404(_root(request), ticket_id)
    return subprocess_runner.request_implementation_fix(ticket_id, _root(request))


@router.post("/{ticket_id}/run-next", response_model=ActionResult, status_code=202)
def run_next(ticket_id: str, request: Request) -> ActionResult:
    logger.info("api: POST /tickets/%s/run-next", ticket_id)
    _get_or_404(_root(request), ticket_id)
    from fastapi.background import BackgroundTasks
    result_holder: list[ActionResult] = []

    def _bg() -> None:
        result_holder.append(subprocess_runner.run_next(ticket_id, _root(request)))

    import threading
    t = threading.Thread(target=_bg, daemon=True)
    t.start()
    return ActionResult(ok=True, message="run-next dispatched in background")


# ── git action endpoints ──────────────────────────────────────────────────────

@router.post("/{ticket_id}/commit", response_model=ActionResult)
def commit(ticket_id: str, request: Request) -> ActionResult:
    logger.info("api: POST /tickets/%s/commit", ticket_id)
    _get_or_404(_root(request), ticket_id)
    return subprocess_runner.commit_ticket(ticket_id, _root(request))


@router.post("/{ticket_id}/push", response_model=ActionResult)
def push(ticket_id: str, request: Request) -> ActionResult:
    logger.info("api: POST /tickets/%s/push", ticket_id)
    _get_or_404(_root(request), ticket_id)
    return subprocess_runner.push_ticket(ticket_id, _root(request))


@router.post("/{ticket_id}/checkpoint", response_model=ActionResult)
def checkpoint(ticket_id: str, request: Request) -> ActionResult:
    logger.info("api: checkpoint requested for %s", ticket_id)
    _get_or_404(_root(request), ticket_id)
    return subprocess_runner.checkpoint_ticket(ticket_id, _root(request))
