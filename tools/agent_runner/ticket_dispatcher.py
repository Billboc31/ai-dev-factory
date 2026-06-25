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


def _read_ticket_content(project_root: Path, ticket_id: str) -> str:
    path = project_root / "runs" / ticket_id / "ticket.md"
    if path.is_file():
        try:
            return path.read_text(encoding="utf-8")
        except OSError:
            return ""
    return ""


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


def _sort_key(rec: dict) -> tuple:
    """Stable ordering: higher score first, then lower queue_rank, then older
    updated_at (ascending ISO string), then ticket_id."""
    queue_rank = rec.get("_queue_rank")
    queue_rank_key = queue_rank if queue_rank is not None else 10_000
    updated_at = rec.get("_updated_at") or "9999"
    return (-int(rec["score"]), queue_rank_key, updated_at, rec["ticket_id"])


def get_recommended_tickets(
    db_path,
    project_root: Path,
    *,
    project_id: str | None = None,
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

    for row in rows:
        ticket_id = (row.get("ticket_id") or "").strip()
        if not ticket_id:
            continue
        if not _candidate_row(row):
            continue

        ticket_content = _read_ticket_content(project_root, ticket_id)
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
]
