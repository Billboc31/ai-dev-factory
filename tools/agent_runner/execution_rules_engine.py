"""Execution Rules Engine.

Evaluates configurable project policies against a single ticket and emits an
``eligible`` or ``blocked`` decision with explicit per-rule reasons. The engine
is advisory: it never starts execution, reserves workers, or reorders queues.

The engine reads the human-approval lifecycle only through
``get_execution_approval_state``, which wraps
``ticket_approval_service.compute_execution_eligibility``. The module MUST NOT
reference ``ticket_approvals`` or ``approval_status`` directly (a static test
in the suite enforces this).
"""

from __future__ import annotations

import datetime
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

_TOOLS_DIR = Path(__file__).resolve().parent
if str(_TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(_TOOLS_DIR))

import runtime_db  # noqa: E402


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class RuleContext:
    """Inputs available to a rule evaluator."""

    project_id: str
    ticket_id: str
    configuration: dict
    intelligence: dict | None
    readiness: dict | None
    approval_state: str


@dataclass
class RuleResult:
    """Result of evaluating a single rule."""

    passed: bool
    reason: str
    warnings: list[str] = field(default_factory=list)


@dataclass
class RuleSpec:
    """Static specification of a rule registered in the engine."""

    key: str
    description: str
    default_enabled: bool
    default_configuration: dict
    evaluator: Callable[[RuleContext], RuleResult]


# ── Rule evaluators ──────────────────────────────────────────────────────────

def _rule_require_ticket_intelligence(ctx: RuleContext) -> RuleResult:
    if not ctx.intelligence:
        return RuleResult(
            passed=False,
            reason="Ticket Intelligence analysis is missing.",
        )
    status = ctx.intelligence.get("analysis_status")
    if status != "completed":
        return RuleResult(
            passed=False,
            reason=f"Ticket Intelligence analysis_status is '{status}', expected 'completed'.",
        )
    return RuleResult(passed=True, reason="Ticket Intelligence analysis is completed.")


_READY_STATES = frozenset({"ready_candidate", "ready_to_take"})


def _rule_require_readiness_candidate(ctx: RuleContext) -> RuleResult:
    if not ctx.readiness:
        return RuleResult(
            passed=False,
            reason="Readiness evaluation is missing.",
        )
    status = ctx.readiness.get("readiness_status")
    if status not in _READY_STATES:
        return RuleResult(
            passed=False,
            reason=f"Readiness status is '{status}', expected 'ready_candidate' or a later state.",
        )
    return RuleResult(passed=True, reason=f"Readiness status is '{status}'.")


def _rule_require_human_approval(ctx: RuleContext) -> RuleResult:
    if ctx.approval_state == "ready_to_take":
        return RuleResult(
            passed=True,
            reason="Human execution approval is present (ready_to_take).",
        )
    return RuleResult(
        passed=False,
        reason=(
            f"Human execution approval is missing (approval_state='{ctx.approval_state}', "
            "expected 'ready_to_take')."
        ),
    )


def _rule_block_when_human_review_required(ctx: RuleContext) -> RuleResult:
    flag = bool((ctx.intelligence or {}).get("requires_human_plan_review"))
    if not flag:
        return RuleResult(
            passed=True,
            reason="Ticket Intelligence does not require human plan review.",
        )
    if ctx.approval_state == "ready_to_take":
        return RuleResult(
            passed=True,
            reason="Human plan review required, and human execution approval is present.",
        )
    return RuleResult(
        passed=False,
        reason=(
            "Ticket Intelligence flags requires_human_plan_review=true but human "
            f"execution approval is missing (approval_state='{ctx.approval_state}')."
        ),
    )


def _rule_max_estimated_cost_usd(ctx: RuleContext) -> RuleResult:
    limit = ctx.configuration.get("max_cost_usd")
    intel = ctx.intelligence or {}
    estimated = intel.get("estimated_cost_max")
    if estimated is None:
        estimated = intel.get("estimated_cost_min")
    if limit is None:
        return RuleResult(
            passed=True,
            reason="No max_cost_usd configured.",
        )
    if estimated is None:
        return RuleResult(
            passed=True,
            reason="No estimated AI cost available; treating as below the limit.",
            warnings=["Estimated AI cost is unknown; cost threshold cannot be enforced."],
        )
    try:
        est_f = float(estimated)
        lim_f = float(limit)
    except (TypeError, ValueError):
        return RuleResult(
            passed=True,
            reason="Cost values are not numeric; cannot enforce threshold.",
            warnings=["Cost threshold could not be parsed."],
        )
    if est_f > lim_f:
        return RuleResult(
            passed=False,
            reason=f"Estimated AI cost ${est_f:.2f} exceeds limit ${lim_f:.2f}.",
        )
    return RuleResult(
        passed=True,
        reason=f"Estimated AI cost ${est_f:.2f} is within limit ${lim_f:.2f}.",
    )


def _rule_max_difficulty(ctx: RuleContext) -> RuleResult:
    limit = ctx.configuration.get("max_difficulty")
    score = (ctx.intelligence or {}).get("difficulty_score")
    if limit is None:
        return RuleResult(
            passed=True,
            reason="No max_difficulty configured.",
        )
    if score is None:
        return RuleResult(
            passed=True,
            reason="No difficulty score available; treating as below the limit.",
            warnings=["Difficulty score is unknown; difficulty threshold cannot be enforced."],
        )
    try:
        score_i = int(score)
        lim_i = int(limit)
    except (TypeError, ValueError):
        return RuleResult(
            passed=True,
            reason="Difficulty values are not numeric; cannot enforce threshold.",
            warnings=["Difficulty threshold could not be parsed."],
        )
    if score_i > lim_i:
        return RuleResult(
            passed=False,
            reason=f"Difficulty score {score_i} exceeds limit {lim_i}.",
        )
    return RuleResult(
        passed=True,
        reason=f"Difficulty score {score_i} is within limit {lim_i}.",
    )


