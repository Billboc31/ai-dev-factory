"""Backlog batch dashboard routes (T219).

Read-only views and guarded operator actions for the new dashboard section
``/projects/<id>/dispatcher/batches``. The action endpoints wrap existing
``backlog_batch`` lifecycle helpers; no new state-machine logic lives here.
"""

from __future__ import annotations

import logging
import os
import re
import sys
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request

from ..dependencies import resolve_project, resolve_project_runtime_root
from ..models.schemas import (
    BatchActionResponse,
    BatchAnalysisSummary,
    BatchBlockedTicket,
    BatchConflict,
    BatchCurrentResponse,
    BatchDetailResponse,
    BatchGraphEdge,
    BatchGraphNode,
    BatchGraphResponse,
    BatchInsightsResponse,
    BatchListResponse,
    BatchPhase,
    BatchPhasesResponse,
    BatchSummary,
    BatchTicketDetail,
)
from ..services.container_paths import to_container_path
from ..services.runtime_resolver import resolve_worktrees_dir

_TOOLS_DIR = Path(__file__).resolve().parents[3] / "tools" / "agent_runner"
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

import backlog_batch as _backlog_batch  # noqa: E402
import runtime_db  # noqa: E402
import dependency_conflicts as _dep_conflicts  # noqa: E402
import ticket_dispatcher as _dispatcher  # noqa: E402

logger = logging.getLogger("control-api")
router = APIRouter(prefix="/dispatcher/batches", tags=["batches"])
project_router = APIRouter(prefix="/projects", tags=["batches"])


# ── color/status helpers ─────────────────────────────────────────────────────

_DONE_STATES = frozenset({"DONE", "MERGED", "ARCHIVED", "TEST_COMPLETE"})
_RUNNING_STATES = frozenset({"PLANNING", "CODING", "REVIEWING", "RUNNING"})
_HUMAN_GATE_STATES = frozenset({
    "PLAN_REVIEW_NEEDED",
    "IMPLEMENTATION_REVIEW_NEEDED",
    "MEMORY_REVIEW_NEEDED",
    "CONFLICT_RESOLUTION_NEEDED",
    "CONFLICT_RESOLUTION_FAILED",
    "CONFLICT_RESOLVED_REVIEW_NEEDED",
})
_FAILED_STATES = frozenset({"FAILED", "ERROR", "PLAN_FIX_REQUIRED", "IMPLEMENTATION_FIX_REQUIRED"})


def _ticket_color_key(state: str | None, *, selected: bool) -> str:
    if selected:
        return "selected"
    if not state:
        return "waiting"
    upper = state.upper()
    if upper in _DONE_STATES:
        return "done"
    if upper in _FAILED_STATES:
        return "failed"
    if upper in _RUNNING_STATES:
        return "running"
    if upper in _HUMAN_GATE_STATES:
        return "waiting_human"
    return "waiting"


def _phase_to_int(value) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    text = str(value).strip()
    if not text:
        return None
    match = re.search(r"-?\d+", text)
    if match is None:
        return None
    try:
        return int(match.group(0))
    except ValueError:
        return None


# ── DB resolution (mirrors dispatcher.py) ────────────────────────────────────

def _root(request: Request) -> Path:
    return request.app.state.project_root


def _db_path(request: Request):
    return getattr(request.app.state, "db_path", None)


def _resolve_db_for_project(request: Request, project_id: str | None):
    if not project_id:
        return _db_path(request)
    project_runtime_root = None
    registry = getattr(request.app.state, "project_registry", None)
    if registry is not None:
        prt = registry.resolve_runtime_root(project_id)
        if prt is not None:
            project_runtime_root = to_container_path(prt)
    runtime_configured = bool(
        project_runtime_root is not None
        or os.environ.get("RUNTIME_BASE_ROOT")
        or os.environ.get("AI_DEV_FACTORY_RUNTIME_ROOT")
    )
    if not runtime_configured:
        return _db_path(request)
    try:
        db = runtime_db.resolve_db_path_for_project(project_id, project_runtime_root)
    except Exception:
        db = None
    if db is not None:
        if isinstance(db, Path):
            mapped = to_container_path(db)
            if mapped is not None and mapped.exists():
                return mapped
        elif getattr(db, "exists", lambda: True)():
            return db
    return _db_path(request)


def _worktrees_dir_for(
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
            project_runtime_root=to_container_path(project_runtime_root)
            if project_runtime_root is not None
            else None,
        )
    return getattr(request.app.state, "worktrees_dir", None)


# ── runtime/ticket data helpers ──────────────────────────────────────────────

