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
    if status in {"queued", "completed"}:
        return False
    if status == "running":
        # Zombie "running" rows (daemon/worker killed mid-flight) must be
        # reclaimed — otherwise batches stay frozen forever.
        return _intelligence_running_is_stale(row)
    return True


def _intelligence_running_is_stale(row: dict, *, max_age_seconds: int = 1800) -> bool:
    """True when a ``running`` intelligence row is older than ``max_age_seconds``."""
    import datetime as _dt

    raw = row.get("started_at") or row.get("updated_at") or ""
    if not raw:
        return True
    try:
        started = _dt.datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        if started.tzinfo is None:
            started = started.replace(tzinfo=_dt.timezone.utc)
    except ValueError:
        return True
    age = (_dt.datetime.now(_dt.timezone.utc) - started).total_seconds()
    return age >= max_age_seconds


def reset_stale_intelligence(db_path, ticket_id: str) -> bool:
    """Flip a stale ``running`` intelligence row back to ``not_started``.

    Returns True when a row was reset (caller should re-claim / re-run).
    """
    try:
        intel = runtime_db.get_ticket_intelligence(db_path, ticket_id)
    except Exception:
        return False
    if not intel or intel.get("analysis_status") != "running":
        return False
    if not _intelligence_running_is_stale(intel):
        return False
    try:
        runtime_db.upsert_ticket_intelligence(
            db_path,
            ticket_id,
            analysis_status="not_started",
            started_at=None,
        )
        logger.info("pipeline: reset stale running intelligence for %s", ticket_id)
        return True
    except Exception as exc:
        logger.warning(
            "pipeline: failed to reset stale intelligence for %s: %s",
            ticket_id,
            exc,
        )
        return False


def needs_readiness(
    intel_row: dict | None,
    ready_row: dict | None,
    *,
    batch_status: str | None = None,
) -> bool:
    if intel_row is None or intel_row.get("analysis_status") != "completed":
        return False
    if ready_row is None:
        return True
    status = ready_row.get("readiness_status") or ""
    if status in {"", "not_started", "queued", "running", "failed"}:
        return True
    if status == "ready_candidate":
        return False
    if status == "blocked":
        # During the initial batch readiness pass, ``blocked`` is a terminal
        # outcome — re-running would flip rows back to ``running`` and prevent
        # ``readiness_running`` batches from advancing to ``dispatching``.
        # Once dispatching starts, re-evaluate so dependency merges can unblock.
        return batch_status not in (None, "readiness_running")
    return False


def _ticket_batch_status(db_path, ticket_id: str) -> str | None:
    if _backlog_batch is None:
        return None
    try:
        return _backlog_batch.get_ticket_batch_status(db_path, ticket_id)
    except Exception:
        return None


def ticket_needs_readiness(
    db_path,
    ticket_id: str,
    intel_row: dict | None,
    ready_row: dict | None,
) -> bool:
    """Return whether readiness work should run for ``ticket_id``."""
    if not _is_batch_ready_for_readiness(db_path, ticket_id):
        return False
    return needs_readiness(
        intel_row,
        ready_row,
        batch_status=_ticket_batch_status(db_path, ticket_id),
    )


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
        if ticket_needs_readiness(db_path, ticket_id, intel, ready):
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
    if not ticket_needs_readiness(db_path, ticket_id, intel, ready):
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
# Delegated to ``runtime_db.claim_ticket_*`` so SQLite and Postgres backends
# share one implementation per backend (see runtime_db.py / runtime_db_pg.py).


def claim_intelligence(db_path, ticket_id: str) -> bool:
    """Atomically claim the intelligence stage for ``ticket_id``.

    Returns True when the caller must run the stage. Returns False when
    another worker already owns the run or the analysis is already complete.
    """
    return runtime_db.claim_ticket_intelligence(db_path, ticket_id)


def claim_readiness(db_path, ticket_id: str) -> bool:
    """Atomically claim the readiness stage for ``ticket_id``.

    Returns True when the caller must run the evaluation. Returns False when
    another worker already owns the run or the evaluation is complete.
    """
    return runtime_db.claim_ticket_readiness(db_path, ticket_id)


def record_intake_once(
    db_path,
    issue_number: int,
    ticket_id: str,
    branch: str | None = None,
) -> bool:
    """Insert one ``issue_intake`` row if the GitHub issue was not seen before.

    Returns True on a fresh insert, False when the issue was already intaken.
    """
    return runtime_db.record_intake_once(db_path, issue_number, ticket_id, branch)


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

    if reset_stale_intelligence(db_path, ticket_id):
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

    if ticket_needs_readiness(db_path, ticket_id, intel, ready):
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
    "ticket_needs_readiness",
    "process_ticket",
    "record_intake_once",
]
