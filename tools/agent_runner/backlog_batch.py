"""Backlog batch lifecycle (T218).

Owns the state machine that groups newly discovered tickets into backlog
batches so that Global Dependency Analysis runs once per batch (instead of
per-ticket), before Readiness evaluation and Dispatcher scheduling.

Status lifecycle:

    collecting → frozen → dependency_analysis_running
                              ├── dependency_analysis_failed → (retry) → dependency_analysis_running
                              └── readiness_running → dispatching → completed

A batch in ``collecting`` with ``freeze_blocked=TRUE`` is intentionally held
open while a prior batch is still ``dispatching`` — this is how the plan
forbids cross-batch dependency-graph mutation during execution. No
``pending_collecting`` status is ever introduced.

This module is pure Python + the runtime DB. It never invokes the AI
subprocess directly — ``global_dependency_analyzer`` does that and reports
back via the lifecycle helpers here.
"""

from __future__ import annotations

import datetime
import sys
from enum import Enum
from pathlib import Path

_TOOLS_DIR = Path(__file__).resolve().parent
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

import runtime_db  # noqa: E402


class BatchStatus(str, Enum):
    """Closed enumeration of backlog batch statuses.

    The plan forbids ``pending_collecting``; do not add it. A blocked
    collecting batch is still ``collecting`` — the block is carried by the
    ``freeze_blocked`` column, not by a distinct status.
    """

    COLLECTING = "collecting"
    FROZEN = "frozen"
    DEPENDENCY_ANALYSIS_RUNNING = "dependency_analysis_running"
    DEPENDENCY_ANALYSIS_FAILED = "dependency_analysis_failed"
    READINESS_RUNNING = "readiness_running"
    DISPATCHING = "dispatching"
    COMPLETED = "completed"


_TERMINAL_STATUSES = frozenset({BatchStatus.COMPLETED.value})


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


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


def _next_batch_id(db_path) -> str:
    """Generate a monotonically increasing batch id of the form ``B0001``."""
    rows = runtime_db.list_backlog_batches(db_path)
    max_n = 0
    for row in rows:
        bid = (row.get("batch_id") or "").strip()
        if bid.startswith("B") and bid[1:].isdigit():
            try:
                max_n = max(max_n, int(bid[1:]))
            except ValueError:
                continue
    return f"B{max_n + 1:04d}"


def _emit_event(
    db_path,
    event_type: str,
    message: str,
    *,
    batch_id: str,
    metadata: dict | None = None,
) -> None:
    meta = dict(metadata or {})
    meta.setdefault("batch_id", batch_id)
    try:
        runtime_db.append_runtime_event(db_path, None, event_type, message, metadata=meta)
    except Exception:
        # Telemetry must never break the state machine.
        pass


# ── Public API ───────────────────────────────────────────────────────────────

class BatchTransitionError(RuntimeError):
    """Raised when a guarded transition is attempted from a wrong ``from_status``."""


