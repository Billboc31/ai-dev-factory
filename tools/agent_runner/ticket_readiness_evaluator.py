"""Ticket Readiness Evaluator.

Readiness answers only: *can this ticket ENTER the workflow now?* It must
never block on plan approval, execution approval, planner review states,
execution rules, or ready-to-take. Those gates belong to later workflow
stages — the plan-review state machine, ``ticket_execution_eligibility``,
``ticket_approval_service``, and ``execution_rules_engine``.

Workflow-entry prerequisites evaluated here:

  * Ticket Intelligence analysis is completed.
  * All dependency tickets are merged.

Anything beyond those two checks is a non-blocking advisory warning. A
runtime guard (``_is_entry_prerequisite_reason``) drops — and logs — any
blocker that mentions ``approval``, ``plan review``, ``execution rule``, or
``ready_to_take``.

Designed to run in a background thread. ``run_evaluation`` never raises:
unexpected errors are persisted as ``readiness_status="failed"`` with the
exception details captured in ``warnings``.

Status enum (canonical, lowercase snake_case — UI labels live elsewhere):

    not_started | queued | running | ready_candidate | blocked | failed
"""

from __future__ import annotations

import json
import logging
import os
import re
import subprocess
import sys
from pathlib import Path

_TOOLS_DIR = Path(__file__).resolve().parent
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

import runtime_db  # noqa: E402
from ticket_merge_state import is_ticket_merged  # noqa: E402


logger = logging.getLogger("ticket_readiness_evaluator")

_GIT_TIMEOUT = 10

# Substrings that must NEVER appear in a readiness blocker — these all refer
# to later-stage gates (plan/execution approval, planner review states,
# execution rules, ready-to-take) and are owned by other components.
_FORBIDDEN_BLOCKER_SUBSTRINGS = (
    "approval",
    "plan review",
    "execution rule",
    "ready_to_take",
)


def _is_entry_prerequisite_reason(reason: str) -> bool:
    """True iff ``reason`` is a legitimate workflow-entry blocker.

    A workflow-entry blocker must not mention any later-stage gate. This is
    the runtime contract enforcement for the readiness scope.
    """
    if not reason:
        return False
    lowered = reason.lower()
    return not any(token in lowered for token in _FORBIDDEN_BLOCKER_SUBSTRINGS)

# Case-insensitive inline dependency markers (e.g. "Depends on T010.").
_INLINE_DEPENDENCY_RE = re.compile(
    r"(?:depends\s+on|after|blocked\s+by)\s+(T\d+)",
    re.IGNORECASE,
)

# Markdown section heading: "## Depends on" (common in GitHub-ingested tickets).
_DEPENDS_ON_SECTION_RE = re.compile(
    r"^#{1,6}\s*depends\s+on\s*$",
    re.IGNORECASE | re.MULTILINE,
)

# List item under a Depends-on section: "- T010 - description" or "1. T010".
_LIST_ITEM_TICKET_RE = re.compile(
    r"^[\s>]*(?:[-*+]|(?:\d+\.))\s+(T\d+)\b",
    re.IGNORECASE,
)

_HEADING_LINE_RE = re.compile(r"^#{1,6}\s+\S")

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


def _extract_dependencies_from_section(ticket_content: str, start: int) -> list[str]:
    """Parse ticket IDs from list items under a ``## Depends on`` section."""
    deps: list[str] = []
    rest = ticket_content[start:]
    for line in rest.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if _HEADING_LINE_RE.match(stripped):
            break
        match = _LIST_ITEM_TICKET_RE.match(stripped)
        if match:
            deps.append(match.group(1).upper())
        elif deps:
            # Prose after the list ends the dependency block.
            break
    return deps


def _extract_dependencies(ticket_content: str) -> list[str]:
    """Return a stable, deduplicated, uppercase list of dependency ticket IDs."""
    if not ticket_content:
        return []
    seen: list[str] = []

    def _add(dep: str) -> None:
        dep = dep.upper()
        if dep not in seen:
            seen.append(dep)

    for match in _INLINE_DEPENDENCY_RE.finditer(ticket_content):
        _add(match.group(1))
    for section in _DEPENDS_ON_SECTION_RE.finditer(ticket_content):
        for dep in _extract_dependencies_from_section(ticket_content, section.end()):
            _add(dep)
    return seen


