"""Integration tests for the Execution Rules API endpoints (T201)."""

from __future__ import annotations

import importlib.util
import json
import sys
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "agent_runner"))


def _load_sqlite_db_module():
    import os as _os
    spec = importlib.util.spec_from_file_location(
        "_api_rules_runtime_db_sqlite",
        Path(__file__).resolve().parents[1] / "tools" / "agent_runner" / "runtime_db.py",
    )
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    saved = _os.environ.get("RUNTIME_DB_BACKEND")
    _os.environ["RUNTIME_DB_BACKEND"] = "sqlite"
    try:
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
    finally:
        if saved is None:
            _os.environ.pop("RUNTIME_DB_BACKEND", None)
        else:
            _os.environ["RUNTIME_DB_BACKEND"] = saved
    return mod


_sqlite_db = _load_sqlite_db_module()


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)


def _make_app(tmp_path: Path):
    from services.control_api.main import create_app
    import services.control_api.routes.rules as _rules_route

    app = create_app(project_root=tmp_path)
    isolated_db = tmp_path / ".runtime" / "adf-test-rules.sqlite"
    _sqlite_db.init_runtime_db(isolated_db)
    app.state.db_path = isolated_db

    _rules_route.runtime_db = _sqlite_db
    return app


def _make_ticket(tmp_path: Path, ticket_id: str) -> None:
    run_dir = tmp_path / "runs" / ticket_id
    run_dir.mkdir(parents=True)
    (run_dir / "state.json").write_text(
        json.dumps({"ticket_id": ticket_id, "state": "PLAN_APPROVED", "branch": f"ticket/{ticket_id}"}),
        encoding="utf-8",
    )
    (run_dir / "ticket.md").write_text(f"# {ticket_id}\n", encoding="utf-8")


# ── GET /projects/{id}/rules ────────────────────────────────────────────────

def test_get_rules_returns_registry_defaults_when_empty(tmp_path):
    (tmp_path / "runs").mkdir()
    client = TestClient(_make_app(tmp_path))
    r = client.get("/projects/proj-a/rules")
    assert r.status_code == 200
    body = r.json()
    assert body["project_id"] == "proj-a"
    keys = {rule["rule_key"] for rule in body["rules"]}
    assert keys == {
        "require_ticket_intelligence",
        "require_readiness_candidate",
        "require_human_approval",
        "block_when_human_review_required",
        "max_estimated_cost_usd",
        "max_difficulty",
    }
    defaults_enabled = {
        rule["rule_key"]: rule["enabled"] for rule in body["rules"]
    }
    assert defaults_enabled["require_ticket_intelligence"] is True
    assert defaults_enabled["require_readiness_candidate"] is True
    assert defaults_enabled["require_human_approval"] is True
    assert defaults_enabled["block_when_human_review_required"] is True
    assert defaults_enabled["max_estimated_cost_usd"] is False
    assert defaults_enabled["max_difficulty"] is False


def test_get_rules_merges_stored_with_defaults(tmp_path):
    (tmp_path / "runs").mkdir()
    app = _make_app(tmp_path)
    _sqlite_db.upsert_project_rule(
        app.state.db_path, "proj-a", "max_difficulty", True, {"max_difficulty": 4}
    )
    client = TestClient(app)
    r = client.get("/projects/proj-a/rules")
    assert r.status_code == 200
    by_key = {rule["rule_key"]: rule for rule in r.json()["rules"]}
    assert by_key["max_difficulty"]["enabled"] is True
    assert by_key["max_difficulty"]["configuration"] == {"max_difficulty": 4}
    # The unset rules still come back at registry defaults.
    assert by_key["max_estimated_cost_usd"]["enabled"] is False


# ── PUT /projects/{id}/rules ────────────────────────────────────────────────

def test_put_rules_replaces_set(tmp_path):
    (tmp_path / "runs").mkdir()
    client = TestClient(_make_app(tmp_path))
    payload = {
        "rules": [
            {"rule_key": "max_difficulty", "enabled": True, "configuration": {"max_difficulty": 3}},
            {"rule_key": "max_estimated_cost_usd", "enabled": True, "configuration": {"max_cost_usd": 0.10}},
            {"rule_key": "require_ticket_intelligence", "enabled": False, "configuration": {}},
            {"rule_key": "require_readiness_candidate", "enabled": True, "configuration": {}},
            {"rule_key": "require_human_approval", "enabled": True, "configuration": {}},
            {"rule_key": "block_when_human_review_required", "enabled": True, "configuration": {}},
        ]
    }
    r = client.put("/projects/proj-a/rules", json=payload)
    assert r.status_code == 200
    by_key = {rule["rule_key"]: rule for rule in r.json()["rules"]}
    assert by_key["max_difficulty"]["enabled"] is True
    assert by_key["max_difficulty"]["configuration"] == {"max_difficulty": 3}
    assert by_key["require_ticket_intelligence"]["enabled"] is False


def test_put_rules_unknown_key_rejected(tmp_path):
    (tmp_path / "runs").mkdir()
    client = TestClient(_make_app(tmp_path))
    r = client.put(
        "/projects/proj-a/rules",
        json={"rules": [{"rule_key": "does_not_exist", "enabled": True, "configuration": {}}]},
    )
    assert r.status_code == 422