def get_or_create_collecting_batch(
    db_path,
    *,
    allow_parallel_batches: bool,
    now: str | None = None,
    max_batch_size: int | None = None,
) -> str:
    """Return the current open ``collecting`` batch, creating a new one if none exists.

    A new batch is created when:
      - no batch with status ``collecting`` exists, or
      - the only ``collecting`` batch has already reached ``max_batch_size`` and
        is therefore unable to accept the new ticket (callers freeze it on the
        next cycle via :func:`try_freeze_idle_batches`).

    When ``allow_parallel_batches=False`` and any batch is currently
    ``dispatching``, the (new or existing) collecting batch is marked with
    ``freeze_blocked=TRUE`` and ``freeze_blocked_reason='prior_batch_dispatching'``
    so :func:`try_freeze_idle_batches` will not freeze it. Tickets continue to be
    ingested normally; only freezing is held back.
    """
    now_str = now or _now_iso()
    collecting = runtime_db.list_backlog_batches(db_path, status=BatchStatus.COLLECTING.value)
    dispatching_exists = bool(
        runtime_db.list_backlog_batches(db_path, status=BatchStatus.DISPATCHING.value)
    )
    should_block = (not allow_parallel_batches) and dispatching_exists

    if collecting:
        batch = collecting[0]
        batch_id = batch["batch_id"]
        size = len(runtime_db.list_backlog_batch_ticket_ids(db_path, batch_id))
        if max_batch_size is not None and size >= max_batch_size:
            return _create_new_collecting_batch(
                db_path, now_str, should_block=should_block
            )
        if should_block and not batch.get("freeze_blocked"):
            runtime_db.update_backlog_batch(
                db_path,
                batch_id,
                freeze_blocked=1,
                freeze_blocked_reason="prior_batch_dispatching",
            )
            _emit_event(
                db_path,
                "batch.freeze_blocked",
                f"batch {batch_id} freeze blocked by prior dispatching batch",
                batch_id=batch_id,
                metadata={"reason": "prior_batch_dispatching"},
            )
        return batch_id

    return _create_new_collecting_batch(db_path, now_str, should_block=should_block)


def _create_new_collecting_batch(db_path, now_str: str, *, should_block: bool) -> str:
    batch_id = _next_batch_id(db_path)
    runtime_db.insert_backlog_batch(
        db_path,
        batch_id,
        status=BatchStatus.COLLECTING.value,
        created_at=now_str,
        last_activity_at=now_str,
        freeze_blocked=should_block,
        freeze_blocked_reason="prior_batch_dispatching" if should_block else None,
    )
    _emit_event(
        db_path,
        "batch.created",
        f"batch {batch_id} created (status=collecting, freeze_blocked={should_block})",
        batch_id=batch_id,
        metadata={"freeze_blocked": should_block},
    )
    if should_block:
        _emit_event(
            db_path,
            "batch.freeze_blocked",
            f"batch {batch_id} freeze blocked by prior dispatching batch",
            batch_id=batch_id,
            metadata={"reason": "prior_batch_dispatching"},
        )
    return batch_id


def add_ticket_to_batch(
    db_path,
    batch_id: str,
    ticket_id: str,
    *,
    now: str | None = None,
) -> bool:
    """Insert ``ticket_id`` into ``batch_id`` if not already in any batch.

    Idempotent: a ticket already attached to a batch is left untouched and the
    function returns ``False``. Returns ``True`` when a new membership row is
    inserted; ``last_activity_at`` is bumped on success so idle freeze logic
    sees fresh activity.
    """
    now_str = now or _now_iso()
    existing = runtime_db.get_batch_for_ticket(db_path, ticket_id)
    if existing is not None:
        return False
    inserted = runtime_db.insert_backlog_batch_ticket(db_path, batch_id, ticket_id, now_str)
    if inserted:
        runtime_db.update_backlog_batch(db_path, batch_id, last_activity_at=now_str)
        _emit_event(
            db_path,
            "batch.ticket_added",
            f"ticket {ticket_id} added to batch {batch_id}",
            batch_id=batch_id,
            metadata={"ticket_id": ticket_id},
        )
    return inserted


def _idle_for_minutes(last_activity_at: str, now: str, idle_timeout_minutes: int) -> bool:
    activity = _parse_iso(last_activity_at)
    now_dt = _parse_iso(now)
    if activity is None or now_dt is None:
        return False
    elapsed = (now_dt - activity).total_seconds() / 60.0
    return elapsed >= float(idle_timeout_minutes)


