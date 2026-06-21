"""Ticket Readiness Evaluator.

Advisory pipeline step that decides whether a ticket is eligible to enter the
development pipeline. Independent of execution: the evaluator persists a
readiness verdict per ticket but does not start, queue, or block runs.

Designed to run in a background thread. ``run_evaluation`` never raises:
unexpected errors are persisted as ``readiness_status="failed"`` with the
exception details captured in ``warnings``.

Status enum (canonical, lowercase snake_case — UI labels live elsewhere):

    not_started | queued | running | ready_candidate | blocked | failed
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

_TOOLS_DIR = Path(__file__).resolve().parent
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

import runtime_db  # noqa: E402
from ticket_merge_state import is_ticket_merged  # noqa: E402


_GIT_TIMEOUT = 10

# Case-insensitive dependency markers.
_DEPENDENCY_RE = re.compile(
    r"(?:depends\s+on|after|blocked\s+by)\s+(T\d+)",
    re.IGNORECASE,
)

# Ticket runtime states that imply a human has approved the plan.
_PLAN_APPROVED_OR_LATER = frozenset({
    "PLAN_APPROVED",
    "IMPLEMENTATION_REVIEW_NEEDED",
    "IMPLEMENTATION_FIX_REQUIRED",
    "IMPLEMENTATION_APPROVED",
    "TEST_COMPLETE",
})


# ── Individual checks ────────────────────────────────────────────────────────

def _check_intelligence(db_path, ticket_id: str) -> tuple[str, str | None]:
    """Returns (status, blocking_reason). ``passed`` iff a completed intelligence row exists."""
    try:
        row = runtime_db.get_ticket_intelligence(db_path, ticket_id)
    except Exception:
        row = None
    if row is None or (row.get("analysis_status") or "") != "completed":
        return "failed", "Missing Ticket Intelligence analysis"
    return "passed", None


def _extract_dependencies(ticket_content: str) -> list[str]:
    """Return a stable, deduplicated, uppercase list of dependency ticket IDs."""
    if not ticket_content:
        return []
    seen: list[str] = []
    for match in _DEPENDENCY_RE.finditer(ticket_content):
        dep = match.group(1).upper()
        if dep not in seen:
            seen.append(dep)
    return seen


def _check_dependencies(
    ticket_content: str,
    project_root: Path,
) -> tuple[str, list[str]]:
    """Returns (status, blocking_reasons). Empty deps → ``passed``."""
    deps = _extract_dependencies(ticket_content)
    if not deps:
        return "passed", []

    reasons: list[str] = []
    for dep in deps:
        try:
            result = is_ticket_merged(project_root, dep)
        except Exception:
            reasons.append(f"Dependency {dep} merge state unknown")
            continue
        if result.status == "merged":
            continue
        if result.status == "not_merged":
            reasons.append(f"Dependency {dep} not merged")
        else:
            reasons.append(f"Dependency {dep} merge state unknown")

    return ("passed" if not reasons else "failed"), reasons


def _has_plan_approved_marker(project_root: Path, ticket_id: str) -> bool:
    """Look for an explicit ``runs/<ticket>/plan-approved.md`` marker."""
    return (project_root / "runs" / ticket_id / "plan-approved.md").is_file()


def _state_implies_plan_approved(project_root: Path, ticket_id: str) -> bool:
    """Treat the ticket's runtime ``state`` at or beyond PLAN_APPROVED as an approval signal."""
    state_path = project_root / "runs" / ticket_id / "state.json"
    if not state_path.is_file():
        return False
    try:
        data = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    state = (data.get("state") or "").strip().upper()
    return state in _PLAN_APPROVED_OR_LATER


def _check_human_approval(
    intelligence_row: dict | None,
    project_root: Path,
    ticket_id: str,
) -> tuple[str, str | None, int, int]:
    """Returns (status, blocking_reason, required_flag, present_flag).

    Required = 1 only when intelligence requested a human plan review.
    """
    required = bool(intelligence_row and intelligence_row.get("requires_human_plan_review"))
    if not required:
        return "passed", None, 0, 0

    present = (
        _has_plan_approved_marker(project_root, ticket_id)
        or _state_implies_plan_approved(project_root, ticket_id)
    )
    present_flag = 1 if present else 0
    if present:
        return "passed", None, 1, present_flag
    return "failed", "Human plan approval missing", 1, present_flag


def _check_context_freshness(project_root: Path) -> tuple[str, str | None]:
    """Capture the current ``main`` SHA. ``fresh`` on success, ``unknown`` on failure."""
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "main"],
            cwd=str(project_root),
            capture_output=True,
            text=True,
            timeout=_GIT_TIMEOUT,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return "unknown", None
    if proc.returncode != 0:
        return "unknown", None
    sha = proc.stdout.strip()
    if not sha:
        return "unknown", None
    return "fresh", sha


# ── Orchestrator ─────────────────────────────────────────────────────────────

def run_evaluation(
    db_path,
    ticket_id: str,
    ticket_content: str,
    project_root: Path,
) -> None:
    """Run the full readiness evaluation for ``ticket_id`` and persist the verdict.

    Background-thread safe: never raises. Persists ``readiness_status="failed"``
    with an explanatory warning if an unexpected exception slips through.
    """
    project_root = Path(project_root)

    runtime_db.upsert_ticket_readiness(db_path, ticket_id, readiness_status="running")

    try:
        intelligence_row = None
        try:
            intelligence_row = runtime_db.get_ticket_intelligence(db_path, ticket_id)
        except Exception:
            intelligence_row = None

        intel_status, intel_reason = _check_intelligence(db_path, ticket_id)
        dep_status, dep_reasons = _check_dependencies(ticket_content, project_root)
        approval_status, approval_reason, approval_required, approval_present = (
            _check_human_approval(intelligence_row, project_root, ticket_id)
        )
        freshness_status, main_sha = _check_context_freshness(project_root)

        blocking_reasons: list[str] = []
        if intel_reason:
            blocking_reasons.append(intel_reason)
        blocking_reasons.extend(dep_reasons)
        if approval_reason:
            blocking_reasons.append(approval_reason)

        all_passed = (
            intel_status == "passed"
            and dep_status == "passed"
            and approval_status == "passed"
        )
        readiness_status = "ready_candidate" if all_passed else "blocked"
        ready_candidate = 1 if all_passed else 0

        runtime_db.upsert_ticket_readiness(
            db_path,
            ticket_id,
            readiness_status=readiness_status,
            ready_candidate=ready_candidate,
            blocking_reasons_json=blocking_reasons,
            warnings_json=[],
            dependency_check_status=dep_status,
            approval_check_status=approval_status,
            context_freshness_status=freshness_status,
            human_approval_required=approval_required,
            human_approval_present=approval_present,
            main_sha_when_evaluated=main_sha,
            evaluated_at=runtime_db._now_iso(),
        )

    except Exception as exc:  # noqa: BLE001 — background job must not raise.
        try:
            runtime_db.upsert_ticket_readiness(
                db_path,
                ticket_id,
                readiness_status="failed",
                ready_candidate=0,
                blocking_reasons_json=[],
                warnings_json=[f"Unexpected error: {exc}"],
                evaluated_at=runtime_db._now_iso(),
            )
        except Exception:
            # Even the persistence path failed — there is nothing more we can do.
            pass
