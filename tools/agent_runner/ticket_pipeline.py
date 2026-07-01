"""Automatic ticket intelligence + readiness pipeline.

When enabled, the daemon runs intelligence analysis on newly ingested (or
backlogged) tickets, then readiness evaluation once intelligence completes.
Manual POST endpoints remain available for re-runs.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

_TOOLS_DIR = Path(__file__).resolve().parent
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

import runtime_db  # noqa: E402
import runtime_settings as _runtime_settings  # noqa: E402
from ticket_readiness_evaluator import read_ticket_markdown, run_evaluation  # noqa: E402

try:
    import backlog_batch as _backlog_batch  # noqa: E402
except ImportError:
    _backlog_batch = None  # type: ignore[assignment]

_BATCH_READY_FOR_READINESS = frozenset({
    "readiness_running",
    "dispatching",
    "completed",
})

logger = logging.getLogger("ticket_pipeline")

_SETTING_KEY = "AUTO_TICKET_PIPELINE"
_ENV_VAR = "AI_DEV_FACTORY_AUTO_TICKET_PIPELINE"


def is_auto_pipeline_enabled(db_path) -> bool:
    """Return whether the automatic intelligence → readiness pipeline is on."""
    try:
        return bool(_runtime_settings.get_setting(db_path, _SETTING_KEY))
    except Exception:
        raw = os.environ.get(_ENV_VAR)
        if raw is not None:
            text = str(raw).strip().lower()
            return text in {"true", "1", "yes", "on"}
        return True


def needs_intelligence(row: dict | None) -> bool:
    if row is None:
        return True
    status = row.get("analysis_status") or ""
    if status in {"queued", "running", "completed"}:
        return False
    return True


def needs_readiness(intel_row: dict | None, ready_row: dict | None) -> bool:
    if intel_row is None or intel_row.get("analysis_status") != "completed":
        return False
    if ready_row is None:
        return True
    status = ready_row.get("readiness_status") or ""
    return status in {"queued", "running"}


def _is_batch_ready_for_readiness(db_path, ticket_id: str) -> bool:
    """Return True when the ticket's batch (if any) authorises readiness evaluation.

    Tickets that do not belong to any batch (legacy / non-dispatcher flow) keep
    their previous behaviour and are eligible. Tickets in a batch are only
    eligible once the batch has reached ``readiness_running`` (or any later
    status — covers idempotent re-runs).
    """
    if _backlog_batch is None:
        return True
    try:
        status = _backlog_batch.get_ticket_batch_status(db_path, ticket_id)
    except Exception:
        return True
    if status is None:
        return True
    return status in _BATCH_READY_FOR_READINESS


def find_next_ticket(db_path, ticket_ids: list[str]) -> str | None:
    """Return the first ticket needing pipeline work, in scan order.

    Intelligence runs continuously (regardless of any batch state) so backlog
    ingestion always enriches new tickets. Readiness only runs once the ticket's
    batch (if any) is in ``readiness_running`` or later — tickets without a
    batch keep the legacy behaviour.
    """
    for ticket_id in ticket_ids:
        try:
            intel = runtime_db.get_ticket_intelligence(db_path, ticket_id)
            ready = runtime_db.get_ticket_readiness(db_path, ticket_id)
        except Exception:
            continue
        if needs_intelligence(intel):
            return ticket_id
        if needs_readiness(intel, ready) and _is_batch_ready_for_readiness(db_path, ticket_id):
            return ticket_id
    return None


def maybe_run_readiness_after_intelligence(
    db_path,
    ticket_id: str,
    ticket_content: str,
    project_root: Path,
    *,
    project_id: str | None = None,
) -> None:
    """Chain readiness after a successful intelligence run when auto-pipeline is on.

    Uses ``claim_readiness`` so the inline chain and the readiness thread pool
    cannot both process the same ticket at once.
    """
    if not is_auto_pipeline_enabled(db_path):
        return
    try:
        ready = runtime_db.get_ticket_readiness(db_path, ticket_id)
    except Exception:
        ready = None
    intel = {"analysis_status": "completed"}
    if not (needs_readiness(intel, ready) and _is_batch_ready_for_readiness(db_path, ticket_id)):
        return
    if not claim_readiness(db_path, ticket_id):
        logger.info(
            "pipeline: skip already_claimed ticket=%s stage=readiness (chain)",
            ticket_id,
        )
        return
    logger.info("pipeline: auto readiness for %s after intelligence", ticket_id)
    run_evaluation(
        db_path, ticket_id, ticket_content, Path(project_root), project_id=project_id
    )


# ── Atomic claim helpers (T221) ──────────────────────────────────────────────
#
# The stage runners (Ticket Intelligence and Readiness) can now execute in
# parallel across tickets. To keep them safe under concurrent scheduling we
# guarantee that at most one worker processes a given ticket at a time by
# claiming the stage atomically before touching it.
#
# Both helpers use a single UPSERT statement so the transition is atomic
# under WAL SQLite:
#   * If no row exists → INSERT with status='running' (PK guards uniqueness).
#   * If a row exists in a non-terminal / non-running state → UPDATE to
#     'running'; the ``WHERE`` clause on the ``DO UPDATE`` blocks the
#     transition when another worker already holds the claim or the stage
#     has completed.
# ``rowcount == 1`` when the caller now owns the claim; ``0`` otherwise.

_INTELLIGENCE_TERMINAL_OR_RUNNING = ("running", "completed")
_READINESS_TERMINAL_OR_RUNNING = ("running", "completed")


def claim_intelligence(db_path, ticket_id: str) -> bool:
    """Atomically claim the intelligence stage for ``ticket_id``.

    Returns True when the caller must run the stage. Returns False when
    another worker already owns the run or the analysis is already complete.
    """
    now = runtime_db._now_iso()
    with runtime_db._connect(db_path) as conn:
        cur = conn.execute(
            """
            INSERT INTO ticket_intelligence
                (ticket_id, analysis_status, started_at, created_at, updated_at)
            VALUES (?, 'running', ?, ?, ?)
            ON CONFLICT(ticket_id) DO UPDATE SET
                analysis_status = 'running',
                started_at      = excluded.started_at,
                updated_at      = excluded.updated_at
            WHERE ticket_intelligence.analysis_status NOT IN ('running', 'completed')
            """,
            (ticket_id, now, now, now),
        )
        return cur.rowcount == 1


def claim_readiness(db_path, ticket_id: str) -> bool:
    """Atomically claim the readiness stage for ``ticket_id``.

    Returns True when the caller must run the evaluation. Returns False when
    another worker already owns the run or the evaluation is complete.
    """
    now = runtime_db._now_iso()
    with runtime_db._connect(db_path) as conn:
        cur = conn.execute(
            """
            INSERT INTO ticket_readiness
                (ticket_id, readiness_status, created_at, updated_at)
            VALUES (?, 'running', ?, ?)
            ON CONFLICT(ticket_id) DO UPDATE SET
                readiness_status = 'running',
                updated_at       = excluded.updated_at
            WHERE ticket_readiness.readiness_status NOT IN ('running', 'completed')
            """,
            (ticket_id, now, now),
        )
        return cur.rowcount == 1


def record_intake_once(
    db_path,
    issue_number: int,
    ticket_id: str,
    branch: str | None = None,
) -> bool:
    """Insert one ``issue_intake`` row if the GitHub issue was not seen before.

    Returns True on a fresh insert, False when the issue was already intaken.
    The PK on ``issue_intake.issue_number`` makes this race-safe under WAL.
    """
    now = runtime_db._now_iso()
    with runtime_db._connect(db_path) as conn:
        cur = conn.execute(
            """
            INSERT INTO issue_intake
                (issue_number, ticket_id, branch, status, ingested_at, updated_at)
            VALUES (?, ?, ?, 'ingested', ?, ?)
            ON CONFLICT(issue_number) DO NOTHING
            """,
            (issue_number, ticket_id, branch, now, now),
        )
        return cur.rowcount == 1


def process_ticket(
    db_path,
    ticket_id: str,
    project_root: Path,
    exec_cmd: str,
    *,
    worktrees_dir: Path | None = None,
    project_id: str | None = None,
) -> bool:
    """Run intelligence and/or readiness for one ticket. Returns True if work ran."""
    if not is_auto_pipeline_enabled(db_path):
        return False

    import ticket_intelligence_analyzer as analyzer  # noqa: WPS433

    project_root = Path(project_root)
    content = read_ticket_markdown(
        project_root,
        ticket_id,
        worktrees_dir=worktrees_dir,
        project_id=project_id,
    )

    try:
        intel = runtime_db.get_ticket_intelligence(db_path, ticket_id)
    except Exception:
        intel = None

    if needs_intelligence(intel):
        logger.info("pipeline: running intelligence for %s", ticket_id)
        analyzer.run_analysis(
            db_path,
            ticket_id,
            content,
            exec_cmd,
            project_root,
            project_id=project_id,
        )
        return True

    try:
        ready = runtime_db.get_ticket_readiness(db_path, ticket_id)
    except Exception:
        ready = None

    if needs_readiness(intel, ready) and _is_batch_ready_for_readiness(db_path, ticket_id):
        logger.info("pipeline: running readiness for %s", ticket_id)
        run_evaluation(db_path, ticket_id, content, project_root, project_id=project_id)
        return True

    return False


__all__ = [
    "claim_intelligence",
    "claim_readiness",
    "find_next_ticket",
    "is_auto_pipeline_enabled",
    "maybe_run_readiness_after_intelligence",
    "needs_intelligence",
    "needs_readiness",
    "process_ticket",
    "record_intake_once",
]
