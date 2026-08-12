"""Ticket Dispatcher Service (T212).

Read-only advisory service that recommends the next ticket(s) to execute.

It combines the existing — and intentionally untouched — execution-eligibility
aggregator with the Intelligence queue rank / difficulty signals to rank
``READY_TO_TAKE`` tickets. The dispatcher never starts a ticket, never writes
to the runtime DB, never mutates ``state.json``, and never calls the daemon /
runner / scheduler. It only reads and computes.

Modes
-----

``off``       Default — short-circuits to an empty payload. No eligibility
              evaluation is performed.
``advisory``  Compute ranked recommendations and a blocked list.
``manual``    Same recommendations as ``advisory``; launching a ticket
              remains a human action via the existing run-ticket UI/API.
``auto``      Reserved for future work. The dispatcher refuses to act on it
              and returns ``not_implemented=True`` alongside an empty list.

Configured via ``AI_DEV_FACTORY_DISPATCHER_MODE``.
"""

from __future__ import annotations

import datetime
import os
import sys
from pathlib import Path

_TOOLS_DIR = Path(__file__).resolve().parent
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

import runtime_db  # noqa: E402
import runtime_settings as _runtime_settings  # noqa: E402
import ticket_execution_eligibility as _eligibility  # noqa: E402
from dependency_conflicts import build_conflict_map  # noqa: E402
from ticket_readiness_evaluator import read_ticket_markdown  # noqa: E402

try:
    import backlog_batch as _backlog_batch  # noqa: E402
except ImportError:
    _backlog_batch = None  # type: ignore[assignment]


DISPATCHER_MODES: tuple[str, ...] = ("off", "advisory", "manual", "auto")
DEFAULT_DISPATCHER_MODE = "off"

# Ticket states that are not candidates for being "the next ticket to run".
# Mirrors the kanban exclusions used by ``board_service`` for the "running" /
# "pr_ready" / "done" lanes — we never recommend something that is already
# active, archived, or beyond the runner's reach.
_EXCLUDED_RUNTIME_STATES: frozenset[str] = frozenset({
    "PLANNING",
    "CODING",
    "CANCELLED",
    "TEST_COMPLETE",
})

# Active tickets in the same batch block conflicting recommendations.
_ACTIVE_CONFLICT_STATES: frozenset[str] = frozenset({
    "PLANNING",
    "CODING",
    "REVIEWING",
    "RUNNING",
})

# Schema-hotspot mutex: at most one migrations writer may be mid-implementation
# (or mid-conflict) at a time. Planning-only states do not hold the lock.
_SCHEMA_HOTSPOT_HOLDER_STATES: frozenset[str] = frozenset({
    "PLAN_APPROVED",
    "CODING",
    "IMPLEMENTATION_REVIEW_NEEDED",
    "IMPLEMENTATION_FIX_REQUIRED",
    "IMPLEMENTATION_APPROVED",
    "CONFLICT_RESOLUTION_NEEDED",
    "CONFLICT_RESOLVING",
    "CONFLICT_RESOLVED_REVIEW_NEEDED",
    "CONFLICT_RESOLUTION_FAILED",
})

# Batch wave gate: a phase is complete when every ticket in that phase reaches
# one of these terminal runtime states (mirrors ``batches._DONE_STATES``).
_PHASE_DONE_STATES: frozenset[str] = frozenset({
    "DONE",
    "MERGED",
    "ARCHIVED",
    "TEST_COMPLETE",
})

_UNKNOWN_EXECUTION_PHASE = 10_000

_ENV_VAR = "AI_DEV_FACTORY_DISPATCHER_MODE"


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )


