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


def find_next_ticket(db_path, ticket_ids: list[str]) -> str | None:
    """Return the first ticket needing pipeline work, in scan order."""
    for ticket_id in ticket_ids:
        try:
            intel = runtime_db.get_ticket_intelligence(db_path, ticket_id)
            ready = runtime_db.get_ticket_readiness(db_path, ticket_id)
        except Exception:
            continue
        if needs_intelligence(intel) or needs_readiness(intel, ready):
            return ticket_id
    return None


def maybe_run_readiness_after_intelligence(
    db_path,
    ticket_id: str,
    ticket_content: str,
    project_root: Path,
) -> None:
    """Chain readiness after a successful intelligence run when auto-pipeline is on."""
    if not is_auto_pipeline_enabled(db_path):
        return
    try:
        ready = runtime_db.get_ticket_readiness(db_path, ticket_id)
    except Exception:
        ready = None
    intel = {"analysis_status": "completed"}
    if needs_readiness(intel, ready):
        logger.info("pipeline: auto readiness for %s after intelligence", ticket_id)
        run_evaluation(db_path, ticket_id, ticket_content, Path(project_root))


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

    if needs_readiness(intel, ready):
        logger.info("pipeline: running readiness for %s", ticket_id)
        run_evaluation(db_path, ticket_id, content, project_root)
        return True

    return False


__all__ = [
    "find_next_ticket",
    "is_auto_pipeline_enabled",
    "maybe_run_readiness_after_intelligence",
    "needs_intelligence",
    "needs_readiness",
    "process_ticket",
]
