"""Tests for execution_rules_engine — one pass/fail case per rule (T201)."""

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
        "_runtime_db_sqlite_test_rules_engine",
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


def _ctx(**kwargs):
    base = dict(
        project_id="proj-a",
        ticket_id="T001",
        configuration={},
        intelligence=None,
        readiness=None,
        approval_state="not_started",
    )
    base.update(kwargs)
    return engine.RuleContext(**base)


# ── require_ticket_intelligence ─────────────────────────────────────────────

def test_require_ticket_intelligence_passes_when_completed():
    spec = engine.RULE_REGISTRY["require_ticket_intelligence"]
    res = spec.evaluator(_ctx(intelligence={"analysis_status": "completed"}))
    assert res.passed is True
    assert "completed" in res.reason


def test_require_ticket_intelligence_fails_when_missing():
    spec = engine.RULE_REGISTRY["require_ticket_intelligence"]
    res = spec.evaluator(_ctx(intelligence=None))
    assert res.passed is False
    assert "missing" in res.reason.lower()


# ── require_readiness_candidate ─────────────────────────────────────────────

def test_require_readiness_passes_when_ready_candidate():
    spec = engine.RULE_REGISTRY["require_readiness_candidate"]
    res = spec.evaluator(_ctx(readiness={"readiness_status": "ready_candidate"}))
    assert res.passed is True


def test_require_readiness_passes_when_ready_to_take():
    spec = engine.RULE_REGISTRY["require_readiness_candidate"]
    res = spec.evaluator(_ctx(readiness={"readiness_status": "ready_to_take"}))
    assert res.passed is True


def test_require_readiness_fails_when_blocked():
    spec = engine.RULE_REGISTRY["require_readiness_candidate"]
    res = spec.evaluator(_ctx(readiness={"readiness_status": "blocked"}))
    assert res.passed is False
    assert "blocked" in res.reason


# ── require_human_approval (driven by approval_state ONLY) ──────────────────

def test_require_human_approval_passes_when_ready_to_take():
    spec = engine.RULE_REGISTRY["require_human_approval"]
    res = spec.evaluator(_ctx(approval_state="ready_to_take"))
    assert res.passed is True
    assert "approval" in res.reason.lower()


def test_require_human_approval_fails_when_ready_candidate():
    spec = engine.RULE_REGISTRY["require_human_approval"]
    res = spec.evaluator(_ctx(approval_state="ready_candidate"))
    assert res.passed is False
    assert "ready_candidate" in res.reason


# ── block_when_human_review_required (deprecated no-op) ─────────────────────

def test_block_when_human_review_always_passes():
    spec = engine.RULE_REGISTRY["block_when_human_review_required"]
    res = spec.evaluator(
        _ctx(
            intelligence={"requires_human_plan_review": True},
            approval_state="ready_candidate",
        )
    )
    assert res.passed is True
    assert "PLAN_REVIEW_NEEDED" in res.reason


# ── max_estimated_cost_usd ───────────────────────────────────────────────────

def test_max_estimated_cost_passes_when_under_limit():
    spec = engine.RULE_REGISTRY["max_estimated_cost_usd"]
    res = spec.evaluator(
        _ctx(
            configuration={"max_cost_usd": 0.50},
            intelligence={"estimated_cost_max": 0.25},
        )
    )
    assert res.passed is True


def test_max_estimated_cost_fails_when_over_limit():
    spec = engine.RULE_REGISTRY["max_estimated_cost_usd"]
    res = spec.evaluator(
        _ctx(
            configuration={"max_cost_usd": 0.50},
            intelligence={"estimated_cost_max": 1.20},
        )
    )
    assert res.passed is False
    assert "exceeds" in res.reason


def test_max_estimated_cost_passes_with_unknown_cost_but_warns():
    spec = engine.RULE_REGISTRY["max_estimated_cost_usd"]
    res = spec.evaluator(
        _ctx(
            configuration={"max_cost_usd": 0.50},
            intelligence={},
        )
    )
    assert res.passed is True
    assert res.warnings  # warning produced when no cost available