def get_dispatcher_mode(db_path=None) -> str:
    """Resolve the dispatcher mode through the settings registry.

    When ``db_path`` is provided the registry is consulted first, so a DB
    override of ``DISPATCHER_ENABLED`` takes effect immediately. Without a
    handle (or on any failure) we fall back to the legacy env-var read so
    existing callers keep working.

    Returns one of ``DISPATCHER_MODES``. Unknown values silently fall back to
    ``"off"`` so a misconfigured deployment cannot accidentally enable the
    dispatcher.
    """
    raw: str | None = None
    if db_path is not None:
        try:
            raw = _runtime_settings.get_setting(db_path, "DISPATCHER_ENABLED")
        except Exception:
            raw = None
    if raw is None:
        raw = os.environ.get(_ENV_VAR)
    candidate = (raw or "").strip().lower()
    if candidate in DISPATCHER_MODES:
        return candidate
    return DEFAULT_DISPATCHER_MODE


def is_dispatcher_enabled(db_path=None) -> bool:
    """Return True when the resolved dispatcher mode is anything other than ``off``."""
    return get_dispatcher_mode(db_path) != "off"


def _resolve_mode(mode: str | None, db_path=None) -> str:
    if mode is None:
        return get_dispatcher_mode(db_path)
    candidate = mode.strip().lower()
    if candidate in DISPATCHER_MODES:
        return candidate
    return DEFAULT_DISPATCHER_MODE


def _safe_call(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except Exception:
        return None


def _read_ticket_content(
    project_root: Path,
    ticket_id: str,
    *,
    worktrees_dir: Path | None = None,
    project_id: str | None = None,
) -> str:
    return read_ticket_markdown(
        project_root,
        ticket_id,
        worktrees_dir=worktrees_dir,
        project_id=project_id,
    )


def _parse_iso(value: str | None) -> datetime.datetime | None:
    if not value:
        return None
    text = value.strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.datetime.fromisoformat(text)
    except ValueError:
        return None


def _age_bonus(updated_at: str | None, now: datetime.datetime) -> int:
    """Older eligible tickets get a small uplift, capped at +10."""
    parsed = _parse_iso(updated_at)
    if parsed is None:
        return 0
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=datetime.timezone.utc)
    days = max(0.0, (now - parsed).total_seconds() / 86400.0)
    return min(10, int(days))


def _queue_rank_bonus(queue_rank: int | None) -> int:
    if queue_rank is None:
        return 0
    return max(0, 30 - int(queue_rank))


def _difficulty_bonus(label: str | None) -> int:
    if not label:
        return 0
    norm = label.strip().lower()
    if norm in {"trivial", "simple"}:
        return 5
    if norm == "moderate":
        return 2
    return 0


def _score(
    *,
    ready_to_take: bool,
    queue_rank: int | None,
    difficulty_label: str | None,
    updated_at: str | None,
    now: datetime.datetime,
) -> int:
    if not ready_to_take:
        return 0
    score = 50
    score += _queue_rank_bonus(queue_rank)
    score += _difficulty_bonus(difficulty_label)
    score += _age_bonus(updated_at, now)
    return max(0, min(100, score))


def _format_reason(
    *,
    ready_to_take: bool,
    queue_rank: int | None,
    difficulty_label: str | None,
) -> str:
    if not ready_to_take:
        return "Not READY_TO_TAKE"
    parts = ["READY_TO_TAKE"]
    if difficulty_label:
        parts.append(f"difficulty={difficulty_label}")
    if queue_rank is not None:
        parts.append(f"queue_rank={queue_rank}")
    parts.append("no blockers")
    return ", ".join(parts)


def _candidate_row(row: dict) -> bool:
    state = (row.get("state") or "").strip()
    if state in _EXCLUDED_RUNTIME_STATES:
        return False
    if bool(row.get("daemon_archived")):
        return False
    return True