def try_freeze_idle_batches(
    db_path,
    *,
    idle_timeout_minutes: int,
    max_batch_size: int,
    now: str | None = None,
) -> list[str]:
    """Transition idle (or size-capped) ``collecting`` batches to ``frozen``.

    A batch with ``freeze_blocked=TRUE`` is never frozen here. Returns the
    list of batch ids that transitioned to ``frozen`` on this call.
    """
    now_str = now or _now_iso()
    frozen: list[str] = []
    for batch in runtime_db.list_backlog_batches(db_path, status=BatchStatus.COLLECTING.value):
        if batch.get("freeze_blocked"):
            continue
        batch_id = batch["batch_id"]
        members = runtime_db.list_backlog_batch_ticket_ids(db_path, batch_id)
        size = len(members)
        if size == 0:
            continue
        idle = _idle_for_minutes(batch.get("last_activity_at"), now_str, idle_timeout_minutes)
        full = size >= max_batch_size
        if not (idle or full):
            continue
        runtime_db.update_backlog_batch(
            db_path,
            batch_id,
            status=BatchStatus.FROZEN.value,
            frozen_at=now_str,
        )
        _emit_event(
            db_path,
            "batch.frozen",
            f"batch {batch_id} frozen (size={size}, reason={'size' if full else 'idle'})",
            batch_id=batch_id,
            metadata={
                "size": size,
                "reason": "size" if full else "idle",
                "from": BatchStatus.COLLECTING.value,
                "to": BatchStatus.FROZEN.value,
            },
        )
        frozen.append(batch_id)
    return frozen


def unblock_freezing_for_pending_collecting_batches(db_path) -> list[str]:
    """Clear ``freeze_blocked`` once no batch is currently ``dispatching``.

    Called after a batch reaches ``completed``. Returns the list of batch ids
    that had their ``freeze_blocked`` flag cleared.
    """
    dispatching = runtime_db.list_backlog_batches(
        db_path, status=BatchStatus.DISPATCHING.value
    )
    if dispatching:
        return []
    cleared: list[str] = []
    for batch in runtime_db.list_backlog_batches(db_path, status=BatchStatus.COLLECTING.value):
        if not batch.get("freeze_blocked"):
            continue
        if (batch.get("freeze_blocked_reason") or "") != "prior_batch_dispatching":
            continue
        batch_id = batch["batch_id"]
        runtime_db.update_backlog_batch(
            db_path,
            batch_id,
            freeze_blocked=0,
            freeze_blocked_reason=None,
        )
        _emit_event(
            db_path,
            "batch.freeze_unblocked",
            f"batch {batch_id} freeze_blocked cleared",
            batch_id=batch_id,
        )
        cleared.append(batch_id)
    return cleared


def transition_batch(
    db_path,
    batch_id: str,
    from_status: str,
    to_status: str,
    *,
    reason: str | None = None,
    extra_fields: dict | None = None,
) -> None:
    """Guarded transition: refuses to apply if current status != ``from_status``.

    Raises :class:`BatchTransitionError` so the caller treats it as a race
    rather than a silent overwrite.
    """
    row = runtime_db.get_backlog_batch(db_path, batch_id)
    if row is None:
        raise BatchTransitionError(f"unknown batch_id={batch_id}")
    if (row.get("status") or "") != from_status:
        raise BatchTransitionError(
            f"batch {batch_id} expected status={from_status}, found={row.get('status')}"
        )
    fields: dict = {"status": to_status}
    if extra_fields:
        fields.update(extra_fields)
    runtime_db.update_backlog_batch(db_path, batch_id, **fields)
    _emit_event(
        db_path,
        "batch.status_changed",
        f"batch {batch_id} {from_status} -> {to_status}"
        + (f" ({reason})" if reason else ""),
        batch_id=batch_id,
        metadata={"from": from_status, "to": to_status, "reason": reason},
    )