def read_ticket_markdown(
    project_root: Path,
    ticket_id: str,
    *,
    worktrees_dir: Path | None = None,
    project_id: str | None = None,
) -> str:
    """Read ``ticket.md``, preferring the active worktree run dir when present."""
    project_root = Path(project_root)
    candidates: list[Path] = []
    if worktrees_dir is not None:
        candidates.append(
            worktrees_dir / ticket_id / "runs" / ticket_id / "ticket.md"
        )
    runtime_base = os.environ.get("RUNTIME_BASE_ROOT")
    if project_id and runtime_base:
        candidates.append(
            Path(runtime_base).expanduser()
            / project_id
            / "worktrees"
            / ticket_id
            / "runs"
            / ticket_id
            / "ticket.md"
        )
    candidates.append(project_root / "runs" / ticket_id / "ticket.md")
    for path in candidates:
        if path.is_file():
            try:
                return path.read_text(encoding="utf-8")
            except OSError:
                continue
    return ""


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
    """Treat the ticket's runtime ``state`` at or beyond PLAN_APPROVED as an approval signal.

    This is consulted *only* to promote ``ready_candidate`` → ``ready_to_take``
    when a downstream approval already exists. The planner-review states
    (``PLAN_REVIEW_NEEDED``, ``PLAN_FIX_REQUIRED``, ``PLAN_APPROVED``) must
    never influence the ``blocked`` status — readiness only cares about
    workflow-entry prerequisites.
    """
    state_path = project_root / "runs" / ticket_id / "state.json"
    if not state_path.is_file():
        return False
    try:
        data = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return False
    state = (data.get("state") or "").strip().upper()
    return state in _PLAN_APPROVED_OR_LATER


def _collect_future_approval_warnings(
    intelligence_row: dict | None,
    project_root: Path,
    ticket_id: str,
) -> tuple[str, list[str], int, int]:
    """Return (status, warnings, required_flag, present_flag) for downstream approvals.

    Emits *non-blocking* advisory warnings when intelligence indicates a
    human plan review or execution approval may be required later in the
    workflow. Never produces a blocking reason — those gates are owned by
    the plan-review state machine and ``ticket_approval_service``.

    ``required_flag`` and ``present_flag`` track the plan-review approval
    specifically (preserving the existing schema columns
    ``human_approval_required`` / ``human_approval_present``).
    """
    plan_required = bool(
        intelligence_row and intelligence_row.get("requires_human_plan_review")
    )
    execution_required = bool(
        intelligence_row and intelligence_row.get("requires_human_execution_approval")
    )

    if not plan_required and not execution_required:
        return "passed", [], 0, 0

    plan_present = False
    if plan_required:
        plan_present = (
            _has_plan_approved_marker(project_root, ticket_id)
            or _state_implies_plan_approved(project_root, ticket_id)
        )

    warnings: list[str] = []
    if plan_required and not plan_present:
        warnings.append("Human plan review may be required later")
    if execution_required:
        warnings.append("Human execution approval may be required later")

    status = "advisory" if warnings else "passed"
    required_flag = 1 if plan_required else 0
    present_flag = 1 if (plan_required and plan_present) else 0
    return status, warnings, required_flag, present_flag


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
        approval_status, approval_warnings, approval_required, approval_present = (
            _collect_future_approval_warnings(intelligence_row, project_root, ticket_id)
        )
        freshness_status, main_sha = _check_context_freshness(project_root)

        # Blockers come *only* from intelligence + dependency checks. The
        # ``_is_entry_prerequisite_reason`` guard enforces this contract at
        # runtime: any blocker that slips through referring to a later-stage
        # gate is dropped and logged. See module docstring for the contract.
        candidate_blockers: list[str] = []
        if intel_reason:
            candidate_blockers.append(intel_reason)
        candidate_blockers.extend(dep_reasons)

        blocking_reasons: list[str] = []
        for reason in candidate_blockers:
            if _is_entry_prerequisite_reason(reason):
                blocking_reasons.append(reason)
            else:
                logger.error(
                    "readiness blocker violates entry-prerequisite contract "
                    "and was dropped: ticket=%s reason=%r",
                    ticket_id,
                    reason,
                )

        warnings: list[str] = list(approval_warnings)

        all_passed = (
            intel_status == "passed"
            and dep_status == "passed"
        )
        readiness_status = "ready_candidate" if all_passed else "blocked"
        ready_candidate = 1 if all_passed else 0

        # Preserve ready_to_take across re-evaluations when an execution approval
        # is already on file. Without this, recomputing base candidacy would
        # silently demote an approved ticket back to ready_candidate.
        if readiness_status == "ready_candidate":
            try:
                latest_exec = runtime_db.get_latest_ticket_approval(
                    db_path, ticket_id, "execution"
                )
            except Exception:
                latest_exec = None
            if latest_exec and latest_exec.get("approval_status") == "approved":
                readiness_status = "ready_to_take"

        runtime_db.upsert_ticket_readiness(
            db_path,
            ticket_id,
            readiness_status=readiness_status,
            ready_candidate=ready_candidate,
            blocking_reasons_json=blocking_reasons,
            warnings_json=warnings,
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
