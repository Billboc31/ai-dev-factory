"""Ticket Readiness routes — GET /readiness + POST /evaluate-readiness.

Readiness answers only: *can this ticket ENTER the workflow now?* These
endpoints surface ``blocking_reasons`` (workflow-entry blockers only) and
``warnings`` (advisory, non-blocking — including future plan/execution
approvals). They never feed plan-approval, execution-approval, planner-review
or rule-engine state back into the evaluator. See
``tools/agent_runner/ticket_readiness_evaluator.py`` for the contract.
"""

from __future__ import annotations

import logging
import sys
import threading
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request

from ..dependencies import resolve_project, resolve_project_runtime_root
from ..models.schemas import TicketReadiness, TicketReadinessQueued
from ..services.artifact_reader import get_ticket
from ..services.runtime_resolver import resolve_runs_dir, resolve_ticket_run_dir, resolve_worktrees_dir

try:
    from ..services.container_paths import to_container_path
except ImportError:
    def to_container_path(path: Path | str | None) -> Path | None:  # type: ignore[misc]
        return Path(path) if path is not None else None

from .intelligence import _resolve_db_for_project

_TOOLS_DIR = Path(__file__).resolve().parents[3] / "tools" / "agent_runner"
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))
import runtime_db  # noqa: E402
import ticket_readiness_evaluator as _evaluator  # noqa: E402

logger = logging.getLogger("control-api")
router = APIRouter(prefix="/tickets", tags=["readiness"])
project_router = APIRouter(prefix="/projects", tags=["readiness"])


def _root(request: Request) -> Path:
    return request.app.state.project_root


def _db_path(request: Request):
    return getattr(request.app.state, "db_path", None)


def _worktrees_dir(request: Request) -> Path | None:
    return getattr(request.app.state, "worktrees_dir", None)


def _scoped_runtime_root(project_runtime_root: Path | None) -> Path | None:
    return to_container_path(project_runtime_root) if project_runtime_root is not None else None


def _scoped_worktrees(
    request: Request,
    project_root: Path,
    *,
    project_id: str | None = None,
    project_runtime_root: Path | None = None,
) -> Path | None:
    if project_id is not None or project_runtime_root is not None:
        return resolve_worktrees_dir(
            project_root,
            project_id=project_id,
            project_runtime_root=_scoped_runtime_root(project_runtime_root),
        )
    return _worktrees_dir(request)


def _bool_or_none(val) -> bool | None:
    if val is None:
        return None
    return bool(val)


def _parse_row(row: dict) -> TicketReadiness:
    """Convert a raw DB row into a ``TicketReadiness`` response model."""
    return TicketReadiness(
        ticket_id=row["ticket_id"],
        readiness_status=row["readiness_status"],
        ready_candidate=bool(row.get("ready_candidate")),
        blocking_reasons=row.get("blocking_reasons_json") or [],
        warnings=row.get("warnings_json") or [],
        dependency_check_status=row.get("dependency_check_status"),
        approval_check_status=row.get("approval_check_status"),
        context_freshness_status=row.get("context_freshness_status"),
        human_approval_required=_bool_or_none(row.get("human_approval_required")),
        human_approval_present=_bool_or_none(row.get("human_approval_present")),
        main_sha_when_evaluated=row.get("main_sha_when_evaluated"),
        evaluated_at=row.get("evaluated_at"),
        created_at=row.get("created_at"),
        updated_at=row.get("updated_at"),
    )


def _read_ticket_content(
    project_root: Path,
    ticket_id: str,
    worktrees_dir: Path | None,
    *,
    project_id: str | None = None,
    project_runtime_root: Path | None = None,
) -> str:
    try:
        runs_dir = resolve_runs_dir(
            project_root,
            project_id=project_id,
            project_runtime_root=_scoped_runtime_root(project_runtime_root),
        )
        run_dir = resolve_ticket_run_dir(ticket_id, runs_dir, worktrees_dir)
        ticket_path = run_dir / "ticket.md"
        if ticket_path.exists():
            return ticket_path.read_text(encoding="utf-8")
    except Exception as exc:
        logger.warning("could not read ticket.md for %s: %s", ticket_id, exc)
    return ""


