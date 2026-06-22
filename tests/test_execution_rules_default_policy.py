"""Default policy tests for the Execution Rules Engine (T201)."""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest

_TOOLS = Path(__file__).parent.parent / "tools" / "agent_runner"
sys.path.insert(0, str(_TOOLS))


def _load_sqlite_runtime_db():
    spec = importlib.util.spec_from_file_location(
        "_runtime_db_sqlite_test_default_policy",
        _TOOLS / "runtime_db.py",
    )
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    old = os.environ.get("RUNTIME_DB_BACKEND")
    os.environ["RUNTIME_DB_BACKEND"] = "sqlite"
    try:
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
    finally:
        if old is None:
            os.environ.pop("RUNTIME_DB_BACKEND", None)
        else:
            os.environ["RUNTIME_DB_BACKEND"] = old
    return mod


_db = _load_sqlite_runtime_db()

import execution_rules_engine as engine  # noqa: E402


def test_registry_default_rules_match_expected_policy() -> None:
    defaults = {r["rule_key"]: r for r in engine.get_registry_default_rules()}

    assert defaults["require_ticket_intelligence"]["enabled"] is True
    assert defaults["require_readiness_candidate"]["enabled"] is True
    assert defaults["require_human_approval"]["enabled"] is True
    assert defaults["block_when_human_review_required"]["enabled"] is True

    assert defaults["max_estimated_cost_usd"]["enabled"] is False
    assert defaults["max_estimated_cost_usd"]["configuration"] == {"max_cost_usd": 0.50}
    assert defaults["max_difficulty"]["enabled"] is False
    assert defaults["max_difficulty"]["configuration"] == {"max_difficulty": 7}


@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    db_path = tmp_path / ".runtime" / "default_policy.sqlite"
    _db.init_runtime_db(db_path)

    import runtime_db as live_db
    for name in (
        "list_project_rules",
        "upsert_project_rule",
        "replace_project_rules",
        "get_ticket_rule_evaluation",
        "upsert_ticket_rule_evaluation",
        "get_ticket_intelligence",
        "get_ticket_readiness",
    ):
        monkeypatch.setattr(live_db, name, getattr(_db, name))
    return db_path


def test_default_policy_evaluation_with_eligible_ticket(db, monkeypatch):
    """Eligible when ticket satisfies all 4 default-enabled rules."""
    _db.upsert_ticket_intelligence(
        db, "T001", analysis_status="completed", requires_human_plan_review=0
    )
    _db.upsert_ticket_readiness(db, "T001", readiness_status="ready_to_take")
    monkeypatch.setattr(engine, "get_execution_approval_state", lambda _d, _t: "ready_to_take")

    assert _db.list_project_rules(db, "proj-a") == []

    result = engine.evaluate_ticket(db, "proj-a", "T001")
    assert result["eligibility_status"] == "eligible"
    passed_keys = {r["rule_key"] for r in result["passed_rules"]}

    # The 4 default-enabled rules must all be evaluated and pass.
    assert "require_ticket_intelligence" in passed_keys
    assert "require_readiness_candidate" in passed_keys
    assert "require_human_approval" in passed_keys
    assert "block_when_human_review_required" in passed_keys
    # The 2 threshold rules are disabled by default → never evaluated.
    assert "max_estimated_cost_usd" not in passed_keys
    assert "max_difficulty" not in passed_keys


def test_default_policy_blocks_when_intelligence_missing(db, monkeypatch):
    """When intelligence is missing, require_ticket_intelligence fails."""
    monkeypatch.setattr(engine, "get_execution_approval_state", lambda _d, _t: "not_started")

    result = engine.evaluate_ticket(db, "proj-a", "T002")
    assert result["eligibility_status"] == "blocked"
    failed_keys = {r["rule_key"] for r in result["failed_rules"]}
    assert "require_ticket_intelligence" in failed_keys


def test_default_policy_disables_threshold_rules_even_with_cost_exceeded(db, monkeypatch):
    """Threshold rules are inert under default policy (disabled)."""
    _db.upsert_ticket_intelligence(
        db,
        "T003",
        analysis_status="completed",
        requires_human_plan_review=0,
        estimated_cost_max=10.0,
        difficulty_score=10,
    )
    _db.upsert_ticket_readiness(db, "T003", readiness_status="ready_to_take")
    monkeypatch.setattr(engine, "get_execution_approval_state", lambda _d, _t: "ready_to_take")

    result = engine.evaluate_ticket(db, "proj-a", "T003")
    assert result["eligibility_status"] == "eligible"
    failed_keys = {r["rule_key"] for r in result["failed_rules"]}
    assert "max_estimated_cost_usd" not in failed_keys
    assert "max_difficulty" not in failed_keys


def test_enabled_threshold_rule_blocks(db, monkeypatch):
    _db.upsert_ticket_intelligence(
        db,
        "T004",
        analysis_status="completed",
        requires_human_plan_review=0,
        estimated_cost_max=2.50,
    )
    _db.upsert_ticket_readiness(db, "T004", readiness_status="ready_to_take")
    monkeypatch.setattr(engine, "get_execution_approval_state", lambda _d, _t: "ready_to_take")

    _db.upsert_project_rule(
        db, "proj-a", "max_estimated_cost_usd", True, {"max_cost_usd": 1.00}
    )

    result = engine.evaluate_ticket(db, "proj-a", "T004")
    assert result["eligibility_status"] == "blocked"
    failed_keys = {r["rule_key"] for r in result["failed_rules"]}
    assert "max_estimated_cost_usd" in failed_keys
