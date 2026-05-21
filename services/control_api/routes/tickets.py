import json
import logging
import sys
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import PlainTextResponse

from ..models.schemas import ActionResult, AuditEvent, TicketSummary, TimelineResponse
from ..services import artifact_reader, subprocess_runner

_TOOLS_DIR = Path(__file__).resolve().parents[3] / "tools" / "agent_runner"
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))
import runtime_db  # noqa: E402

logger = logging.getLogger("control-api")
router = APIRouter(prefix="/tickets", tags=["tickets"])


def _root(request: Request) -> Path:
    return request.app.state.project_root


def _worktrees_dir(request: Request) -> Path | None:
    return getattr(request.app.state, "worktrees_dir", None)


def _db_path(request: Request) -> Path | None:
    return getattr(request.app.state, "db_path", None)


def _log_action(request: Request, ticket_id: str, action: str, result: ActionResult) -> None:
    db = _db_path(request)
    if db is None:
        return
    msg = f"{action} ok" if result.ok else f"{action} failed: {result.stderr or result.message}"
    try:
        runtime_db.append_runtime_event(
            db,
            ticket_id,
            event_type=f"action:{action}",
            message=msg,
            metadata={"ok": result.ok, "returncode": result.returncode},
        )
    except Exception:
        logger.exception("audit log write failed for %s/%s (non-fatal)", ticket_id, action)


def _get_or_404(project_root: Path, ticket_id: str, worktrees_dir: Path | None = None) -> TicketSummary:
    try:
        ticket = artifact_reader.get_ticket(project_root, ticket_id, worktrees_dir=worktrees_dir)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"invalid ticket_id: {ticket_id!r}")
    if ticket is None:
        raise HTTPException(status_code=404, detail=f"ticket {ticket_id} not found")
    return ticket


# ── read endpoints ────────────────────────────────────────────────────────────

@router.get("", response_model=list[TicketSummary])
def list_tickets(request: Request) -> list[TicketSummary]:
    return artifact_reader.list_tickets(_root(request), worktrees_dir=_worktrees_dir(request))


@router.get("/{ticket_id}", response_model=TicketSummary)
def get_ticket(ticket_id: str, request: Request) -> TicketSummary:
    return _get_or_404(_root(request), ticket_id, _worktrees_dir(request))


@router.get("/{ticket_id}/state")
def get_state(ticket_id: str, request: Request) -> dict[str, Any]:
    _get_or_404(_root(request), ticket_id, _worktrees_dir(request))
    state = artifact_reader.get_ticket_state(_root(request), ticket_id, worktrees_dir=_worktrees_dir(request))
    if state is None:
        raise HTTPException(status_code=404, detail="state.json not found")
    return state


@router.get("/{ticket_id}/logs", response_class=PlainTextResponse)
def get_logs(ticket_id: str, request: Request) -> str:
    _get_or_404(_root(request), ticket_id, _worktrees_dir(request))
    logs = artifact_reader.get_ticket_logs(_root(request), ticket_id, worktrees_dir=_worktrees_dir(request))
    if logs is None:
        raise HTTPException(status_code=404, detail="no logs found")
    return logs


@router.get("/{ticket_id}/artifacts")
def get_artifacts(ticket_id: str, request: Request) -> dict[str, Any]:
    _get_or_404(_root(request), ticket_id, _worktrees_dir(request))
    return artifact_reader.get_ticket_artifacts(_root(request), ticket_id, worktrees_dir=_worktrees_dir(request))


@router.get("/{ticket_id}/plan", response_class=PlainTextResponse)
def get_plan(ticket_id: str, request: Request) -> str:
    _get_or_404(_root(request), ticket_id, _worktrees_dir(request))
    content = artifact_reader.get_ticket_plan(_root(request), ticket_id, worktrees_dir=_worktrees_dir(request))
    if content is None:
        raise HTTPException(status_code=404, detail="plan not found")
    return content


@router.get("/{ticket_id}/review", response_class=PlainTextResponse)
def get_review(ticket_id: str, request: Request) -> str:
    _get_or_404(_root(request), ticket_id, _worktrees_dir(request))
    content = artifact_reader.get_ticket_review(_root(request), ticket_id, worktrees_dir=_worktrees_dir(request))
    if content is None:
        raise HTTPException(status_code=404, detail="review not found")
    return content


@router.get("/{ticket_id}/tests", response_class=PlainTextResponse)
def get_tests(ticket_id: str, request: Request) -> str:
    _get_or_404(_root(request), ticket_id, _worktrees_dir(request))
    content = artifact_reader.get_ticket_tests(_root(request), ticket_id, worktrees_dir=_worktrees_dir(request))
    if content is None:
        raise HTTPException(status_code=404, detail="test report not found")
    return content


@router.get("/{ticket_id}/timeline", response_model=TimelineResponse)
def get_timeline(ticket_id: str, request: Request) -> TimelineResponse:
    _get_or_404(_root(request), ticket_id, _worktrees_dir(request))
    timeline = artifact_reader.get_ticket_timeline(_root(request), ticket_id, worktrees_dir=_worktrees_dir(request))
    if timeline is None:
        raise HTTPException(status_code=404, detail="timeline not available")
    return timeline


# ── workflow action endpoints ─────────────────────────────────────────────────

