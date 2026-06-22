"""Tests for ticket_diagnostics DB persistence (T203)."""

import importlib.util
import os
import sys
from pathlib import Path

import pytest

_TOOLS = Path(__file__).parent.parent / "tools" / "agent_runner"
sys.path.insert(0, str(_TOOLS))


def _load_sqlite_runtime_db():
    """Load runtime_db as a fresh SQLite-mode module, bypassing any env rebinding."""
    spec = importlib.util.spec_from_file_location(
        "_runtime_db_sqlite_test_diagnostics",
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
init_runtime_db = _db.init_runtime_db
upsert_ticket_diagnostics = _db.upsert_ticket_diagnostics
get_ticket_diagnostics = _db.get_ticket_diagnostics


@pytest.fixture()
def db(tmp_path: Path) -> Path:
    db_path = tmp_path / ".runtime" / "test.sqlite"
    init_runtime_db(db_path)
    return db_path


def test_schema_created(db: Path) -> None:
    import sqlite3
    with sqlite3.connect(str(db)) as conn:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='ticket_diagnostics'"
        ).fetchone()
    assert row is not None


def test_get_returns_none_when_absent(db: Path) -> None:
    assert get_ticket_diagnostics(db, "T999") is None


def test_round_trip_basic_row(db: Path) -> None:
    upsert_ticket_diagnostics(
        db,
        "T203",
        project_id="proj1",
        diagnostic_status="completed",
        is_stuck=1,
        severity="warning",
        summary="Ticket is waiting for human approval.",
        current_state="WAITING_APPROVAL",
        last_known_step="plan_review",
        last_error=None,
        checks_json=[{"key": "approval", "status": "failed", "message": "missing", "details": {}}],
        recommended_actions_json=[
            {"action_key": "approve_execution", "label": "Approve", "risk": "low", "reason": "x"}
        ],
    )
    row = get_ticket_diagnostics(db, "T203")
    assert row is not None
    assert row["ticket_id"] == "T203"
    assert row["project_id"] == "proj1"
    assert row["is_stuck"] == 1
    assert row["severity"] == "warning"
    assert row["summary"] == "Ticket is waiting for human approval."
    assert row["current_state"] == "WAITING_APPROVAL"
    assert row["last_known_step"] == "plan_review"
    assert row["checks_json"] == [
        {"key": "approval", "status": "failed", "message": "missing", "details": {}}
    ]
    assert row["recommended_actions_json"] == [
        {"action_key": "approve_execution", "label": "Approve", "risk": "low", "reason": "x"}
    ]
    assert row["generated_at"] is not None
    assert row["created_at"] is not None


def test_created_at_preserved_across_updates(db: Path) -> None:
    upsert_ticket_diagnostics(db, "T001", severity="info")
    first = get_ticket_diagnostics(db, "T001")
    assert first is not None
    created = first["created_at"]
    upsert_ticket_diagnostics(db, "T001", severity="warning", summary="changed")
    second = get_ticket_diagnostics(db, "T001")
    assert second is not None
    assert second["created_at"] == created
    assert second["severity"] == "warning"
    assert second["summary"] == "changed"


def test_lists_default_to_empty(db: Path) -> None:
    upsert_ticket_diagnostics(db, "T010")
    row = get_ticket_diagnostics(db, "T010")
    assert row is not None
    assert row["checks_json"] == []
    assert row["recommended_actions_json"] == []


def test_multiple_tickets_isolated(db: Path) -> None:
    upsert_ticket_diagnostics(db, "T001", severity="info", summary="A")
    upsert_ticket_diagnostics(db, "T002", severity="error", summary="B")
    r1 = get_ticket_diagnostics(db, "T001")
    r2 = get_ticket_diagnostics(db, "T002")
    assert r1 is not None and r2 is not None
    assert r1["summary"] == "A"
    assert r2["summary"] == "B"
    assert r1["severity"] == "info"
    assert r2["severity"] == "error"


def test_upsert_does_not_duplicate(db: Path) -> None:
    upsert_ticket_diagnostics(db, "T001", severity="info")
    upsert_ticket_diagnostics(db, "T001", severity="warning")
    import sqlite3
    with sqlite3.connect(str(db)) as conn:
        rows = conn.execute(
            "SELECT * FROM ticket_diagnostics WHERE ticket_id = 'T001'"
        ).fetchall()
    assert len(rows) == 1