# ── Registry ─────────────────────────────────────────────────────────────────

RULE_REGISTRY: dict[str, RuleSpec] = {
    "require_ticket_intelligence": RuleSpec(
        key="require_ticket_intelligence",
        description="Ticket Intelligence analysis must be completed.",
        default_enabled=True,
        default_configuration={},
        evaluator=_rule_require_ticket_intelligence,
    ),
    "require_readiness_candidate": RuleSpec(
        key="require_readiness_candidate",
        description="Ticket must be at least readiness 'ready_candidate'.",
        default_enabled=True,
        default_configuration={},
        evaluator=_rule_require_readiness_candidate,
    ),
    "require_human_approval": RuleSpec(
        key="require_human_approval",
        description="Human execution approval must be present (ready_to_take).",
        default_enabled=True,
        default_configuration={},
        evaluator=_rule_require_human_approval,
    ),
    "block_when_human_review_required": RuleSpec(
        key="block_when_human_review_required",
        description=(
            "Block tickets flagged requires_human_plan_review until human "
            "execution approval is granted."
        ),
        default_enabled=True,
        default_configuration={},
        evaluator=_rule_block_when_human_review_required,
    ),
    "max_estimated_cost_usd": RuleSpec(
        key="max_estimated_cost_usd",
        description="Block tickets whose estimated AI cost exceeds max_cost_usd.",
        default_enabled=False,
        default_configuration={"max_cost_usd": 0.50},
        evaluator=_rule_max_estimated_cost_usd,
    ),
    "max_difficulty": RuleSpec(
        key="max_difficulty",
        description="Block tickets whose difficulty score exceeds max_difficulty.",
        default_enabled=False,
        default_configuration={"max_difficulty": 7},
        evaluator=_rule_max_difficulty,
    ),
}


# ── Approval bridge ──────────────────────────────────────────────────────────
#
# IMPORTANT: this wrapper is the SOLE bridge between the engine and the
# canonical human-execution-eligibility lifecycle exposed by
# ticket_approval_service.compute_execution_eligibility. Rule evaluators read
# the resulting string from RuleContext.approval_state. The engine module does
# not reference the underlying approval table or its status column directly.

def get_execution_approval_state(db_path, ticket_id: str) -> str:
    """Return the canonical execution eligibility string for a ticket."""
    import ticket_approval_service  # local import keeps the bridge explicit
    return ticket_approval_service.compute_execution_eligibility(db_path, ticket_id)


# ── Default policy resolution ────────────────────────────────────────────────

def _resolve_effective_rules(
    project_id: str, db_path
) -> list[dict]:
    """Return the effective set of rules for a project (stored ∪ registry defaults)."""
    stored_rows = runtime_db.list_project_rules(db_path, project_id)
    stored_by_key = {row["rule_key"]: row for row in stored_rows}

    effective: list[dict] = []
    for key, spec in RULE_REGISTRY.items():
        if key in stored_by_key:
            row = stored_by_key[key]
            effective.append(
                {
                    "rule_key": key,
                    "enabled": bool(row.get("enabled")),
                    "configuration": row.get("configuration") or {},
                }
            )
        else:
            effective.append(
                {
                    "rule_key": key,
                    "enabled": spec.default_enabled,
                    "configuration": dict(spec.default_configuration),
                }
            )
    return effective


def get_registry_default_rules() -> list[dict]:
    """Return the registry default rules serialised for storage."""
    return [
        {
            "rule_key": spec.key,
            "enabled": spec.default_enabled,
            "configuration": dict(spec.default_configuration),
        }
        for spec in RULE_REGISTRY.values()
    ]


# ── Evaluation ───────────────────────────────────────────────────────────────

def evaluate_ticket(db_path, project_id: str, ticket_id: str) -> dict:
    """Evaluate every enabled rule and persist the resulting decision."""
    intelligence = runtime_db.get_ticket_intelligence(db_path, ticket_id)
    readiness = runtime_db.get_ticket_readiness(db_path, ticket_id)
    approval_state = get_execution_approval_state(db_path, ticket_id)

    effective_rules = _resolve_effective_rules(project_id, db_path)

    passed_rules: list[dict] = []
    failed_rules: list[dict] = []
    warnings: list[dict] = []

    for rule in effective_rules:
        if not rule["enabled"]:
            continue
        spec = RULE_REGISTRY.get(rule["rule_key"])
        if spec is None:
            continue
        ctx = RuleContext(
            project_id=project_id,
            ticket_id=ticket_id,
            configuration=rule.get("configuration") or {},
            intelligence=intelligence,
            readiness=readiness,
            approval_state=approval_state,
        )
        result = spec.evaluator(ctx)
        entry = {"rule_key": rule["rule_key"], "reason": result.reason}
        if result.passed:
            passed_rules.append(entry)
        else:
            failed_rules.append(entry)
        for warn in result.warnings or []:
            warnings.append({"rule_key": rule["rule_key"], "message": warn})

    eligibility_status = "blocked" if failed_rules else "eligible"
    evaluated_at = _now_iso()

    runtime_db.upsert_ticket_rule_evaluation(
        db_path,
        ticket_id,
        project_id,
        eligibility_status,
        passed_rules,
        failed_rules,
        warnings,
        evaluated_at,
    )

    return {
        "eligibility_status": eligibility_status,
        "passed_rules": passed_rules,
        "failed_rules": failed_rules,
        "warnings": warnings,
        "evaluated_at": evaluated_at,
    }
