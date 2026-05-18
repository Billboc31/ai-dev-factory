"""Tests for T111 — runtime_db SQLite module."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "tools" / "agent_runner"))

from runtime_db import (
    append_runtime_event,
    get_issue_intake,
    get_ticket_runtime,
    init_runtime_db,
    list_issue_intake,
    list_runtime_events,
    list_ticket_runtime,
    list_workers,
    record_issue_intake,
    remove_worker,
    upsert_ticket_runtime,
    upsert_worker,
)


# ── fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture()
def db(tmp_path: Path) -> Path:
    """Return a fresh, initialised DB path for each test."""
    db_path = tmp_path / ".runtime" / "test.sqlite"
    init_runtime_db(db_path)
    return db_path


# ── init ──────────────────────────────────────────────────────────────────────

def test_init_creates_db_file(tmp_path: Path) -> None:
    db_path = tmp_path / ".runtime" / "ai-dev-factory.sqlite"
    assert not db_path.exists()
    init_runtime_db(db_path)
    assert db_path.exists()


def test_init_is_idempotent(tmp_path: Path) -> None:
    db_path = tmp_path / ".runtime" / "ai-dev-factory.sqlite"
    init_runtime_db(db_path)
    init_runtime_db(db_path)  # second call must not raise
    assert db_path.exists()


# ── issue_intake ──────────────────────────────────────────────────────────────

def test_record_issue_intake_insert(db: Path) -> None:
    record_issue_intake(db, 42, "T042", branch="ticket/T042-foo")
    row = get_issue_intake(db, 42)
    assert row is not None
    assert row["issue_number"] == 42
    assert row["ticket_id"] == "T042"
    assert row["branch"] == "ticket/T042-foo"
    assert row["status"] == "ingested"


def test_record_issue_intake_update_on_conflict(db: Path) -> None:
    record_issue_intake(db, 42, "T042")
    record_issue_intake(db, 42, "T042-updated", branch="ticket/T042-bar")
    row = get_issue_intake(db, 42)
    assert row is not None
    assert row["ticket_id"] == "T042-updated"
    assert row["branch"] == "ticket/T042-bar"
    # Only one row — no duplicates
    assert len(list_issue_intake(db)) == 1


def test_list_issue_intake_multiple(db: Path) -> None:
    record_issue_intake(db, 10, "T010")
    record_issue_intake(db, 20, "T020")
    rows = list_issue_intake(db)
    assert len(rows) == 2
    assert rows[0]["issue_number"] == 10
    assert rows[1]["issue_number"] == 20


def test_get_issue_intake_returns_none_when_absent(db: Path) -> None:
    assert get_issue_intake(db, 999) is None


# ── ticket_runtime ────────────────────────────────────────────────────────────

def test_upsert_ticket_runtime_insert(db: Path) -> None:
    upsert_ticket_runtime(db, "T042", issue_number=42, branch="ticket/T042-foo", state="INIT")
    row = get_ticket_runtime(db, "T042")
    assert row is not None
    assert row["ticket_id"] == "T042"
    assert row["state"] == "INIT"
    assert row["issue_number"] == 42


def test_upsert_ticket_runtime_update(db: Path) -> None:
    upsert_ticket_runtime(db, "T042", state="INIT")
    upsert_ticket_runtime(db, "T042", state="PLAN_APPROVED")
    row = get_ticket_runtime(db, "T042")
    assert row is not None
    assert row["state"] == "PLAN_APPROVED"
    assert len(list_ticket_runtime(db)) == 1


def test_list_ticket_runtime(db: Path) -> None:
    upsert_ticket_runtime(db, "T001", state="INIT")
    upsert_ticket_runtime(db, "T002", state="PLAN_REVIEW_NEEDED")
    rows = list_ticket_runtime(db)
    assert len(rows) == 2
    assert rows[0]["ticket_id"] == "T001"


# ── workers ───────────────────────────────────────────────────────────────────

def test_upsert_and_remove_worker(db: Path) -> None:
    upsert_worker(db, "T042", pid=12345, branch="ticket/T042-foo", worktree_path="/wt/T042")
    workers = list_workers(db)
    assert len(workers) == 1
    assert workers[0]["pid"] == 12345
    assert workers[0]["status"] == "running"

    remove_worker(db, "T042")
    assert list_workers(db) == []


def test_upsert_worker_updates_existing(db: Path) -> None:
    upsert_worker(db, "T042", pid=100, branch="ticket/T042-foo", worktree_path="/wt/T042")
    upsert_worker(db, "T042", pid=200, branch="ticket/T042-foo", worktree_path="/wt/T042")
    workers = list_workers(db)
    assert len(workers) == 1
    assert workers[0]["pid"] == 200


def test_remove_worker_noop_when_absent(db: Path) -> None:
    remove_worker(db, "T999")  # must not raise


# ── runtime_events ────────────────────────────────────────────────────────────

def test_append_and_list_runtime_events(db: Path) -> None:
    append_runtime_event(db, "T042", "step_start", "Starting planner")
    append_runtime_event(db, "T042", "step_done", "Planner done", metadata={"rc": 0})
    append_runtime_event(db, "T043", "step_start", "Starting coder")

    all_events = list_runtime_events(db)
    assert len(all_events) == 3

    t042_events = list_runtime_events(db, ticket_id="T042")
    assert len(t042_events) == 2
    assert all(e["ticket_id"] == "T042" for e in t042_events)


def test_runtime_event_metadata_roundtrip(db: Path) -> None:
    meta = {"rc": 0, "step": "coder", "attempt": 2}
    append_runtime_event(db, "T042", "step_done", "done", metadata=meta)
    events = list_runtime_events(db, ticket_id="T042")
    import json
    stored = json.loads(events[0]["metadata_json"])
    assert stored == meta


# ── DB persistence ────────────────────────────────────────────────────────────

def test_db_survives_reconnect(tmp_path: Path) -> None:
    """Data must persist after closing all connections (simulates process restart)."""
    db_path = tmp_path / ".runtime" / "ai-dev-factory.sqlite"
    init_runtime_db(db_path)

    record_issue_intake(db_path, 99, "T099")
    upsert_ticket_runtime(db_path, "T099", state="INIT")
    upsert_worker(db_path, "T099", pid=9999, branch="ticket/T099-foo", worktree_path="/wt/T099")
    append_runtime_event(db_path, "T099", "test", "hello")

    # Re-open with a new connection (simulates fresh process)
    assert get_issue_intake(db_path, 99)["ticket_id"] == "T099"
    assert get_ticket_runtime(db_path, "T099")["state"] == "INIT"
    assert list_workers(db_path)[0]["pid"] == 9999
    assert list_runtime_events(db_path, ticket_id="T099")[0]["message"] == "hello"