def _ticket_passes_batch_gate(db_path, ticket_id: str) -> bool:
    """Return True when ``ticket_id`` is eligible from the batch state machine.

    Two acceptable cases:
      - the ticket is not part of any backlog batch (legacy / non-batch
        ingestion path) → eligibility falls back to the existing rules;
      - the ticket belongs to a batch whose status is ``dispatching``.

    Tickets in a batch that is still ``collecting``, ``frozen``,
    ``dependency_analysis_running``, ``dependency_analysis_failed``, or
    ``readiness_running`` are excluded from dispatcher recommendations until
    the batch transitions to ``dispatching``.
    """
    if _backlog_batch is None:
        return True
    try:
        batch_status = _backlog_batch.get_ticket_batch_status(db_path, ticket_id)
    except Exception:
        return True
    if batch_status is None:
        return True
    return batch_status == _backlog_batch.BatchStatus.DISPATCHING.value


def _sort_key(rec: dict) -> tuple:
    """Stable ordering: higher score first, then lower queue_rank, then older
    updated_at (ascending ISO string), then ticket_id."""
    queue_rank = rec.get("_queue_rank")
    queue_rank_key = queue_rank if queue_rank is not None else 10_000
    updated_at = rec.get("_updated_at") or "9999"
    return (-int(rec["score"]), queue_rank_key, updated_at, rec["ticket_id"])


def _phase_to_int(phase: str | int | None) -> int:
    """Coerce ``execution_phase`` to an int for ordering; unknown → large."""
    if phase is None:
        return _UNKNOWN_EXECUTION_PHASE
    text = str(phase).strip()
    if not text:
        return _UNKNOWN_EXECUTION_PHASE
    try:
        return int(text)
    except (TypeError, ValueError):
        return _UNKNOWN_EXECUTION_PHASE


def _ticket_wave_done(runtime_row: dict | None) -> bool:
    """True when a batch ticket no longer blocks its execution phase."""
    if not runtime_row:
        return False
    if bool(runtime_row.get("daemon_archived")):
        return True
    state = (runtime_row.get("state") or "").strip().upper()
    return state in _PHASE_DONE_STATES


def _active_wave_phase(
    members: set[str],
    runtime_map: dict[str, dict],
    analyses: dict[str, dict],
) -> int | None:
    """Return the lowest ``execution_phase`` that still has unfinished tickets.

    Tickets without a persisted ``execution_phase`` are ignored for wave
    computation so legacy / partially analysed batches keep working.
    """
    by_phase: dict[int, list[str]] = {}
    for ticket_id in members:
        analysis = analyses.get(ticket_id, {})
        phase = _phase_to_int(analysis.get("execution_phase"))
        if phase >= _UNKNOWN_EXECUTION_PHASE:
            continue
        by_phase.setdefault(phase, []).append(ticket_id)
    if not by_phase:
        return None
    for phase in sorted(by_phase):
        if not all(
            _ticket_wave_done(runtime_map.get(ticket_id))
            for ticket_id in by_phase[phase]
        ):
            return phase
    return None


