"""Ticket Execution Eligibility Service.

Read-only aggregator that produces a single ``READY_TO_TAKE`` decision for a
ticket by combining the existing — and intentionally untouched — Intelligence,
Readiness, Approval and dependency systems.

The service never writes to the runtime DB and never touches the scheduler or
worker. It returns a structured payload that the API and UI can consume
directly. The first failing check (in a fixed order) becomes the
``blocking_step``; the status is derived from which step failed.

Check order: intelligence → dependencies → readiness → approval.
"""

from __future__ import annotations

import datetime
import sys
from pathlib import Path

_TOOLS_DIR = Path(__file__).resolve().parent
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

import runtime_db  # noqa: E402
from ticket_merge_state import is_ticket_merged  # noqa: E402
from ticket_readiness_evaluator import _extract_dependencies  # noqa: E402


CHECK_ORDER = ("intelligence", "dependencies", "readiness", "approval")

_READY_READINESS_STATES = frozenset({"ready_candidate", "ready_to_take"})


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _safe_get(fn, *args, **kwargs):
    """Call ``fn`` and swallow any exception, returning None."""
    try:
        return fn(*args, **kwargs)
    except Exception:
        return None


# ── Per-check evaluators ─────────────────────────────────────────────────────

def _eval_intelligence(intelligence: dict | None) -> dict:
    if intelligence is None:
        return {
            "status": "failed",
            "detail": "Ticket Intelligence analysis is missing.",
        }
    analysis_status = (intelligence.get("analysis_status") or "").strip()
    if analysis_status == "completed":
        return {
            "status": "passed",
            "detail": "Ticket Intelligence analysis is completed.",
        }
    if analysis_status in {"queued", "running"}:
        return {
            "status": "pending",
            "detail": f"Ticket Intelligence analysis is {analysis_status}.",
        }
    if analysis_status == "failed":
        return {
            "status": "failed",
            "detail": "Ticket Intelligence analysis failed.",
        }
    if not analysis_status:
        return {
            "status": "unknown",
            "detail": "Ticket Intelligence analysis status is unknown.",
        }
    return {
        "status": "failed",
        "detail": f"Ticket Intelligence analysis_status='{analysis_status}'.",
    }


def _eval_dependencies(ticket_content: str | None, project_root: Path) -> dict:
    deps = _extract_dependencies(ticket_content or "")
    if not deps:
        return {
            "status": "passed",
            "detail": "No declared dependencies.",
            "unmet": [],
        }

    unmet: list[str] = []
    unknown: list[str] = []
    for dep in deps:
        result = None
        try:
            result = is_ticket_merged(project_root, dep)
        except Exception:
            unknown.append(dep)
            continue
        if result is None:
            unknown.append(dep)
            continue
        if result.status == "merged":
            continue
        if result.status == "not_merged":
            unmet.append(dep)
        else:
            unknown.append(dep)

    if not unmet and not unknown:
        return {
            "status": "passed",
            "detail": f"All {len(deps)} dependency(ies) merged.",
            "unmet": [],
        }
    if unmet:
        return {
            "status": "failed",
            "detail": f"Dependency {unmet[0]} not merged",
            "unmet": unmet + unknown,
        }
    return {
        "status": "unknown",
        "detail": f"Dependency {unknown[0]} merge state unknown",
        "unmet": unknown,
    }


def _eval_readiness(readiness: dict | None) -> dict:
    if readiness is None:
        return {
            "status": "failed",
            "detail": "Readiness evaluation has not been run.",
        }
    status = (readiness.get("readiness_status") or "").strip()
    if status in _READY_READINESS_STATES:
        return {"status": "passed", "detail": f"Readiness status is '{status}'."}
    if status in {"queued", "running"}:
        return {"status": "pending", "detail": f"Readiness evaluation is {status}."}
    if status == "blocked":
        reasons = readiness.get("blocking_reasons_json") or readiness.get("blocking_reasons") or []
        first = reasons[0] if isinstance(reasons, list) and reasons else "Readiness blocked."
        return {"status": "failed", "detail": str(first)}
    if status == "failed":
        return {"status": "failed", "detail": "Readiness evaluation failed."}
    if status in {"", "not_started"}:
        return {"status": "failed", "detail": "Readiness evaluation has not been run."}
    return {"status": "failed", "detail": f"Readiness status is '{status}'."}


