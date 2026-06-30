"""Ticket Execution Eligibility Service.

Read-only aggregator that produces a single ``READY_TO_TAKE`` decision for a
ticket by combining the existing — and intentionally untouched — Intelligence,
Readiness, Approval and dependency systems.

The service never writes to the runtime DB and never touches the scheduler or
worker. It returns a structured payload that the API and UI can consume
directly. The first failing check (in a fixed order) becomes the
``blocking_step``; the status is derived from which step failed.

Check order: intelligence → dependencies → readiness → approval.

The ``approval`` step gates on **human execution approval** (the Human Approval
panel / ``ticket_approvals`` type ``execution``) when the project rule
``require_human_approval`` is enabled (or the global
``REQUIRE_HUMAN_EXECUTION_APPROVAL`` setting when no ``project_id`` is
available). Plan review during development (``PLAN_REVIEW_NEEDED``) is never
checked here — that gate lives in the ``run_ticket`` state machine.
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
from ticket_readiness_evaluator import _extract_dependencies, collect_dependency_ticket_ids  # noqa: E402

_EXECUTION_APPROVAL_RULE = "require_human_approval"


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


def _eval_dependencies(
    ticket_content: str | None,
    project_root: Path,
    *,
    project_id: str | None = None,
    repo: str | None = None,
    intelligence: dict | None = None,
) -> dict:
    deps = collect_dependency_ticket_ids(ticket_content or "", intelligence)
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
            result = is_ticket_merged(
                project_root, dep, project_id=project_id, repo=None
            )
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


def _is_human_execution_approval_required(db_path, project_id: str | None) -> bool:
    """Return whether the Human Approval gate must yield ``ready_to_take``."""
    try:
        from execution_rules_engine import RULE_REGISTRY, _resolve_effective_rules  # noqa: WPS433

        if project_id:
            for rule in _resolve_effective_rules(project_id, db_path):
                if rule["rule_key"] == _EXECUTION_APPROVAL_RULE:
                    return bool(rule["enabled"])
            spec = RULE_REGISTRY.get(_EXECUTION_APPROVAL_RULE)
            return bool(spec.default_enabled) if spec else False
    except Exception:
        pass

    try:
        import runtime_settings as rs  # noqa: WPS433

        return bool(rs.get_setting(db_path, "REQUIRE_HUMAN_EXECUTION_APPROVAL"))
    except Exception:
        return False


def _eval_approval(
    db_path,
    ticket_id: str,
    project_id: str | None,
) -> dict:
    """Gate on human **execution** approval when the project policy requires it."""
    if not _is_human_execution_approval_required(db_path, project_id):
        return {
            "status": "passed",
            "detail": "Human execution approval gate is disabled.",
        }

    from execution_rules_engine import get_execution_approval_state  # noqa: WPS433

    approval_state = get_execution_approval_state(db_path, ticket_id)
    if approval_state == "ready_to_take":
        return {
            "status": "passed",
            "detail": "Human execution approval granted.",
        }
    if approval_state == "blocked":
        return {
            "status": "failed",
            "detail": "Human execution approval was rejected.",
        }
    return {
        "status": "failed",
        "detail": "Human execution approval required",
    }


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
        return "Approve ticket for execution"
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
    project_id: str | None = None,
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

    checks: dict[str, dict] = {
        "intelligence": _eval_intelligence(intelligence),
        "dependencies": _eval_dependencies(
            ticket_content,
            project_root,
            project_id=project_id,
            intelligence=intelligence,
        ),
        "readiness": _eval_readiness(readiness),
        "approval": _eval_approval(db_path, ticket_id, project_id),
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