def _apply_phase_wave_filter(
    db_path,
    recommendations: list[dict],
    blocked: list[dict],
    runtime_rows: list[dict],
) -> tuple[list[dict], list[dict]]:
    """Keep only recommendations in the batch's current execution wave.

    The batch dependency analyser assigns ``execution_phase`` so tickets in
    the same phase can run in parallel while later phases stay sequential.
    This filter enforces that model: no ticket from phase *N+1* is recommended
    while phase *N* still has unfinished members, even when its ``depends_on``
    prerequisites are already merged.
    """
    if not recommendations:
        return recommendations, blocked

    runtime_map: dict[str, dict] = {}
    for row in runtime_rows:
        ticket_id = (row.get("ticket_id") or "").strip()
        if ticket_id:
            runtime_map[ticket_id] = row

    rec_by_id = {rec["ticket_id"]: rec for rec in recommendations}
    batch_ids: dict[str, str] = {}
    analyses: dict[str, dict] = {}
    batch_members_cache: dict[str, set[str]] = {}
    batch_analyses_cache: dict[str, dict[str, dict]] = {}

    for ticket_id in rec_by_id:
        batch_id, analysis = _load_ticket_batch_analysis(db_path, ticket_id)
        if batch_id:
            batch_ids[ticket_id] = batch_id
            analyses[ticket_id] = analysis

    def _batch_members(batch_id: str) -> set[str]:
        if batch_id not in batch_members_cache:
            members = _safe_call(
                runtime_db.list_backlog_batch_ticket_ids, db_path, batch_id,
            ) or []
            batch_members_cache[batch_id] = set(members)
        return batch_members_cache[batch_id]

    def _analyses_for_batch(batch_id: str) -> dict[str, dict]:
        if batch_id not in batch_analyses_cache:
            batch_analyses: dict[str, dict] = {}
            for member in _batch_members(batch_id):
                if member in analyses:
                    batch_analyses[member] = analyses[member]
                else:
                    batch_analyses[member] = (
                        _safe_call(
                            runtime_db.get_dependency_analysis,
                            db_path,
                            member,
                            batch_id,
                        )
                        or {}
                    )
            batch_analyses_cache[batch_id] = batch_analyses
        return batch_analyses_cache[batch_id]

    active_wave_by_batch: dict[str, int | None] = {}

    def _active_wave(batch_id: str) -> int | None:
        if batch_id not in active_wave_by_batch:
            active_wave_by_batch[batch_id] = _active_wave_phase(
                _batch_members(batch_id),
                runtime_map,
                _analyses_for_batch(batch_id),
            )
        return active_wave_by_batch[batch_id]

    selected: set[str] = set()
    phase_blocked: dict[str, str] = {}

    for ticket_id, rec in rec_by_id.items():
        batch_id = batch_ids.get(ticket_id)
        if not batch_id:
            selected.add(ticket_id)
            continue

        active_wave = _active_wave(batch_id)
        if active_wave is None:
            selected.add(ticket_id)
            continue

        ticket_phase = _phase_to_int(
            analyses.get(ticket_id, {}).get("execution_phase"),
        )
        if ticket_phase >= _UNKNOWN_EXECUTION_PHASE:
            selected.add(ticket_id)
            continue

        if ticket_phase <= active_wave:
            selected.add(ticket_id)
            continue

        phase_blocked[ticket_id] = (
            f"blocked by batch execution phase {active_wave} "
            f"(ticket is phase {ticket_phase})"
        )

    filtered_recs = [rec for rec in recommendations if rec["ticket_id"] in selected]
    already_blocked = {entry["ticket_id"] for entry in blocked}

    for ticket_id, reason in sorted(phase_blocked.items()):
        if ticket_id in already_blocked:
            continue
        blocked.append({
            "ticket_id": ticket_id,
            "ready_to_take": False,
            "status": "PHASE_BLOCKED",
            "blocking_step": "phase",
            "reason": reason,
        })

    return filtered_recs, blocked


def _parallel_group_rank(parallel_group: str | None) -> int:
    """Lower rank wins tie-breaks among same-phase conflicting tickets."""
    if not parallel_group:
        return 2
    norm = parallel_group.strip().lower()
    if norm == "foundation":
        return 0
    if norm == "bootstrap":
        return 1
    return 1


def _conflict_priority_key(ticket_id: str, analysis: dict | None) -> tuple:
    analysis = analysis or {}
    return (
        _phase_to_int(analysis.get("execution_phase")),
        _parallel_group_rank(analysis.get("parallel_group")),
        ticket_id,
    )


def _load_ticket_batch_analysis(db_path, ticket_id: str) -> tuple[str | None, dict]:
    batch_id = _safe_call(runtime_db.get_batch_for_ticket, db_path, ticket_id)
    if not batch_id:
        return None, {}
    analysis = _safe_call(
        runtime_db.get_dependency_analysis, db_path, ticket_id, batch_id,
    ) or {}
    return batch_id, analysis


