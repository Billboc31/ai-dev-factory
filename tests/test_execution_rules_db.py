"""Persistence tests for project_execution_rules and ticket_rule_evaluation (T201)."""

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
        "_runtime_db_sqlite_test_rules",
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


@pytest.fixture()
def db(tmp_path: Path) -> Path:
    db_path = tmp_path / ".runtime" / "test.sqlite"
    _db.init_runtime_db(db_path)
    return db_path


def test_schema_creates_project_execution_rules(db: Path) -> None:
    import sqlite3
    with sqlite3.connect(str(db)) as conn:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='project_execution_rules'"
        ).fetchone()
    assert row is not None


def test_schema_creates_ticket_rule_evaluation(db: Path) -> None:
    import sqlite3
    with sqlite3.connect(str(db)) as conn:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='ticket_rule_evaluation'"
        ).fetchone()
    assert row is not None


def test_list_project_rules_empty(db: Path) -> None:
    assert _db.list_project_rules(db, "proj-a") == []


def test_upsert_project_rule_round_trip(db: Path) -> None:
    _db.upsert_project_rule(
        db, "proj-a", "max_estimated_cost_usd", True, {"max_cost_usd": 0.75}
    )
    rules = _db.list_project_rules(db, "proj-a")
    assert len(rules) == 1
    assert rules[0]["rule_key"] == "max_estimated_cost_usd"
    assert rules[0]["enabled"] is True
    assert rules[0]["configuration"] == {"max_cost_usd": 0.75}


def test_upsert_project_rule_updates_existing(db: Path) -> None:
    _db.upsert_project_rule(db, "proj-a", "max_difficulty", True, {"max_difficulty": 5})
    _db.upsert_project_rule(db, "proj-a", "max_difficulty", False, {"max_difficulty": 9})
    rules = _db.list_project_rules(db, "proj-a")
    assert len(rules) == 1
    assert rules[0]["enabled"] is False
    assert rules[0]["configuration"] == {"max_difficulty": 9}


def test_list_project_rules_isolated_by_project(db: Path) -> None:
    _db.upsert_project_rule(db, "proj-a", "require_human_approval", True, {})
    _db.upsert_project_rule(db, "proj-b", "max_difficulty", True, {"max_difficulty": 3})
    a = _db.list_project_rules(db, "proj-a")
    b = _db.list_project_rules(db, "proj-b")
    assert [r["rule_key"] for r in a] == ["require_human_approval"]
    assert [r["rule_key"] for r in b] == ["max_difficulty"]


def test_replace_project_rules_overwrites_set(db: Path) -> None:
    _db.upsert_project_rule(db, "proj-a", "require_human_approval", True, {})
    _db.upsert_project_rule(db, "proj-a", "max_difficulty", True, {"max_difficulty": 5})
    _db.replace_project_rules(
        db,
        "proj-a",
        [
            {"rule_key": "require_ticket_intelligence", "enabled": True, "configuration": {}},
            {"rule_key": "max_estimated_cost_usd", "enabled": False, "configuration": {"max_cost_usd": 0.5}},
        ],
    )
    rules = _db.list_project_rules(db, "proj-a")
    keys = sorted(r["rule_key"] for r in rules)
    assert keys == ["max_estimated_cost_usd", "require_ticket_intelligence"]


def test_get_ticket_rule_evaluation_returns_none_when_absent(db: Path) -> None:
    assert _db.get_ticket_rule_evaluation(db, "T999") is None