def test_max_estimated_cost_passes_when_disabled_via_no_config():
    # When no max_cost_usd configured, the rule should always pass.
    spec = engine.RULE_REGISTRY["max_estimated_cost_usd"]
    res = spec.evaluator(
        _ctx(
            configuration={},
            intelligence={"estimated_cost_max": 9.99},
        )
    )
    assert res.passed is True


# ── max_difficulty ──────────────────────────────────────────────────────────

def test_max_difficulty_passes_when_under_limit():
    spec = engine.RULE_REGISTRY["max_difficulty"]
    res = spec.evaluator(
        _ctx(
            configuration={"max_difficulty": 7},
            intelligence={"difficulty_score": 5},
        )
    )
    assert res.passed is True


def test_max_difficulty_fails_when_over_limit():
    spec = engine.RULE_REGISTRY["max_difficulty"]
    res = spec.evaluator(
        _ctx(
            configuration={"max_difficulty": 5},
            intelligence={"difficulty_score": 9},
        )
    )
    assert res.passed is False
    assert "exceeds" in res.reason


def test_max_difficulty_passes_when_no_config_set():
    spec = engine.RULE_REGISTRY["max_difficulty"]
    res = spec.evaluator(
        _ctx(
            configuration={},
            intelligence={"difficulty_score": 10},
        )
    )
    assert res.passed is True


# ── Integration via evaluate_ticket ─────────────────────────────────────────

@pytest.fixture()
def db(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    db_path = tmp_path / ".runtime" / "engine.sqlite"
    _db.init_runtime_db(db_path)

    import runtime_db as live_db
    monkeypatch.setattr(live_db, "list_project_rules", _db.list_project_rules)
    monkeypatch.setattr(live_db, "upsert_project_rule", _db.upsert_project_rule)
    monkeypatch.setattr(live_db, "replace_project_rules", _db.replace_project_rules)
    monkeypatch.setattr(
        live_db, "get_ticket_rule_evaluation", _db.get_ticket_rule_evaluation
    )
    monkeypatch.setattr(
        live_db, "upsert_ticket_rule_evaluation", _db.upsert_ticket_rule_evaluation
    )
    monkeypatch.setattr(live_db, "get_ticket_intelligence", _db.get_ticket_intelligence)
    monkeypatch.setattr(live_db, "get_ticket_readiness", _db.get_ticket_readiness)
    return db_path


def test_evaluate_ticket_blocked_when_rule_fails(db, monkeypatch):
    _db.upsert_ticket_intelligence(db, "T001", analysis_status="completed")
    _db.upsert_ticket_readiness(db, "T001", readiness_status="ready_candidate")
    _db.upsert_project_rule(db, "proj-a", "require_human_approval", True, {})
    monkeypatch.setattr(engine, "get_execution_approval_state", lambda _db_path, _t: "ready_candidate")

    result = engine.evaluate_ticket(db, "proj-a", "T001")
    assert result["eligibility_status"] == "blocked"
    failed_keys = [r["rule_key"] for r in result["failed_rules"]]
    assert "require_human_approval" in failed_keys


def test_evaluate_ticket_eligible_when_all_pass(db, monkeypatch):
    _db.upsert_ticket_intelligence(
        db, "T002", analysis_status="completed", requires_human_plan_review=0
    )
    _db.upsert_ticket_readiness(db, "T002", readiness_status="ready_to_take")
    monkeypatch.setattr(engine, "get_execution_approval_state", lambda _db_path, _t: "ready_to_take")

    result = engine.evaluate_ticket(db, "proj-a", "T002")
    assert result["eligibility_status"] == "eligible"
    assert result["failed_rules"] == []
    persisted = _db.get_ticket_rule_evaluation(db, "T002")
    assert persisted["eligibility_status"] == "eligible"
    assert persisted["project_id"] == "proj-a"