def _same_batch_conflicts(
    ticket_id: str,
    analysis: dict,
    *,
    batch_members: set[str],
    conflict_map: dict[str, set[str]] | None = None,
) -> list[str]:
    if conflict_map is not None:
        return sorted(
            other
            for other in conflict_map.get(ticket_id, set())
            if other in batch_members
        )
    from dependency_conflicts import conflict_partners

    return conflict_partners(ticket_id, analysis, ticket_set=batch_members)


def _conflict_block_reason(
    *,
    blocker_id: str,
    blocker_analysis: dict | None,
    blocked_analysis: dict | None,
    running: bool,
) -> str:
    if running:
        return f"blocked by conflicting ticket {blocker_id} (currently running)"
    blocker_phase = _phase_to_int((blocker_analysis or {}).get("execution_phase"))
    blocked_phase = _phase_to_int((blocked_analysis or {}).get("execution_phase"))
    if blocker_phase < blocked_phase:
        return f"blocked by conflict with earlier-phase ticket {blocker_id}"
    return f"blocked by conflicting ticket {blocker_id}"


def _apply_conflict_filter(
    db_path,
    recommendations: list[dict],
    blocked: list[dict],
    runtime_rows: list[dict],
) -> tuple[list[dict], list[dict]]:
    """Remove conflicting recommendations within the same batch.

    Consumes dependency-analysis rows (``conflicting_tickets``,
    ``execution_phase``, ``parallel_group``) read-only. Never mutates analysis
    data. Tickets outside a batch, or with no recorded conflicts, pass through.
    """
    if not recommendations:
        return recommendations, blocked

    runtime_map: dict[str, str] = {}
    for row in runtime_rows:
        ticket_id = (row.get("ticket_id") or "").strip()
        if ticket_id:
            runtime_map[ticket_id] = (row.get("state") or "").strip().upper()

    rec_by_id = {rec["ticket_id"]: rec for rec in recommendations}
    analyses: dict[str, dict] = {}
    batch_ids: dict[str, str] = {}
    batch_members_cache: dict[str, set[str]] = {}
    batch_conflict_maps: dict[str, dict[str, set[str]]] = {}

    for ticket_id in rec_by_id:
        batch_id, analysis = _load_ticket_batch_analysis(db_path, ticket_id)
        if batch_id:
            batch_ids[ticket_id] = batch_id
            analyses[ticket_id] = analysis

    def _batch_members(batch_id: str) -> set[str]:
        if batch_id not in batch_members_cache:
            members = _safe_call(
                runtime_db.list_backlog_batch_ticket_ids, db_path, batch_id,
            ) or []
            batch_members_cache[batch_id] = set(members)
        return batch_members_cache[batch_id]

    def _conflict_map_for_batch(batch_id: str) -> dict[str, set[str]]:
        if batch_id not in batch_conflict_maps:
            members = sorted(_batch_members(batch_id))
            batch_analyses: dict[str, dict] = {}
            for member in members:
                if member in analyses:
                    batch_analyses[member] = analyses[member]
                else:
                    row = _safe_call(
                        runtime_db.get_dependency_analysis,
                        db_path,
                        member,
                        batch_id,
                    ) or {}
                    batch_analyses[member] = row
            batch_conflict_maps[batch_id] = build_conflict_map(
                members, batch_analyses,
            )
        return batch_conflict_maps[batch_id]

    running_by_batch: dict[str, set[str]] = {}

    def _running_in_batch(batch_id: str) -> set[str]:
        if batch_id not in running_by_batch:
            active = {
                member
                for member in _batch_members(batch_id)
                if runtime_map.get(member, "") in _ACTIVE_CONFLICT_STATES
            }
            running_by_batch[batch_id] = active
        return running_by_batch[batch_id]

    candidate_ids = sorted(
        rec_by_id,
        key=lambda tid: _conflict_priority_key(tid, analyses.get(tid)),
    )

    selected: set[str] = set()
    conflict_blocked: dict[str, tuple[str, str]] = {}

    for ticket_id in candidate_ids:
        batch_id = batch_ids.get(ticket_id)
        if not batch_id:
            selected.add(ticket_id)
            continue

        analysis = analyses.get(ticket_id, {})
        members = _batch_members(batch_id)
        conflict_map = _conflict_map_for_batch(batch_id)
        conflicts = _same_batch_conflicts(
            ticket_id, analysis, batch_members=members, conflict_map=conflict_map,
        )

        running_conflict = next(
            (other for other in conflicts if other in _running_in_batch(batch_id)),
            None,
        )
        if running_conflict is not None:
            conflict_blocked[ticket_id] = (
                running_conflict,
                _conflict_block_reason(
                    blocker_id=running_conflict,
                    blocker_analysis=analyses.get(running_conflict),
                    blocked_analysis=analysis,
                    running=True,
                ),
            )
            continue

        selected_conflict = next(
            (other for other in conflicts if other in selected),
            None,
        )
        if selected_conflict is not None:
            conflict_blocked[ticket_id] = (
                selected_conflict,
                _conflict_block_reason(
                    blocker_id=selected_conflict,
                    blocker_analysis=analyses.get(selected_conflict),
                    blocked_analysis=analysis,
                    running=False,
                ),
            )
            continue

        selected.add(ticket_id)

    filtered_recs = [rec for rec in recommendations if rec["ticket_id"] in selected]
    already_blocked = {entry["ticket_id"] for entry in blocked}

    for ticket_id, (blocker_id, reason) in sorted(conflict_blocked.items()):
        if ticket_id in already_blocked:
            continue
        blocked.append({
            "ticket_id": ticket_id,
            "ready_to_take": False,
            "status": "CONFLICT_BLOCKED",
            "blocking_step": "conflicts",
            "reason": reason,
            "blocked_by": [blocker_id],
        })

    return filtered_recs, blocked