def test_upsert_ticket_rule_evaluation_round_trip(db: Path) -> None:
    _db.upsert_ticket_rule_evaluation(
        db,
        ticket_id="T001",
        project_id="proj-a",
        eligibility_status="blocked",
        passed_rules=[{"rule_key": "require_ticket_intelligence", "reason": "ok"}],
        failed_rules=[{"rule_key": "require_human_approval", "reason": "missing approval"}],
        warnings=[{"rule_key": "max_estimated_cost_usd", "message": "no cost data"}],
        evaluated_at="2026-01-01T00:00:00Z",
    )
    row = _db.get_ticket_rule_evaluation(db, "T001")
    assert row is not None
    assert row["ticket_id"] == "T001"
    assert row["project_id"] == "proj-a"
    assert row["eligibility_status"] == "blocked"
    assert row["passed_rules_json"] == [
        {"rule_key": "require_ticket_intelligence", "reason": "ok"}
    ]
    assert row["failed_rules_json"] == [
        {"rule_key": "require_human_approval", "reason": "missing approval"}
    ]
    assert row["warnings_json"] == [
        {"rule_key": "max_estimated_cost_usd", "message": "no cost data"}
    ]
    assert row["evaluated_at"] == "2026-01-01T00:00:00Z"


def test_upsert_ticket_rule_evaluation_overwrites(db: Path) -> None:
    _db.upsert_ticket_rule_evaluation(
        db,
        ticket_id="T001",
        project_id="proj-a",
        eligibility_status="blocked",
        passed_rules=[],
        failed_rules=[{"rule_key": "require_human_approval", "reason": "no approval"}],
        warnings=[],
        evaluated_at="2026-01-01T00:00:00Z",
    )
    _db.upsert_ticket_rule_evaluation(
        db,
        ticket_id="T001",
        project_id="proj-a",
        eligibility_status="eligible",
        passed_rules=[{"rule_key": "require_human_approval", "reason": "ok"}],
        failed_rules=[],
        warnings=[],
        evaluated_at="2026-01-02T00:00:00Z",
    )
    row = _db.get_ticket_rule_evaluation(db, "T001")
    assert row["eligibility_status"] == "eligible"
    assert row["failed_rules_json"] == []
    assert row["evaluated_at"] == "2026-01-02T00:00:00Z"

    import sqlite3
    with sqlite3.connect(str(db)) as conn:
        rows = conn.execute(
            "SELECT * FROM ticket_rule_evaluation WHERE ticket_id = 'T001'"
        ).fetchall()
    assert len(rows) == 1


def test_json_columns_deserialise_to_lists(db: Path) -> None:
    _db.upsert_ticket_rule_evaluation(
        db,
        ticket_id="T010",
        project_id="proj-a",
        eligibility_status="eligible",
        passed_rules=[],
        failed_rules=[],
        warnings=[],
        evaluated_at="2026-01-01T00:00:00Z",
    )
    row = _db.get_ticket_rule_evaluation(db, "T010")
    assert isinstance(row["passed_rules_json"], list)
    assert isinstance(row["failed_rules_json"], list)
    assert isinstance(row["warnings_json"], list)


# ── Postgres backend mirrors the public API (no live server required) ────────

def test_postgres_backend_exports_same_helpers():
    """The PG module must mirror the public helper API used by the engine/route."""
    import runtime_db_pg as pg
    for name in (
        "list_project_rules",
        "upsert_project_rule",
        "replace_project_rules",
        "get_ticket_rule_evaluation",
        "upsert_ticket_rule_evaluation",
    ):
        assert callable(getattr(pg, name)), f"runtime_db_pg.{name} is missing"


def test_postgres_ddl_creates_required_tables():
    """The PG DDL declares both T201 tables with the documented columns."""
    import runtime_db_pg as pg
    ddl = pg._DDL
    assert "CREATE TABLE IF NOT EXISTS project_execution_rules" in ddl
    assert "CREATE TABLE IF NOT EXISTS ticket_rule_evaluation" in ddl
    # required columns
    for col in (
        "project_id",
        "rule_key",
        "enabled",
        "configuration_json",
    ):
        assert col in ddl
    for col in (
        "ticket_id",
        "eligibility_status",
        "failed_rules_json",
        "passed_rules_json",
        "warnings_json",
        "evaluated_at",
    ):
        assert col in ddl
