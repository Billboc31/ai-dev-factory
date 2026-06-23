"""Stale ticket-intelligence analysis reaper.

A ``ticket_intelligence`` row whose ``analysis_status`` is ``queued`` or
``running`` and whose ``updated_at`` has not progressed past the configured
threshold is considered stuck (the worker died, the supervisor never wrote
back, the API process crashed, ...). The reaper transitions such rows to
``failed`` with a descriptive ``analysis_summary`` so the dashboard can leave
the "Analysis in progress…" state without operator intervention.

The module is intentionally synchronous and stateless — callers (typically the
GET handler on the API) trigger it opportunistically. No background thread,
no scheduler, no daemon.
"""

from __future__ import annotations

import datetime
import sqlite3
import sys
from pathlib import Path
from typing import Any

_TOOLS_DIR = Path(__file__).resolve().parent
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

import runtime_db  # noqa: E402

STALE_QUEUED_SECONDS = 10 * 60
STALE_RUNNING_SECONDS = 15 * 60

_STATUS_THRESHOLDS = {
    "queued": STALE_QUEUED_SECONDS,
    "running": STALE_RUNNING_SECONDS,
}


def _parse_iso(value: str | None) -> datetime.datetime | None:
    if not value:
        return None
    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        dt = datetime.datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt


def _scan_stale_rows(db_path: Path) -> list[dict[str, Any]]:
    """Return the rows currently in ``queued``/``running`` (with ``updated_at``).

    Reads through a plain ``sqlite3`` connection so the function works on a
    raw DB path without requiring ``runtime_db`` row-decoding helpers.
    """
    if db_path is None:
        return []
    if not Path(str(db_path)).exists():
        return []
    with sqlite3.connect(str(db_path)) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT ticket_id, analysis_status, updated_at "
            "FROM ticket_intelligence "
            "WHERE analysis_status IN ('queued', 'running')"
        ).fetchall()
    return [dict(r) for r in rows]


def reap_stale_intelligence(
    db_path: Path,
    *,
    now: datetime.datetime | None = None,
) -> list[dict[str, Any]]:
    """Transition stuck ticket-intelligence rows to ``failed``.

    Returns one dict per recovered ticket (``ticket_id``, ``previous_status``,
    ``age_seconds``) so callers can log what was reaped. Rows still within the
    threshold are left untouched.
    """
    now = now or datetime.datetime.now(datetime.timezone.utc)
    recovered: list[dict[str, Any]] = []

    try:
        candidates = _scan_stale_rows(db_path)
    except sqlite3.Error:
        return recovered

    for row in candidates:
        status = row.get("analysis_status")
        threshold = _STATUS_THRESHOLDS.get(status)
        if threshold is None:
            continue
        updated_at = _parse_iso(row.get("updated_at"))
        if updated_at is None:
            continue
        age = (now - updated_at).total_seconds()
        if age < threshold:
            continue

        ticket_id = row["ticket_id"]
        summary = (
            f"Analysis stuck in {status!r} for {int(age)}s "
            "— auto-recovered by reaper."
        )
        runtime_db.upsert_ticket_intelligence(
            db_path,
            ticket_id,
            analysis_status="failed",
            analysis_summary=summary,
        )
        recovered.append(
            {
                "ticket_id": ticket_id,
                "previous_status": status,
                "age_seconds": int(age),
            }
        )
    return recovered