def _eval_approval(
    intelligence: dict | None,
    approval_plan: dict | None,
    state_value: str | None,
    has_plan_approved_marker: bool,
) -> dict:
    """Approval check — only enforced when intelligence requested human plan review.

    ``state_value`` and ``has_plan_approved_marker`` mirror the readiness
    evaluator's plan-approval signals so we treat ``runs/<ticket>/state.json``
    states at or beyond ``PLAN_APPROVED`` (or an explicit ``plan-approved.md``
    marker) as a present approval.
    """
    required = bool((intelligence or {}).get("requires_human_plan_review"))
    if not required:
        return {
            "status": "passed",
            "detail": "Human plan review not required by Intelligence.",
        }

    state_implies_approved = False
    if state_value:
        # Same set the readiness evaluator considers (see _PLAN_APPROVED_OR_LATER).
        state_implies_approved = state_value.strip().upper() in {
            "PLAN_APPROVED",
            "IMPLEMENTATION_REVIEW_NEEDED",
            "IMPLEMENTATION_FIX_REQUIRED",
            "IMPLEMENTATION_APPROVED",
            "TEST_COMPLETE",
        }

    if has_plan_approved_marker or state_implies_approved:
        return {"status": "passed", "detail": "Human plan approval present."}

    plan_status = (approval_plan or {}).get("approval_status") if approval_plan else None
    if plan_status == "approved":
        return {"status": "passed", "detail": "Plan approval recorded."}
    if plan_status == "rejected":
        return {"status": "failed", "detail": "Plan approval was rejected."}
    # This belongs to Eligibility, not Readiness. Readiness must never
    # surface this message as a blocker — see
    # ``tools/agent_runner/ticket_readiness_evaluator.py`` (the
    # ``_is_entry_prerequisite_reason`` guard would drop it).
    return {"status": "failed", "detail": "Human plan approval required"}


# ── Mapping helpers ──────────────────────────────────────────────────────────

def _next_action_for(blocking_step: str, checks: dict) -> str | None:
    if blocking_step == "intelligence":
        return "Run Ticket Intelligence analysis"
    if blocking_step == "dependencies":
        unmet = checks["dependencies"].get("unmet") or []
        if unmet:
            return f"Wait for {unmet[0]} to be merged"
        return "Resolve dependency state"
    if blocking_step == "readiness":
        return "Run readiness evaluation and resolve blockers"
    if blocking_step == "approval":
        return "Approve plan review"
    return None


def _status_for(blocking_step: str | None, all_unknown: bool) -> str:
    if blocking_step is None:
        return "READY_TO_TAKE"
    if all_unknown:
        return "UNKNOWN"
    if blocking_step == "dependencies":
        return "DEPENDENCY_BLOCKED"
    if blocking_step == "approval":
        return "WAITING_HUMAN_ACTION"
    return "BLOCKED"


# ── Public entry point ──────────────────────────────────────────────────────

def evaluate_eligibility(
    db_path,
    project_root: Path,
    ticket_id: str,
    *,
    ticket_content: str | None = None,
    project_id: str | None = None,  # noqa: ARG001 — accepted for future use
) -> dict:
    """Return the aggregated execution-eligibility payload for ``ticket_id``.

    Pure read: never writes to the DB. Inputs are read from the existing
    Intelligence/Readiness/Approval tables plus the ticket's runtime
    ``state.json``. The first failing check (in ``CHECK_ORDER``) becomes the
    ``blocking_step``.
    """
    project_root = Path(project_root)

    intelligence = _safe_get(runtime_db.get_ticket_intelligence, db_path, ticket_id)
    readiness = _safe_get(runtime_db.get_ticket_readiness, db_path, ticket_id)
    approval_plan = _safe_get(runtime_db.get_latest_ticket_approval, db_path, ticket_id, "plan")

    state_value = None
    state_path = project_root / "runs" / ticket_id / "state.json"
    if state_path.is_file():
        try:
            import json as _json
            data = _json.loads(state_path.read_text(encoding="utf-8"))
            state_value = data.get("state")
        except (OSError, ValueError):
            state_value = None

    has_plan_approved_marker = (
        project_root / "runs" / ticket_id / "plan-approved.md"
    ).is_file()

    checks: dict[str, dict] = {
        "intelligence": _eval_intelligence(intelligence),
        "dependencies": _eval_dependencies(ticket_content, project_root),
        "readiness": _eval_readiness(readiness),
        "approval": _eval_approval(
            intelligence,
            approval_plan,
            state_value,
            has_plan_approved_marker,
        ),
    }

    blocking_step: str | None = None
    for key in CHECK_ORDER:
        if checks[key]["status"] in {"failed", "pending"}:
            blocking_step = key
            break

    all_unknown = all(c["status"] == "unknown" for c in checks.values())

    status = _status_for(blocking_step, all_unknown)
    ready_to_take = blocking_step is None and not all_unknown

    reason: str | None
    next_action: str | None
    if ready_to_take:
        reason = "All eligibility checks passed."
        next_action = "Ticket can be taken by a worker"
    elif all_unknown:
        reason = "No eligibility signals available."
        next_action = "Run intelligence and readiness analyses"
    else:
        reason = checks[blocking_step]["detail"]
        next_action = _next_action_for(blocking_step, checks)

    return {
        "ticket_id": ticket_id,
        "ready_to_take": ready_to_take,
        "status": status,
        "reason": reason,
        "next_action": next_action,
        "blocking_step": blocking_step,
        "checks": checks,
        "evaluated_at": _now_iso(),
    }
