"""Tests for ticket_readiness DB persistence (T198)."""

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
        "_runtime_db_sqlite_test_readiness",
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
upsert_ticket_readiness = _db.upsert_ticket_readiness
get_ticket_readiness = _db.get_ticket_readiness


@pytest.fixture()
def db(tmp_path: Path) -> Path:
    db_path = tmp_path / ".runtime" / "test.sqlite"
    init_runtime_db(db_path)
    return db_path


def test_schema_created(db: Path) -> None:
    """The ticket_readiness table must exist after init_runtime_db."""
    import sqlite3
    with sqlite3.connect(str(db)) as conn:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='ticket_readiness'"
        ).fetchone()
    assert row is not None


def test_default_status_on_insert(db: Path) -> None:
    upsert_ticket_readiness(db, "T100")
    row = get_ticket_readiness(db, "T100")
    assert row is not None
    assert row["readiness_status"] == "not_started"
    assert row["ready_candidate"] == 0
    # List columns decoded to [] when absent.
    assert row["blocking_reasons_json"] == []
    assert row["warnings_json"] == []


def test_upsert_insert_and_get(db: Path) -> None:
    upsert_ticket_readiness(db, "T001", readiness_status="queued")
    row = get_ticket_readiness(db, "T001")
    assert row is not None
    assert row["ticket_id"] == "T001"
    assert row["readiness_status"] == "queued"
    assert row["ready_candidate"] == 0


def test_get_returns_none_when_absent(db: Path) -> None:
    assert get_ticket_readiness(db, "T999") is None


def test_round_trip_json_list_fields(db: Path) -> None:
    upsert_ticket_readiness(
        db,
        "T001",
        readiness_status="blocked",
        blocking_reasons_json=["Dependency T010 not merged", "Missing Ticket Intelligence analysis"],
        warnings_json=["context freshness unknown"],
    )
    row = get_ticket_readiness(db, "T001")
    assert row is not None
    assert row["blocking_reasons_json"] == [
        "Dependency T010 not merged",
        "Missing Ticket Intelligence analysis",
    ]
    assert row["warnings_json"] == ["context freshness unknown"]


def test_upsert_update_does_not_duplicate(db: Path) -> None:
    upsert_ticket_readiness(db, "T001", readiness_status="queued")
    upsert_ticket_readiness(
        db,
        "T001",
        readiness_status="ready_candidate",
        ready_candidate=1,
        blocking_reasons_json=[],
    )
    row = get_ticket_readiness(db, "T001")
    assert row is not None
    assert row["readiness_status"] == "ready_candidate"
    assert row["ready_candidate"] == 1
    assert row["blocking_reasons_json"] == []

    import sqlite3
    with sqlite3.connect(str(db)) as conn:
        rows = conn.execute(
            "SELECT * FROM ticket_readiness WHERE ticket_id = 'T001'"
        ).fetchall()
    assert len(rows) == 1


def test_created_at_preserved_across_updates(db: Path) -> None:
    upsert_ticket_readiness(db, "T001", readiness_status="queued")
    first = get_ticket_readiness(db, "T001")
    created = first["created_at"]
    upsert_ticket_readiness(db, "T001", readiness_status="running")
    second = get_ticket_readiness(db, "T001")
    assert second["created_at"] == created


def test_all_fields_round_trip(db: Path) -> None:
    upsert_ticket_readiness(
        db,
        "T001",
        readiness_status="ready_candidate",
        ready_candidate=1,
        blocking_reasons_json=[],
        warnings_json=[],
        dependency_check_status="passed",
        approval_check_status="passed",
        context_freshness_status="fresh",
        human_approval_required=1,
        human_approval_present=1,
        main_sha_when_evaluated="deadbeef",
        evaluated_at="2025-01-01T00:00:00Z",
    )
    row = get_ticket_readiness(db, "T001")
    assert row["ready_candidate"] == 1
    assert row["dependency_check_status"] == "passed"
    assert row["approval_check_status"] == "passed"
    assert row["context_freshness_status"] == "fresh"
    assert row["human_approval_required"] == 1
    assert row["human_approval_present"] == 1
    assert row["main_sha_when_evaluated"] == "deadbeef"
    assert row["evaluated_at"] == "2025-01-01T00:00:00Z"


def test_multiple_tickets_isolated(db: Path) -> None:
    upsert_ticket_readiness(db, "T001", readiness_status="ready_candidate", ready_candidate=1)
    upsert_ticket_readiness(
        db,
        "T002",
        readiness_status="blocked",
        blocking_reasons_json=["Dependency T001 not merged"],
    )
    r1 = get_ticket_readiness(db, "T001")
    r2 = get_ticket_readiness(db, "T002")
    assert r1["readiness_status"] == "ready_candidate"
    assert r2["readiness_status"] == "blocked"
    assert r2["blocking_reasons_json"] == ["Dependency T001 not merged"]