def mark_dependency_analysis_attempt_started(
    db_path,
    batch_id: str,
    *,
    now: str | None = None,
) -> None:
    """Increment attempts and transition to ``dependency_analysis_running``.

    Accepts a starting status of either ``frozen`` or
    ``dependency_analysis_failed`` (retry).
    """
    now_str = now or _now_iso()
    row = runtime_db.get_backlog_batch(db_path, batch_id)
    if row is None:
        raise BatchTransitionError(f"unknown batch_id={batch_id}")
    current = (row.get("status") or "")
    if current not in {
        BatchStatus.FROZEN.value,
        BatchStatus.DEPENDENCY_ANALYSIS_FAILED.value,
    }:
        raise BatchTransitionError(
            f"batch {batch_id} cannot start dependency analysis from status={current}"
        )
    attempts = int(row.get("dependency_analysis_attempts") or 0) + 1
    runtime_db.update_backlog_batch(
        db_path,
        batch_id,
        status=BatchStatus.DEPENDENCY_ANALYSIS_RUNNING.value,
        dependency_analysis_attempts=attempts,
        next_dependency_analysis_retry_at=None,
    )
    _emit_event(
        db_path,
        "batch.dependency_analysis_started",
        f"batch {batch_id} dependency analysis attempt {attempts} started",
        batch_id=batch_id,
        metadata={"attempt": attempts, "from": current},
    )


def mark_dependency_analysis_succeeded(
    db_path,
    batch_id: str,
) -> None:
    """Transition to ``readiness_running`` and clear retry / error state."""
    row = runtime_db.get_backlog_batch(db_path, batch_id)
    if row is None:
        raise BatchTransitionError(f"unknown batch_id={batch_id}")
    if (row.get("status") or "") != BatchStatus.DEPENDENCY_ANALYSIS_RUNNING.value:
        raise BatchTransitionError(
            f"batch {batch_id} expected dependency_analysis_running, "
            f"found={row.get('status')}"
        )
    runtime_db.update_backlog_batch(
        db_path,
        batch_id,
        status=BatchStatus.READINESS_RUNNING.value,
        last_dependency_analysis_error=None,
        next_dependency_analysis_retry_at=None,
    )
    _emit_event(
        db_path,
        "batch.dependency_analysis_completed",
        f"batch {batch_id} dependency analysis completed",
        batch_id=batch_id,
        metadata={"to": BatchStatus.READINESS_RUNNING.value},
    )
    _emit_event(
        db_path,
        "batch.readiness_started",
        f"batch {batch_id} readiness phase started",
        batch_id=batch_id,
    )


def mark_dependency_analysis_failed(
    db_path,
    batch_id: str,
    *,
    error: str,
    cooldown_minutes: int,
    max_attempts: int,
    now: str | None = None,
) -> dict:
    """Record a failed analysis and schedule the next retry (or mark terminal).

    Returns a dict ``{"attempts": int, "exhausted": bool, "next_retry_at": str | None}``.
    Emits ``batch.dependency_analysis_failed`` always, plus
    ``batch.dependency_analysis_exhausted`` exactly once when the limit is reached.
    """
    now_str = now or _now_iso()
    row = runtime_db.get_backlog_batch(db_path, batch_id)
    if row is None:
        raise BatchTransitionError(f"unknown batch_id={batch_id}")
    attempts = int(row.get("dependency_analysis_attempts") or 0)
    exhausted = attempts >= max_attempts
    if exhausted:
        next_retry_at = None
    else:
        now_dt = _parse_iso(now_str) or datetime.datetime.now(datetime.timezone.utc)
        next_retry = now_dt + datetime.timedelta(minutes=cooldown_minutes)
        next_retry_at = next_retry.strftime("%Y-%m-%dT%H:%M:%SZ")
    runtime_db.update_backlog_batch(
        db_path,
        batch_id,
        status=BatchStatus.DEPENDENCY_ANALYSIS_FAILED.value,
        last_dependency_analysis_error=error,
        next_dependency_analysis_retry_at=next_retry_at,
    )
    _emit_event(
        db_path,
        "batch.dependency_analysis_failed",
        f"batch {batch_id} dependency analysis attempt {attempts} failed",
        batch_id=batch_id,
        metadata={
            "attempt": attempts,
            "next_retry_at": next_retry_at,
            "exhausted": exhausted,
            "error": error[:500] if isinstance(error, str) else error,
        },
    )
    if exhausted:
        _emit_event(
            db_path,
            "batch.dependency_analysis_exhausted",
            f"batch {batch_id} dependency analysis exhausted ({attempts} attempts)",
            batch_id=batch_id,
            metadata={"attempts": attempts},
        )
    return {
        "attempts": attempts,
        "exhausted": exhausted,
        "next_retry_at": next_retry_at,
    }