@router.post("/{ticket_id}/approve-plan", response_model=ActionResult)
def approve_plan(ticket_id: str, request: Request) -> ActionResult:
    logger.info("api: POST /tickets/%s/approve-plan", ticket_id)
    _get_or_404(_root(request), ticket_id, _worktrees_dir(request))
    result = subprocess_runner.approve_plan(ticket_id, _root(request), _worktrees_dir(request))
    _log_action(request, ticket_id, "approve-plan", result)
    return result


@router.post("/{ticket_id}/request-plan-fix", response_model=ActionResult)
def request_plan_fix(ticket_id: str, request: Request) -> ActionResult:
    logger.info("api: POST /tickets/%s/request-plan-fix", ticket_id)
    _get_or_404(_root(request), ticket_id, _worktrees_dir(request))
    result = subprocess_runner.request_plan_fix(ticket_id, _root(request), _worktrees_dir(request))
    _log_action(request, ticket_id, "request-plan-fix", result)
    return result


@router.post("/{ticket_id}/approve-implementation", response_model=ActionResult)
def approve_implementation(ticket_id: str, request: Request) -> ActionResult:
    logger.info("api: POST /tickets/%s/approve-implementation", ticket_id)
    _get_or_404(_root(request), ticket_id, _worktrees_dir(request))
    result = subprocess_runner.approve_implementation(ticket_id, _root(request), _worktrees_dir(request))
    _log_action(request, ticket_id, "approve-implementation", result)
    return result


@router.post("/{ticket_id}/request-implementation-fix", response_model=ActionResult)
def request_implementation_fix(ticket_id: str, request: Request) -> ActionResult:
    logger.info("api: POST /tickets/%s/request-implementation-fix", ticket_id)
    _get_or_404(_root(request), ticket_id, _worktrees_dir(request))
    result = subprocess_runner.request_implementation_fix(ticket_id, _root(request), _worktrees_dir(request))
    _log_action(request, ticket_id, "request-implementation-fix", result)
    return result


@router.post("/{ticket_id}/run-next", response_model=ActionResult, status_code=202)
def run_next(ticket_id: str, request: Request) -> ActionResult:
    logger.info("api: POST /tickets/%s/run-next", ticket_id)
    _get_or_404(_root(request), ticket_id, _worktrees_dir(request))
    root = _root(request)
    wt_dir = _worktrees_dir(request)

    import threading

    def _bg() -> None:
        subprocess_runner.run_next(ticket_id, root, wt_dir)

    t = threading.Thread(target=_bg, daemon=True)
    t.start()
    result = ActionResult(ok=True, message="run-next dispatched in background")
    _log_action(request, ticket_id, "run-next", result)
    return result


# ── git action endpoints ──────────────────────────────────────────────────────

@router.post("/{ticket_id}/commit", response_model=ActionResult)
def commit(ticket_id: str, request: Request) -> ActionResult:
    logger.info("api: POST /tickets/%s/commit", ticket_id)
    _get_or_404(_root(request), ticket_id, _worktrees_dir(request))
    result = subprocess_runner.commit_ticket(ticket_id, _root(request), _worktrees_dir(request))
    _log_action(request, ticket_id, "commit", result)
    return result


@router.post("/{ticket_id}/push", response_model=ActionResult)
def push(ticket_id: str, request: Request) -> ActionResult:
    logger.info("api: POST /tickets/%s/push", ticket_id)
    _get_or_404(_root(request), ticket_id, _worktrees_dir(request))
    result = subprocess_runner.push_ticket(ticket_id, _root(request), _worktrees_dir(request))
    _log_action(request, ticket_id, "push", result)
    return result


@router.post("/{ticket_id}/checkpoint", response_model=ActionResult)
def checkpoint(ticket_id: str, request: Request) -> ActionResult:
    logger.info("api: checkpoint requested for %s", ticket_id)
    _get_or_404(_root(request), ticket_id, _worktrees_dir(request))
    result = subprocess_runner.checkpoint_ticket(ticket_id, _root(request), _worktrees_dir(request))
    _log_action(request, ticket_id, "checkpoint", result)
    return result


@router.post("/{ticket_id}/archive", response_model=ActionResult)
def archive(ticket_id: str, request: Request) -> ActionResult:
    logger.info("api: POST /tickets/%s/archive", ticket_id)
    _get_or_404(_root(request), ticket_id, _worktrees_dir(request))
    result = subprocess_runner.archive_ticket(ticket_id, _root(request), _worktrees_dir(request))
    _log_action(request, ticket_id, "archive", result)
    return result


# ── audit log endpoint ────────────────────────────────────────────────────────

@router.get("/{ticket_id}/audit-log", response_model=list[AuditEvent])
def get_audit_log(ticket_id: str, request: Request) -> list[AuditEvent]:
    _get_or_404(_root(request), ticket_id, _worktrees_dir(request))
    db = _db_path(request)
    if db is None:
        return []
    events = runtime_db.list_runtime_events(db, ticket_id=ticket_id)
    result = []
    for e in events:
        if not e["event_type"].startswith("action:"):
            continue
        meta = json.loads(e["metadata_json"]) if e.get("metadata_json") else None
        result.append(AuditEvent(
            id=e["id"],
            event_type=e["event_type"],
            message=e["message"],
            metadata=meta,
            created_at=e["created_at"],
        ))
    return result