def test_put_rules_rejects_negative_cost(tmp_path):
    (tmp_path / "runs").mkdir()
    client = TestClient(_make_app(tmp_path))
    r = client.put(
        "/projects/proj-a/rules",
        json={"rules": [{"rule_key": "max_estimated_cost_usd", "enabled": True, "configuration": {"max_cost_usd": -1}}]},
    )
    assert r.status_code == 422


def test_put_rules_reset_defaults_via_action(tmp_path):
    (tmp_path / "runs").mkdir()
    app = _make_app(tmp_path)
    _sqlite_db.upsert_project_rule(
        app.state.db_path, "proj-a", "max_difficulty", True, {"max_difficulty": 1}
    )
    client = TestClient(app)
    r = client.put("/projects/proj-a/rules", json={"action": "reset_defaults"})
    assert r.status_code == 200
    by_key = {rule["rule_key"]: rule for rule in r.json()["rules"]}
    # Registry defaults restored.
    assert by_key["max_difficulty"]["enabled"] is False
    assert by_key["max_difficulty"]["configuration"] == {"max_difficulty": 7}


# ── GET /tickets/{id}/rule-evaluation ───────────────────────────────────────

def test_get_rule_evaluation_404_when_missing(tmp_path):
    _make_ticket(tmp_path, "T001")
    client = TestClient(_make_app(tmp_path))
    r = client.get("/tickets/T001/rule-evaluation")
    assert r.status_code == 404


def test_get_rule_evaluation_returns_persisted_row(tmp_path):
    _make_ticket(tmp_path, "T001")
    app = _make_app(tmp_path)
    _sqlite_db.upsert_ticket_rule_evaluation(
        app.state.db_path,
        ticket_id="T001",
        project_id="proj-a",
        eligibility_status="blocked",
        passed_rules=[],
        failed_rules=[{"rule_key": "require_human_approval", "reason": "missing"}],
        warnings=[],
        evaluated_at="2026-01-01T00:00:00Z",
    )
    client = TestClient(app)
    r = client.get("/tickets/T001/rule-evaluation")
    assert r.status_code == 200
    body = r.json()
    assert body["eligibility_status"] == "blocked"
    assert body["failed_rules"] == [
        {"rule_key": "require_human_approval", "reason": "missing"}
    ]


# ── POST /tickets/{id}/evaluate-rules ───────────────────────────────────────

def test_evaluate_returns_202_and_schedules(tmp_path, monkeypatch):
    _make_ticket(tmp_path, "T001")
    app = _make_app(tmp_path)
    db = app.state.db_path

    _sqlite_db.upsert_ticket_intelligence(
        db, "T001", analysis_status="completed", requires_human_plan_review=0
    )
    _sqlite_db.upsert_ticket_readiness(db, "T001", readiness_status="ready_to_take")

    import execution_rules_engine as engine
    monkeypatch.setattr(engine, "get_execution_approval_state", lambda _d, _t: "ready_to_take")

    # Wire engine through the SQLite DB module for upsert/get.
    monkeypatch.setattr(engine.runtime_db, "list_project_rules", _sqlite_db.list_project_rules)
    monkeypatch.setattr(engine.runtime_db, "get_ticket_intelligence", _sqlite_db.get_ticket_intelligence)
    monkeypatch.setattr(engine.runtime_db, "get_ticket_readiness", _sqlite_db.get_ticket_readiness)
    monkeypatch.setattr(
        engine.runtime_db, "upsert_ticket_rule_evaluation", _sqlite_db.upsert_ticket_rule_evaluation
    )

    client = TestClient(app)
    r = client.post("/projects/proj-a/tickets/T001/evaluate-rules")
    assert r.status_code == 202
    body = r.json()
    assert body["status"] == "scheduled"
    assert body["ticket_id"] == "T001"

    # TestClient runs background tasks synchronously after the response.
    persisted = _sqlite_db.get_ticket_rule_evaluation(db, "T001")
    assert persisted is not None
    assert persisted["eligibility_status"] == "eligible"
    assert persisted["project_id"] == "proj-a"


def test_evaluate_404_when_ticket_missing(tmp_path):
    (tmp_path / "runs").mkdir()
    client = TestClient(_make_app(tmp_path))
    r = client.post("/tickets/T999/evaluate-rules")
    assert r.status_code == 404


# ── Project-scoped GET ─────────────────────────────────────────────────────

def test_project_scoped_get_rule_evaluation(tmp_path):
    _make_ticket(tmp_path, "T001")
    app = _make_app(tmp_path)
    _sqlite_db.upsert_ticket_rule_evaluation(
        app.state.db_path,
        ticket_id="T001",
        project_id="proj-a",
        eligibility_status="eligible",
        passed_rules=[{"rule_key": "require_human_approval", "reason": "ok"}],
        failed_rules=[],
        warnings=[],
        evaluated_at="2026-01-01T00:00:00Z",
    )
    client = TestClient(app)
    r = client.get("/projects/proj-a/tickets/T001/rule-evaluation")
    assert r.status_code == 200
    assert r.json()["eligibility_status"] == "eligible"