def batch_intelligence_complete(db_path, batch_id: str) -> bool:
    """Return True when every batch member has completed Ticket Intelligence."""
    members = list_batch_tickets(db_path, batch_id)
    if not members:
        return True
    for ticket_id in members:
        row = runtime_db.get_ticket_intelligence(db_path, ticket_id)
        if row is None or row.get("analysis_status") != "completed":
            return False
    return True


def pick_batches_ready_for_dependency_analysis(
    db_path,
    *,
    now: str | None = None,
    max_attempts: int,
) -> list[str]:
    """Return batch ids eligible to run (or retry) dependency analysis."""
    now_str = now or _now_iso()
    now_dt = _parse_iso(now_str)
    out: list[str] = []
    for batch in runtime_db.list_backlog_batches(db_path, status=BatchStatus.FROZEN.value):
        if batch_intelligence_complete(db_path, batch["batch_id"]):
            out.append(batch["batch_id"])
    for batch in runtime_db.list_backlog_batches(
        db_path, status=BatchStatus.DEPENDENCY_ANALYSIS_FAILED.value
    ):
        attempts = int(batch.get("dependency_analysis_attempts") or 0)
        if attempts >= max_attempts:
            continue
        next_retry_at = batch.get("next_dependency_analysis_retry_at")
        if next_retry_at is None:
            continue
        retry_dt = _parse_iso(next_retry_at)
        if retry_dt is None or now_dt is None or now_dt >= retry_dt:
            if batch_intelligence_complete(db_path, batch["batch_id"]):
                out.append(batch["batch_id"])
    return out


def list_batch_tickets(db_path, batch_id: str) -> list[str]:
    return runtime_db.list_backlog_batch_ticket_ids(db_path, batch_id)


def get_batch_status(db_path, batch_id: str) -> dict | None:
    row = runtime_db.get_backlog_batch(db_path, batch_id)
    if row is None:
        return None
    members = runtime_db.list_backlog_batch_ticket_ids(db_path, batch_id)
    return {
        "batch_id": batch_id,
        "status": row.get("status"),
        "freeze_blocked": bool(row.get("freeze_blocked")),
        "freeze_blocked_reason": row.get("freeze_blocked_reason"),
        "attempts": int(row.get("dependency_analysis_attempts") or 0),
        "last_error": row.get("last_dependency_analysis_error"),
        "next_retry_at": row.get("next_dependency_analysis_retry_at"),
        "ticket_count": len(members),
        "created_at": row.get("created_at"),
        "frozen_at": row.get("frozen_at"),
        "completed_at": row.get("completed_at"),
    }


def get_batch_id_for_ticket(db_path, ticket_id: str) -> str | None:
    return runtime_db.get_batch_for_ticket(db_path, ticket_id)


def get_ticket_batch_status(db_path, ticket_id: str) -> str | None:
    """Return the status of the batch containing ``ticket_id``, or None."""
    batch_id = runtime_db.get_batch_for_ticket(db_path, ticket_id)
    if batch_id is None:
        return None
    row = runtime_db.get_backlog_batch(db_path, batch_id)
    if row is None:
        return None
    return row.get("status")


__all__ = [
    "BatchStatus",
    "BatchTransitionError",
    "add_ticket_to_batch",
    "batch_intelligence_complete",
    "get_batch_id_for_ticket",
    "get_batch_status",
    "get_or_create_collecting_batch",
    "get_ticket_batch_status",
    "list_batch_tickets",
    "mark_dependency_analysis_attempt_started",
    "mark_dependency_analysis_failed",
    "mark_dependency_analysis_succeeded",
    "pick_batches_ready_for_dependency_analysis",
    "transition_batch",
    "try_freeze_idle_batches",
    "unblock_freezing_for_pending_collecting_batches",
]