def _read_plan_markdown(
    project_root: Path,
    ticket_id: str,
    *,
    worktrees_dir: Path | None = None,
    worktree_path: str | None = None,
) -> str:
    candidates: list[Path] = []
    if worktree_path:
        candidates.append(Path(worktree_path) / "runs" / ticket_id / "plan.md")
    if worktrees_dir:
        candidates.append(Path(worktrees_dir) / ticket_id / "runs" / ticket_id / "plan.md")
    candidates.append(project_root / "runs" / ticket_id / "plan.md")
    for path in candidates:
        try:
            if path.is_file():
                return path.read_text(encoding="utf-8")
        except OSError:
            continue
    return ""


def _ticket_is_schema_hotspot(
    ticket_id: str,
    runtime_row: dict,
    *,
    project_root: Path,
    worktrees_dir: Path | None = None,
    ticket_content: str | None = None,
) -> bool:
    """Detect tickets that will (or already do) write DB migrations."""
    try:
        from migration_index_fix import (
            text_suggests_schema_hotspot,
            worktree_has_migration_changes,
        )
    except ImportError:
        return False

    content = ticket_content if ticket_content is not None else ""
    if not content:
        content = _read_ticket_content(
            project_root,
            ticket_id,
            worktrees_dir=worktrees_dir,
        )
    plan = _read_plan_markdown(
        project_root,
        ticket_id,
        worktrees_dir=worktrees_dir,
        worktree_path=runtime_row.get("worktree_path"),
    )
    if text_suggests_schema_hotspot(content) or text_suggests_schema_hotspot(plan):
        return True

    wt = (runtime_row.get("worktree_path") or "").strip()
    if wt and Path(wt).is_dir():
        try:
            if worktree_has_migration_changes(Path(wt)):
                return True
        except Exception:
            pass
    return False