def _safe(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception:
        logger.exception("batches: %s failed", getattr(fn, "__name__", "?"))
        return None


def _read_ticket_title(
    project_root: Path,
    ticket_id: str,
    *,
    worktrees_dir: Path | None,
) -> str | None:
    """Best-effort: read the first H1 from ``runs/<ticket>/ticket.md``."""
    candidates: list[Path] = []
    if worktrees_dir is not None:
        candidates.append(
            worktrees_dir / ticket_id / "runs" / ticket_id / "ticket.md"
        )
    candidates.append(project_root / "runs" / ticket_id / "ticket.md")
    for candidate in candidates:
        try:
            if not candidate.exists():
                continue
            for line in candidate.read_text(encoding="utf-8").splitlines():
                stripped = line.strip()
                if stripped.startswith("# "):
                    return stripped[2:].strip()
        except Exception:
            continue
    return None


def _ticket_runtime_map(db_path) -> dict[str, dict]:
    rows = _safe(runtime_db.list_ticket_runtime, db_path) or []
    return {(row.get("ticket_id") or ""): row for row in rows if row.get("ticket_id")}


def _dependency_analysis_for_batch(db_path, batch_id: str, ticket_ids: list[str]) -> dict[str, dict]:
    out: dict[str, dict] = {}
    for ticket_id in ticket_ids:
        row = _safe(runtime_db.get_dependency_analysis, db_path, ticket_id, batch_id)
        if row:
            out[ticket_id] = row
    return out


def _dispatcher_payload(
    db_path,
    project_root: Path,
    *,
    project_id: str | None,
    worktrees_dir: Path | None,
) -> dict | None:
    try:
        return _dispatcher.get_recommended_tickets(
            db_path,
            project_root,
            project_id=project_id,
            worktrees_dir=worktrees_dir,
            mode="advisory",
        )
    except Exception:
        logger.exception("batches: dispatcher payload failed")
        return None


def _compute_progress(
    runtime_map: dict[str, dict],
    ticket_ids: list[str],
) -> dict[str, int]:
    done = 0
    running = 0
    waiting = 0
    failed = 0
    for ticket_id in ticket_ids:
        state = (runtime_map.get(ticket_id, {}).get("state") or "").upper()
        if state in _DONE_STATES:
            done += 1
        elif state in _RUNNING_STATES:
            running += 1
        elif state in _FAILED_STATES:
            failed += 1
        else:
            waiting += 1
    return {
        "done": done,
        "running": running,
        "waiting": waiting,
        "failed": failed,
        "total": len(ticket_ids),
    }


def _current_phase(
    analyses: dict[str, dict],
    ticket_ids: list[str],
    runtime_map: dict[str, dict],
) -> int | None:
    """Return the highest fully-completed execution phase, or None."""
    phases: dict[int, list[str]] = {}
    for ticket_id in ticket_ids:
        phase = _phase_to_int(analyses.get(ticket_id, {}).get("execution_phase"))
        if phase is None:
            continue
        phases.setdefault(phase, []).append(ticket_id)
    if not phases:
        return None
    best: int | None = None
    for phase in sorted(phases):
        members = phases[phase]
        if all(
            (runtime_map.get(m, {}).get("state") or "").upper() in _DONE_STATES
            for m in members
        ):
            best = phase
        else:
            break
    return best


def _build_summary(
    db_path,
    batch_row: dict,
) -> BatchSummary:
    batch_id = batch_row.get("batch_id") or ""
    ticket_ids = _safe(runtime_db.list_backlog_batch_ticket_ids, db_path, batch_id) or []
    runtime_map = _ticket_runtime_map(db_path)
    analyses = _dependency_analysis_for_batch(db_path, batch_id, ticket_ids)
    progress = _compute_progress(runtime_map, ticket_ids)
    current_phase = _current_phase(analyses, ticket_ids, runtime_map)
    return BatchSummary(
        batch_id=batch_id,
        status=batch_row.get("status") or "",
        ticket_count=len(ticket_ids),
        created_at=batch_row.get("created_at"),
        frozen_at=batch_row.get("frozen_at"),
        completed_at=batch_row.get("completed_at"),
        last_activity_at=batch_row.get("last_activity_at"),
        freeze_blocked=bool(batch_row.get("freeze_blocked")),
        freeze_blocked_reason=batch_row.get("freeze_blocked_reason"),
        dependency_analysis_attempts=int(
            batch_row.get("dependency_analysis_attempts") or 0
        ),
        last_dependency_analysis_error=batch_row.get("last_dependency_analysis_error"),
        next_dependency_analysis_retry_at=batch_row.get(
            "next_dependency_analysis_retry_at"
        ),
        progress=progress,
        current_phase=current_phase,
    )


def _build_summaries(db_path) -> list[BatchSummary]:
    rows = _safe(runtime_db.list_backlog_batches, db_path) or []
    return [_build_summary(db_path, row) for row in rows]


def _build_ticket_details(
    db_path,
    project_root: Path,
    *,
    batch_id: str,
    ticket_ids: list[str],
    worktrees_dir: Path | None,
    dispatcher_payload: dict | None,
) -> list[BatchTicketDetail]:
    runtime_map = _ticket_runtime_map(db_path)
    analyses = _dependency_analysis_for_batch(db_path, batch_id, ticket_ids)

    selected_ids: set[str] = set()
    blocked_status: dict[str, str | None] = {}
    if dispatcher_payload:
        for rec in dispatcher_payload.get("recommendations") or []:
            tid = rec.get("ticket_id")
            if tid:
                selected_ids.add(tid)
        for b in dispatcher_payload.get("blocked") or []:
            tid = b.get("ticket_id")
            if tid:
                blocked_status[tid] = b.get("status") or "BLOCKED"

    out: list[BatchTicketDetail] = []
    for ticket_id in ticket_ids:
        runtime_row = runtime_map.get(ticket_id, {})
        analysis = analyses.get(ticket_id, {})
        readiness_row = _safe(runtime_db.get_ticket_readiness, db_path, ticket_id) or {}
        readiness_state = readiness_row.get("readiness_status")

        if ticket_id in selected_ids:
            dispatcher_state = "READY_TO_TAKE"
        elif ticket_id in blocked_status:
            dispatcher_state = blocked_status[ticket_id] or "BLOCKED"
        else:
            state_upper = (runtime_row.get("state") or "").upper()
            if state_upper in _RUNNING_STATES:
                dispatcher_state = "RUNNING"
            elif state_upper in _DONE_STATES:
                dispatcher_state = "DONE"
            else:
                dispatcher_state = None

        out.append(
            BatchTicketDetail(
                ticket_id=ticket_id,
                title=_read_ticket_title(
                    project_root, ticket_id, worktrees_dir=worktrees_dir
                ),
                status=runtime_row.get("state"),
                execution_phase=_phase_to_int(analysis.get("execution_phase")),
                parallel_group=analysis.get("parallel_group"),
                depends_on=list(analysis.get("depends_on") or []),
                blocks=list(analysis.get("blocks") or []),
                conflicting_tickets=list(analysis.get("conflicting_tickets") or []),
                readiness_state=readiness_state,
                dispatcher_state=dispatcher_state,
                why_this_phase=analysis.get("why_this_phase"),
                dependencies_inferred=list(analysis.get("dependencies_inferred") or []),
                reasoning=analysis.get("reasoning"),
                confidence=analysis.get("confidence"),
            )
        )
    return out


def _build_analysis_summary(
    db_path, batch_id: str
) -> tuple[BatchAnalysisSummary | None, dict | None]:
    """Fetch the persisted analyzer summary + raw output for the batch.

    Returns ``(summary, raw)`` where each half is ``None`` when nothing has
    been persisted yet. Empty structural dicts still produce a summary object
    so the UI can distinguish "no analysis" from "analysis with no fields".
    """
    payload = _safe(runtime_db.get_batch_analysis_summary, db_path, batch_id)
    if not payload:
        return None, None
    summary_dict = payload.get("analysis_summary") or {}
    raw_output = payload.get("raw_analyzer_output")
    generated_at = payload.get("generated_at")
    summary = BatchAnalysisSummary(
        strategy=summary_dict.get("strategy"),
        foundation_tickets=list(summary_dict.get("foundation_tickets") or []),
        bootstrap_tickets=list(summary_dict.get("bootstrap_tickets") or []),
        important_inferred_dependencies=list(
            summary_dict.get("important_inferred_dependencies") or []
        ),
        parallel_opportunities=list(
            summary_dict.get("parallel_opportunities") or []
        ),
        conflicts_resolved=list(summary_dict.get("conflicts_resolved") or []),
        warnings=list(summary_dict.get("warnings") or []),
        generated_at=generated_at,
    )
    return summary, raw_output


def _build_graph(
    db_path,
    *,
    batch_id: str,
    ticket_ids: list[str],
    dispatcher_payload: dict | None,
) -> BatchGraphResponse:
    runtime_map = _ticket_runtime_map(db_path)
    analyses = _dependency_analysis_for_batch(db_path, batch_id, ticket_ids)
    selected_ids: set[str] = set()
    if dispatcher_payload:
        for rec in dispatcher_payload.get("recommendations") or []:
            tid = rec.get("ticket_id")
            if tid:
                selected_ids.add(tid)

    nodes: list[BatchGraphNode] = []
    for ticket_id in ticket_ids:
        runtime_row = runtime_map.get(ticket_id, {})
        analysis = analyses.get(ticket_id, {})
        selected = ticket_id in selected_ids
        nodes.append(
            BatchGraphNode(
                id=ticket_id,
                label=ticket_id,
                status=runtime_row.get("state"),
                color_key=_ticket_color_key(runtime_row.get("state"), selected=selected),
                execution_phase=_phase_to_int(analysis.get("execution_phase")),
                parallel_group=analysis.get("parallel_group"),
                selected_by_dispatcher=selected,
            )
        )

    ticket_set = set(ticket_ids)
    edges: list[BatchGraphEdge] = []
    seen: set[tuple[str, str, str]] = set()
    for ticket_id in ticket_ids:
        analysis = analyses.get(ticket_id) or {}
        for dep in analysis.get("depends_on") or []:
            if dep not in ticket_set:
                continue
            key = (dep, ticket_id, "depends_on")
            if key in seen:
                continue
            seen.add(key)
            edges.append(BatchGraphEdge(from_id=dep, to_id=ticket_id, type="depends_on"))
        for other in _dep_conflicts.conflict_partners(
            ticket_id, analysis, ticket_set=ticket_set,
        ):
            key = tuple(sorted([ticket_id, other])) + ("conflicts_with",)
            if key in seen:
                continue
            seen.add(key)
            edges.append(
                BatchGraphEdge(
                    from_id=ticket_id, to_id=other, type="conflicts_with"
                )
            )
    return BatchGraphResponse(nodes=nodes, edges=edges)


def _build_phases(
    db_path,
    *,
    batch_id: str,
    ticket_ids: list[str],
) -> BatchPhasesResponse:
    analyses = _dependency_analysis_for_batch(db_path, batch_id, ticket_ids)
    buckets: dict[int | None, list[str]] = {}
    for ticket_id in ticket_ids:
        phase = _phase_to_int(analyses.get(ticket_id, {}).get("execution_phase"))
        buckets.setdefault(phase, []).append(ticket_id)
    ordered: list[BatchPhase] = []
    numeric = sorted(p for p in buckets if p is not None)
    for phase in numeric:
        ordered.append(BatchPhase(phase=phase, tickets=sorted(buckets[phase])))
    if None in buckets:
        ordered.append(BatchPhase(phase=None, tickets=sorted(buckets[None])))
    return BatchPhasesResponse(phases=ordered)


def _build_insights(
    db_path,
    *,
    batch_id: str,
    ticket_ids: list[str],
    dispatcher_payload: dict | None,
) -> BatchInsightsResponse:
    analyses = _dependency_analysis_for_batch(db_path, batch_id, ticket_ids)
    ticket_set = set(ticket_ids)

    runnable: list[str] = []
    if dispatcher_payload:
        for rec in dispatcher_payload.get("recommendations") or []:
            tid = rec.get("ticket_id")
            if tid and tid in ticket_set:
                runnable.append(tid)
    runnable.sort()

    runtime_map = _ticket_runtime_map(db_path)
    conflict_blocked: dict[str, list[str]] = {}
    if dispatcher_payload:
        for entry in dispatcher_payload.get("blocked") or []:
            if entry.get("blocking_step") != "conflicts":
                continue
            ticket_id = entry.get("ticket_id")
            if not ticket_id:
                continue
            blockers = list(entry.get("blocked_by") or [])
            if not blockers and entry.get("reason"):
                # Fallback: keep insights usable if only ``reason`` is present.
                for token in str(entry["reason"]).split():
                    if token.startswith("T") and token[1:].isdigit():
                        blockers.append(token.rstrip(".,;"))
            if blockers:
                conflict_blocked[ticket_id] = sorted(set(blockers))

    blocked: list[BatchBlockedTicket] = []
    for ticket_id in ticket_ids:
        deps = list(analyses.get(ticket_id, {}).get("depends_on") or [])
        runtime_state = (
            runtime_map.get(ticket_id, {}).get("state") or ""
        ).upper()
        if runtime_state in _DONE_STATES:
            continue
        if ticket_id in runnable:
            continue
        if ticket_id in conflict_blocked:
            blocked.append(
                BatchBlockedTicket(
                    ticket_id=ticket_id,
                    blocked_by=conflict_blocked[ticket_id],
                )
            )
            continue
        if not deps:
            continue
        blocked.append(BatchBlockedTicket(ticket_id=ticket_id, blocked_by=sorted(set(deps))))

    conflicts: list[BatchConflict] = []
    for ticket_id in ticket_ids:
        others = _dep_conflicts.conflict_partners(
            ticket_id, analyses.get(ticket_id), ticket_set=ticket_set,
        )
        if others:
            conflicts.append(
                BatchConflict(ticket_id=ticket_id, conflicts_with=others)
            )

    return BatchInsightsResponse(
        runnable=runnable, blocked=blocked, conflicts=conflicts
    )


# ── runtime gate ─────────────────────────────────────────────────────────────

def _require_db(db_path):
    if db_path is None:
        raise HTTPException(status_code=503, detail="database not available")
    return db_path


def _require_batch(db_path, batch_id: str) -> dict:
    row = _safe(runtime_db.get_backlog_batch, db_path, batch_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"batch {batch_id!r} not found")
    return row


def _emit_operator_event(
    db_path,
    batch_id: str,
    action: str,
    *,
    message: str | None = None,
    metadata: dict | None = None,
) -> None:
    meta = {"batch_id": batch_id, "action": action}
    if metadata:
        meta.update(metadata)
    try:
        runtime_db.append_runtime_event(
            db_path,
            None,
            "batch.operator_action",
            message or f"operator action {action} on batch {batch_id}",
            metadata=meta,
        )
    except Exception:
        logger.exception("batches: failed to emit operator event")


# ── shared payload builders (global + project-scoped share these) ────────────

def _list_payload(db_path) -> BatchListResponse:
    return BatchListResponse(batches=_build_summaries(db_path))


def _current_payload(db_path) -> BatchCurrentResponse:
    rows = _safe(runtime_db.list_backlog_batches, db_path) or []
    if not rows:
        return BatchCurrentResponse(current=None, next=None)
    current_row = next(
        (r for r in rows if (r.get("status") or "") == "dispatching"), None
    )
    next_row = next(
        (
            r
            for r in rows
            if (r.get("status") or "") not in {"completed", "dispatching"}
        ),
        None,
    )
    return BatchCurrentResponse(
        current=_build_summary(db_path, current_row) if current_row else None,
        next=_build_summary(db_path, next_row) if next_row else None,
    )


def _detail_payload(
    db_path,
    project_root: Path,
    *,
    batch_id: str,
    project_id: str | None,
    worktrees_dir: Path | None,
) -> BatchDetailResponse:
    row = _require_batch(db_path, batch_id)
    ticket_ids = _safe(runtime_db.list_backlog_batch_ticket_ids, db_path, batch_id) or []
    dispatcher_payload = _dispatcher_payload(
        db_path, project_root,
        project_id=project_id, worktrees_dir=worktrees_dir,
    )
    tickets = _build_ticket_details(
        db_path,
        project_root,
        batch_id=batch_id,
        ticket_ids=ticket_ids,
        worktrees_dir=worktrees_dir,
        dispatcher_payload=dispatcher_payload,
    )
    analysis_summary, raw_analyzer_output = _build_analysis_summary(db_path, batch_id)
    return BatchDetailResponse(
        batch=_build_summary(db_path, row),
        tickets=tickets,
        analysis_summary=analysis_summary,
        raw_analyzer_output=raw_analyzer_output,
    )


def _graph_payload(
    db_path,
    project_root: Path,
    *,
    batch_id: str,
    project_id: str | None,
    worktrees_dir: Path | None,
) -> BatchGraphResponse:
    _require_batch(db_path, batch_id)
    ticket_ids = _safe(runtime_db.list_backlog_batch_ticket_ids, db_path, batch_id) or []
    dispatcher_payload = _dispatcher_payload(
        db_path, project_root,
        project_id=project_id, worktrees_dir=worktrees_dir,
    )
    return _build_graph(
        db_path,
        batch_id=batch_id,
        ticket_ids=ticket_ids,
        dispatcher_payload=dispatcher_payload,
    )


def _phases_payload(db_path, batch_id: str) -> BatchPhasesResponse:
    _require_batch(db_path, batch_id)
    ticket_ids = _safe(runtime_db.list_backlog_batch_ticket_ids, db_path, batch_id) or []
    return _build_phases(db_path, batch_id=batch_id, ticket_ids=ticket_ids)


def _insights_payload(
    db_path,
    project_root: Path,
    *,
    batch_id: str,
    project_id: str | None,
    worktrees_dir: Path | None,
) -> BatchInsightsResponse:
    _require_batch(db_path, batch_id)
    ticket_ids = _safe(runtime_db.list_backlog_batch_ticket_ids, db_path, batch_id) or []
    dispatcher_payload = _dispatcher_payload(
        db_path, project_root,
        project_id=project_id, worktrees_dir=worktrees_dir,
    )
    return _build_insights(
        db_path,
        batch_id=batch_id,
        ticket_ids=ticket_ids,
        dispatcher_payload=dispatcher_payload,
    )


# ── action helpers ───────────────────────────────────────────────────────────

def _action_freeze(db_path, batch_id: str) -> BatchActionResponse:
    row = _require_batch(db_path, batch_id)
    status = (row.get("status") or "")
    if status != _backlog_batch.BatchStatus.COLLECTING.value:
        raise HTTPException(
            status_code=409,
            detail=f"batch {batch_id} cannot be frozen from status={status}",
        )
    try:
        _backlog_batch.transition_batch(
            db_path,
            batch_id,
            from_status=_backlog_batch.BatchStatus.COLLECTING.value,
            to_status=_backlog_batch.BatchStatus.FROZEN.value,
            reason="operator_force_freeze",
            extra_fields={"frozen_at": _now_iso_safe()},
        )
    except _backlog_batch.BatchTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    _emit_operator_event(
        db_path, batch_id, "freeze",
        message=f"operator forced freeze on batch {batch_id}",
    )
    return BatchActionResponse(
        batch_id=batch_id, action="freeze",
        status=_backlog_batch.BatchStatus.FROZEN.value,
        message="batch frozen",
    )


def _action_retry_dependency_analysis(db_path, batch_id: str) -> BatchActionResponse:
    row = _require_batch(db_path, batch_id)
    status = (row.get("status") or "")
    if status != _backlog_batch.BatchStatus.DEPENDENCY_ANALYSIS_FAILED.value:
        raise HTTPException(
            status_code=409,
            detail=(
                f"batch {batch_id} cannot retry dependency analysis from status={status}"
            ),
        )
    try:
        _backlog_batch.mark_dependency_analysis_attempt_started(db_path, batch_id)
    except _backlog_batch.BatchTransitionError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    _emit_operator_event(
        db_path, batch_id, "retry_dependency_analysis",
        message=f"operator retried dependency analysis on batch {batch_id}",
    )
    return BatchActionResponse(
        batch_id=batch_id, action="retry_dependency_analysis",
        status=_backlog_batch.BatchStatus.DEPENDENCY_ANALYSIS_RUNNING.value,
        message="dependency analysis retried",
    )


def _action_recompute_dependencies(db_path, batch_id: str) -> BatchActionResponse:
    row = _require_batch(db_path, batch_id)
    status = (row.get("status") or "")
    if status in {
        _backlog_batch.BatchStatus.COMPLETED.value,
        _backlog_batch.BatchStatus.DISPATCHING.value,
    }:
        raise HTTPException(
            status_code=409,
            detail=(
                f"batch {batch_id} cannot recompute dependencies from status={status}"
            ),
        )
    runtime_db.update_backlog_batch(
        db_path,
        batch_id,
        status=_backlog_batch.BatchStatus.FROZEN.value,
        dependency_analysis_attempts=0,
        last_dependency_analysis_error=None,
        next_dependency_analysis_retry_at=None,
    )
    _emit_operator_event(
        db_path, batch_id, "recompute_dependencies",
        message=(
            f"operator requested dependency recompute on batch {batch_id} "
            f"(reset to frozen)"
        ),
        metadata={"previous_status": status},
    )
    return BatchActionResponse(
        batch_id=batch_id, action="recompute_dependencies",
        status=_backlog_batch.BatchStatus.FROZEN.value,
        message="batch reset to frozen for dependency recompute",
    )


def _action_cancel(db_path, batch_id: str) -> BatchActionResponse:
    row = _require_batch(db_path, batch_id)
    status = (row.get("status") or "")
    if status == _backlog_batch.BatchStatus.DISPATCHING.value:
        raise HTTPException(
            status_code=409,
            detail=f"batch {batch_id} cannot be cancelled while dispatching",
        )
    if status == _backlog_batch.BatchStatus.COMPLETED.value:
        raise HTTPException(
            status_code=409,
            detail=f"batch {batch_id} is already completed",
        )
    runtime_db.update_backlog_batch(
        db_path,
        batch_id,
        status=_backlog_batch.BatchStatus.COMPLETED.value,
        completed_at=_now_iso_safe(),
    )
    _emit_operator_event(
        db_path, batch_id, "cancel",
        message=f"operator cancelled batch {batch_id} (previous status={status})",
        metadata={"previous_status": status, "cancelled_by_operator": True},
    )
    return BatchActionResponse(
        batch_id=batch_id, action="cancel",
        status=_backlog_batch.BatchStatus.COMPLETED.value,
        message="batch cancelled",
    )


def _now_iso_safe() -> str:
    import datetime
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ── global routes (no project_id) ────────────────────────────────────────────

@router.get("", response_model=BatchListResponse)
def list_batches(request: Request) -> BatchListResponse:
    db_path = _require_db(_db_path(request))
    return _list_payload(db_path)


@router.get("/current", response_model=BatchCurrentResponse)
def current_batch(request: Request) -> BatchCurrentResponse:
    db_path = _require_db(_db_path(request))
    return _current_payload(db_path)


@router.get("/{batch_id}", response_model=BatchDetailResponse)
def get_batch(batch_id: str, request: Request) -> BatchDetailResponse:
    db_path = _require_db(_db_path(request))
    return _detail_payload(
        db_path,
        _root(request),
        batch_id=batch_id,
        project_id=None,
        worktrees_dir=getattr(request.app.state, "worktrees_dir", None),
    )


@router.get(
    "/{batch_id}/graph",
    response_model=BatchGraphResponse,
    response_model_by_alias=True,
)
def get_batch_graph(batch_id: str, request: Request) -> BatchGraphResponse:
    db_path = _require_db(_db_path(request))
    return _graph_payload(
        db_path,
        _root(request),
        batch_id=batch_id,
        project_id=None,
        worktrees_dir=getattr(request.app.state, "worktrees_dir", None),
    )


@router.get("/{batch_id}/phases", response_model=BatchPhasesResponse)
def get_batch_phases(batch_id: str, request: Request) -> BatchPhasesResponse:
    db_path = _require_db(_db_path(request))
    return _phases_payload(db_path, batch_id)


@router.get("/{batch_id}/insights", response_model=BatchInsightsResponse)
def get_batch_insights(batch_id: str, request: Request) -> BatchInsightsResponse:
    db_path = _require_db(_db_path(request))
    return _insights_payload(
        db_path,
        _root(request),
        batch_id=batch_id,
        project_id=None,
        worktrees_dir=getattr(request.app.state, "worktrees_dir", None),
    )


@router.post("/{batch_id}/freeze", response_model=BatchActionResponse)
def post_freeze(batch_id: str, request: Request) -> BatchActionResponse:
    db_path = _require_db(_db_path(request))
    return _action_freeze(db_path, batch_id)


@router.post(
    "/{batch_id}/retry-dependency-analysis", response_model=BatchActionResponse
)
def post_retry_dependency_analysis(
    batch_id: str, request: Request
) -> BatchActionResponse:
    db_path = _require_db(_db_path(request))
    return _action_retry_dependency_analysis(db_path, batch_id)


@router.post(
    "/{batch_id}/recompute-dependencies", response_model=BatchActionResponse
)
def post_recompute_dependencies(
    batch_id: str, request: Request
) -> BatchActionResponse:
    db_path = _require_db(_db_path(request))
    return _action_recompute_dependencies(db_path, batch_id)


@router.post("/{batch_id}/cancel", response_model=BatchActionResponse)
def post_cancel(batch_id: str, request: Request) -> BatchActionResponse:
    db_path = _require_db(_db_path(request))
    return _action_cancel(db_path, batch_id)


# ── project-scoped routes ────────────────────────────────────────────────────

@project_router.get(
    "/{project_id}/dispatcher/batches", response_model=BatchListResponse
)
def list_batches_project(
    project_id: str,
    request: Request,
    project_root: Path = Depends(resolve_project),
    project_runtime_root: Path | None = Depends(resolve_project_runtime_root),
) -> BatchListResponse:
    db_path = _require_db(_resolve_db_for_project(request, project_id))
    return _list_payload(db_path)


@project_router.get(
    "/{project_id}/dispatcher/batches/current",
    response_model=BatchCurrentResponse,
)
def current_batch_project(
    project_id: str,
    request: Request,
    project_root: Path = Depends(resolve_project),
    project_runtime_root: Path | None = Depends(resolve_project_runtime_root),
) -> BatchCurrentResponse:
    db_path = _require_db(_resolve_db_for_project(request, project_id))
    return _current_payload(db_path)


@project_router.get(
    "/{project_id}/dispatcher/batches/{batch_id}",
    response_model=BatchDetailResponse,
)
def get_batch_project(
    project_id: str,
    batch_id: str,
    request: Request,
    project_root: Path = Depends(resolve_project),
    project_runtime_root: Path | None = Depends(resolve_project_runtime_root),
) -> BatchDetailResponse:
    db_path = _require_db(_resolve_db_for_project(request, project_id))
    worktrees = _worktrees_dir_for(
        request,
        project_root,
        project_id=project_id,
        project_runtime_root=project_runtime_root,
    )
    return _detail_payload(
        db_path,
        project_root,
        batch_id=batch_id,
        project_id=project_id,
        worktrees_dir=worktrees,
    )


@project_router.get(
    "/{project_id}/dispatcher/batches/{batch_id}/graph",
    response_model=BatchGraphResponse,
    response_model_by_alias=True,
)
def get_batch_graph_project(
    project_id: str,
    batch_id: str,
    request: Request,
    project_root: Path = Depends(resolve_project),
    project_runtime_root: Path | None = Depends(resolve_project_runtime_root),
) -> BatchGraphResponse:
    db_path = _require_db(_resolve_db_for_project(request, project_id))
    worktrees = _worktrees_dir_for(
        request,
        project_root,
        project_id=project_id,
        project_runtime_root=project_runtime_root,
    )
    return _graph_payload(
        db_path,
        project_root,
        batch_id=batch_id,
        project_id=project_id,
        worktrees_dir=worktrees,
    )


@project_router.get(
    "/{project_id}/dispatcher/batches/{batch_id}/phases",
    response_model=BatchPhasesResponse,
)
def get_batch_phases_project(
    project_id: str,
    batch_id: str,
    request: Request,
    project_root: Path = Depends(resolve_project),
    project_runtime_root: Path | None = Depends(resolve_project_runtime_root),
) -> BatchPhasesResponse:
    db_path = _require_db(_resolve_db_for_project(request, project_id))
    return _phases_payload(db_path, batch_id)


@project_router.get(
    "/{project_id}/dispatcher/batches/{batch_id}/insights",
    response_model=BatchInsightsResponse,
)
def get_batch_insights_project(
    project_id: str,
    batch_id: str,
    request: Request,
    project_root: Path = Depends(resolve_project),
    project_runtime_root: Path | None = Depends(resolve_project_runtime_root),
) -> BatchInsightsResponse:
    db_path = _require_db(_resolve_db_for_project(request, project_id))
    worktrees = _worktrees_dir_for(
        request,
        project_root,
        project_id=project_id,
        project_runtime_root=project_runtime_root,
    )
    return _insights_payload(
        db_path,
        project_root,
        batch_id=batch_id,
        project_id=project_id,
        worktrees_dir=worktrees,
    )


@project_router.post(
    "/{project_id}/dispatcher/batches/{batch_id}/freeze",
    response_model=BatchActionResponse,
)
def post_freeze_project(
    project_id: str,
    batch_id: str,
    request: Request,
    project_root: Path = Depends(resolve_project),
) -> BatchActionResponse:
    db_path = _require_db(_resolve_db_for_project(request, project_id))
    return _action_freeze(db_path, batch_id)


@project_router.post(
    "/{project_id}/dispatcher/batches/{batch_id}/retry-dependency-analysis",
    response_model=BatchActionResponse,
)
def post_retry_dependency_analysis_project(
    project_id: str,
    batch_id: str,
    request: Request,
    project_root: Path = Depends(resolve_project),
) -> BatchActionResponse:
    db_path = _require_db(_resolve_db_for_project(request, project_id))
    return _action_retry_dependency_analysis(db_path, batch_id)


@project_router.post(
    "/{project_id}/dispatcher/batches/{batch_id}/recompute-dependencies",
    response_model=BatchActionResponse,
)
def post_recompute_dependencies_project(
    project_id: str,
    batch_id: str,
    request: Request,
    project_root: Path = Depends(resolve_project),
) -> BatchActionResponse:
    db_path = _require_db(_resolve_db_for_project(request, project_id))
    return _action_recompute_dependencies(db_path, batch_id)


@project_router.post(
    "/{project_id}/dispatcher/batches/{batch_id}/cancel",
    response_model=BatchActionResponse,
)
def post_cancel_project(
    project_id: str,
    batch_id: str,
    request: Request,
    project_root: Path = Depends(resolve_project),
) -> BatchActionResponse:
    db_path = _require_db(_resolve_db_for_project(request, project_id))
    return _action_cancel(db_path, batch_id)