@router.get("/{ticket_id}/readiness", response_model=TicketReadiness)
def get_readiness(
    ticket_id: str,
    request: Request,
    project_id: str | None = None,
    project_root: Path | None = None,
    project_runtime_root: Path | None = None,
) -> TicketReadiness:
    logger.info("api: GET /tickets/%s/readiness", ticket_id)
    root = project_root or _root(request)
    prr = _scoped_runtime_root(project_runtime_root)
    wt_dir = _scoped_worktrees(
        request, root, project_id=project_id, project_runtime_root=project_runtime_root
    )

    ticket = get_ticket(root, ticket_id, worktrees_dir=wt_dir, project_runtime_root=prr)
    if ticket is None:
        raise HTTPException(status_code=404, detail=f"ticket {ticket_id} not found")

    db = _resolve_db_for_project(request, project_id) if project_id else _db_path(request)
    if db is None:
        raise HTTPException(status_code=503, detail="database not available")

    row = runtime_db.get_ticket_readiness(db, ticket_id)
    if row is None:
        raise HTTPException(
            status_code=404,
            detail=f"no readiness evaluation found for ticket {ticket_id}",
        )

    return _parse_row(row)


@router.post(
    "/{ticket_id}/evaluate-readiness",
    response_model=TicketReadinessQueued,
    status_code=202,
)
def evaluate_readiness(
    ticket_id: str,
    request: Request,
    project_id: str | None = None,
    project_root: Path | None = None,
    project_runtime_root: Path | None = None,
) -> TicketReadinessQueued:
    logger.info("api: POST /tickets/%s/evaluate-readiness", ticket_id)
    root = project_root or _root(request)
    prr = _scoped_runtime_root(project_runtime_root)
    wt_dir = _scoped_worktrees(
        request, root, project_id=project_id, project_runtime_root=project_runtime_root
    )

    ticket = get_ticket(root, ticket_id, worktrees_dir=wt_dir, project_runtime_root=prr)
    if ticket is None:
        raise HTTPException(status_code=404, detail=f"ticket {ticket_id} not found")

    db = _resolve_db_for_project(request, project_id) if project_id else _db_path(request)
    if db is None:
        raise HTTPException(status_code=503, detail="database not available")

    existing = runtime_db.get_ticket_readiness(db, ticket_id)
    if existing and existing.get("readiness_status") in {"queued", "running"}:
        return TicketReadinessQueued(
            ticket_id=ticket_id,
            readiness_status=existing["readiness_status"],
        )

    ticket_content = _read_ticket_content(
        root, ticket_id, wt_dir, project_id=project_id, project_runtime_root=project_runtime_root
    )

    runtime_db.upsert_ticket_readiness(db, ticket_id, readiness_status="queued")

    def _bg() -> None:
        try:
            _evaluator.run_evaluation(
                db, ticket_id, ticket_content, root, project_id=project_id
            )
        except Exception:
            logger.exception("readiness evaluation background error for %s", ticket_id)

    t = threading.Thread(target=_bg, daemon=True)
    t.start()

    return TicketReadinessQueued(ticket_id=ticket_id, readiness_status="queued")


@project_router.get(
    "/{project_id}/tickets/{ticket_id}/readiness",
    response_model=TicketReadiness,
)
def get_readiness_project(
    project_id: str,
    ticket_id: str,
    request: Request,
    project_root: Path = Depends(resolve_project),
    project_runtime_root: Path | None = Depends(resolve_project_runtime_root),
) -> TicketReadiness:
    return get_readiness(
        ticket_id,
        request,
        project_id=project_id,
        project_root=project_root,
        project_runtime_root=project_runtime_root,
    )


@project_router.post(
    "/{project_id}/tickets/{ticket_id}/evaluate-readiness",
    response_model=TicketReadinessQueued,
    status_code=202,
)
def evaluate_readiness_project(
    project_id: str,
    ticket_id: str,
    request: Request,
    project_root: Path = Depends(resolve_project),
    project_runtime_root: Path | None = Depends(resolve_project_runtime_root),
) -> TicketReadinessQueued:
    return evaluate_readiness(
        ticket_id,
        request,
        project_id=project_id,
        project_root=project_root,
        project_runtime_root=project_runtime_root,
    )