def _apply_schema_hotspot_mutex_filter(
    db_path,
    recommendations: list[dict],
    blocked: list[dict],
    runtime_rows: list[dict],
    *,
    project_root: Path,
    worktrees_dir: Path | None = None,
    ticket_contents: dict[str, str] | None = None,
) -> tuple[list[dict], list[dict]]:
    """Allow at most one schema/migrations writer among recommendations.

    If another hotspot already holds an implementation/conflict state, all
    recommended hotspots are blocked. Otherwise keep the highest-ranked
    hotspot recommendation and block the rest.
    """
    if not recommendations:
        return recommendations, blocked

    ticket_contents = ticket_contents or {}
    runtime_map: dict[str, dict] = {}
    for row in runtime_rows:
        ticket_id = (row.get("ticket_id") or "").strip()
        if ticket_id:
            runtime_map[ticket_id] = row

    holders: list[str] = []
    for ticket_id, row in runtime_map.items():
        if bool(row.get("daemon_archived")):
            continue
        state = (row.get("state") or "").strip().upper()
        if state not in _SCHEMA_HOTSPOT_HOLDER_STATES:
            continue
        if _ticket_is_schema_hotspot(
            ticket_id,
            row,
            project_root=project_root,
            worktrees_dir=worktrees_dir,
            ticket_content=ticket_contents.get(ticket_id),
        ):
            holders.append(ticket_id)

    hotspot_recs: list[str] = []
    for rec in recommendations:
        ticket_id = rec["ticket_id"]
        row = runtime_map.get(ticket_id, {})
        if _ticket_is_schema_hotspot(
            ticket_id,
            row,
            project_root=project_root,
            worktrees_dir=worktrees_dir,
            ticket_content=ticket_contents.get(ticket_id),
        ):
            hotspot_recs.append(ticket_id)

    if not hotspot_recs and not holders:
        return recommendations, blocked

    mutex_blocked: dict[str, str] = {}
    keep: set[str] | None = None

    if holders:
        # Prefer the earliest holder id in the reason string for stability.
        holder_id = sorted(holders)[0]
        for ticket_id in hotspot_recs:
            if ticket_id in holders:
                # Already holding — may stay recommended if eligibility said so.
                continue
            mutex_blocked[ticket_id] = (
                f"schema_hotspot_mutex: waiting on {holder_id}"
            )
        # If a holder is somehow still in recommendations, keep only holders
        # among hotspots; drop other hotspots (already in mutex_blocked).
        keep = {tid for tid in hotspot_recs if tid in holders} or None
        if keep is None and hotspot_recs:
            # No holder among recs — block all hotspot recs.
            keep = set()
    else:
        # No active holder: keep the first recommended hotspot (already ranked).
        winner = hotspot_recs[0]
        keep = {winner}
        for ticket_id in hotspot_recs[1:]:
            mutex_blocked[ticket_id] = (
                f"schema_hotspot_mutex: waiting on {winner}"
            )

    if keep is not None:
        filtered_recs = [
            rec for rec in recommendations
            if rec["ticket_id"] not in hotspot_recs or rec["ticket_id"] in keep
        ]
    else:
        filtered_recs = [
            rec for rec in recommendations
            if rec["ticket_id"] not in mutex_blocked
        ]

    already_blocked = {entry["ticket_id"] for entry in blocked}
    for ticket_id, reason in sorted(mutex_blocked.items()):
        if ticket_id in already_blocked:
            continue
        blocked.append({
            "ticket_id": ticket_id,
            "ready_to_take": False,
            "status": "SCHEMA_HOTSPOT_BLOCKED",
            "blocking_step": "schema_hotspot_mutex",
            "reason": reason,
        })

    return filtered_recs, blocked


def get_recommended_tickets(
    db_path,
    project_root: Path,
    *,
    project_id: str | None = None,
    worktrees_dir: Path | None = None,
    mode: str | None = None,
    limit: int | None = None,
) -> dict:
    """Return the dispatcher recommendation payload.

    The function is a pure read: it never writes to the DB or touches the
    daemon/runner. When the resolved mode is ``"off"`` it returns immediately
    with an empty payload and does not call into the eligibility aggregator.
    """
    project_root = Path(project_root)
    resolved_mode = _resolve_mode(mode, db_path=db_path)
    evaluated_at = _now_iso()

    base_payload: dict = {
        "mode": resolved_mode,
        "project_id": project_id,
        "evaluated_at": evaluated_at,
        "recommendations": [],
        "blocked": [],
    }

    if resolved_mode == "off":
        return base_payload

    if resolved_mode == "auto":
        # Reserved for future work — dispatcher refuses to act.
        base_payload["not_implemented"] = True
        return base_payload

    rows = _safe_call(runtime_db.list_ticket_runtime, db_path) or []
    now = datetime.datetime.now(datetime.timezone.utc)

    recommendations: list[dict] = []
    blocked: list[dict] = []
    ticket_contents: dict[str, str] = {}

    for row in rows:
        ticket_id = (row.get("ticket_id") or "").strip()
        if not ticket_id:
            continue
        if not _candidate_row(row):
            continue
        if not _ticket_passes_batch_gate(db_path, ticket_id):
            continue

        ticket_content = _read_ticket_content(
            project_root,
            ticket_id,
            worktrees_dir=worktrees_dir,
            project_id=project_id,
        )
        ticket_contents[ticket_id] = ticket_content
        eligibility = _eligibility.evaluate_eligibility(
            db_path,
            project_root,
            ticket_id,
            ticket_content=ticket_content,
            project_id=project_id,
        )

        intelligence = _safe_call(
            runtime_db.get_ticket_intelligence, db_path, ticket_id
        ) or {}
        queue_rank = intelligence.get("queue_rank")
        difficulty_label = intelligence.get("difficulty_label")
        difficulty_score = intelligence.get("difficulty_score")
        updated_at = row.get("updated_at")

        ready = bool(eligibility.get("ready_to_take"))

        if ready:
            score = _score(
                ready_to_take=True,
                queue_rank=queue_rank,
                difficulty_label=difficulty_label,
                updated_at=updated_at,
                now=now,
            )
            recommendations.append({
                "ticket_id": ticket_id,
                "rank": 0,  # filled in after sorting
                "score": score,
                "ready_to_take": True,
                "intelligence": {
                    "difficulty_score": difficulty_score,
                    "difficulty_label": difficulty_label,
                    "queue_rank": queue_rank,
                },
                "reason": _format_reason(
                    ready_to_take=True,
                    queue_rank=queue_rank,
                    difficulty_label=difficulty_label,
                ),
                "_queue_rank": queue_rank,
                "_updated_at": updated_at,
            })
        else:
            blocked.append({
                "ticket_id": ticket_id,
                "ready_to_take": False,
                "status": eligibility.get("status"),
                "blocking_step": eligibility.get("blocking_step"),
                "reason": eligibility.get("reason"),
            })

    recommendations, blocked = _apply_phase_wave_filter(
        db_path, recommendations, blocked, rows,
    )
    recommendations, blocked = _apply_conflict_filter(
        db_path, recommendations, blocked, rows,
    )
    # Rank before mutex so the kept hotspot is the best-scoring one.
    recommendations.sort(key=_sort_key)
    recommendations, blocked = _apply_schema_hotspot_mutex_filter(
        db_path,
        recommendations,
        blocked,
        rows,
        project_root=project_root,
        worktrees_dir=worktrees_dir,
        ticket_contents=ticket_contents,
    )

    recommendations.sort(key=_sort_key)
    for index, rec in enumerate(recommendations, start=1):
        rec["rank"] = index
        rec.pop("_queue_rank", None)
        rec.pop("_updated_at", None)

    if limit is not None and limit >= 0:
        recommendations = recommendations[:limit]

    blocked.sort(key=lambda b: b["ticket_id"])

    base_payload["recommendations"] = recommendations
    base_payload["blocked"] = blocked
    return base_payload


__all__ = [
    "DISPATCHER_MODES",
    "DEFAULT_DISPATCHER_MODE",
    "get_dispatcher_mode",
    "get_recommended_tickets",
    "is_dispatcher_enabled",
]
