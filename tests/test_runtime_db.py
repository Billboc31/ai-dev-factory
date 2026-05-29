"""Tests for T111 — runtime_db SQLite module."""

import sqlite3
import sys
import threading
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "tools" / "agent_runner"))

from runtime_db import (
    _connect,
    append_runtime_event,
    check_and_recover_db,
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


# ── check_and_recover_db ──────────────────────────────────────────────────────

def test_check_and_recover_db_healthy_db(tmp_path: Path) -> None:
    """Healthy DB passes check unchanged — no quarantine file is created."""
    db_path = tmp_path / ".runtime" / "ai-dev-factory.sqlite"
    init_runtime_db(db_path)
    record_issue_intake(db_path, 1, "T001")

    result = check_and_recover_db(db_path)

    assert result is True
    assert db_path.exists()
    # No quarantine file should exist
    corrupt_files = list(db_path.parent.glob("*.corrupt.*"))
    assert corrupt_files == []
    # Original data still readable
    assert get_issue_intake(db_path, 1) is not None


def test_check_and_recover_db_corrupt_db_quarantined(tmp_path: Path) -> None:
    """Corrupt DB is quarantined and a fresh empty DB is recreated."""
    db_path = tmp_path / ".runtime" / "ai-dev-factory.sqlite"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    # Write garbage so SQLite sees a malformed file
    db_path.write_bytes(b"SQLite format 3\x00" + b"\xff" * 512)

    result = check_and_recover_db(db_path)

    assert result is True
    # Quarantine file exists
    corrupt_files = list(db_path.parent.glob("*.corrupt.*"))
    assert len(corrupt_files) == 1
    # A new empty DB was recreated
    assert db_path.exists()
    # New DB is usable
    record_issue_intake(db_path, 99, "T099")
    assert get_issue_intake(db_path, 99) is not None


def test_check_and_recover_db_lock_serialization(tmp_path: Path) -> None:
    """Concurrent callers are serialized — second caller waits for first to finish."""
    db_path = tmp_path / ".runtime" / "ai-dev-factory.sqlite"
    init_runtime_db(db_path)

    results: list[bool] = []
    errors: list[Exception] = []

    def run():
        try:
            results.append(check_and_recover_db(db_path))
        except Exception as exc:
            errors.append(exc)

    threads = [threading.Thread(target=run) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)

    assert errors == [], f"threads raised: {errors}"
    assert len(results) == 4
    assert all(r is True for r in results)


def test_check_and_recover_db_pragmas(tmp_path: Path) -> None:
    """busy_timeout and synchronous=NORMAL pragmas are applied by _connect()."""
    db_path = tmp_path / ".runtime" / "ai-dev-factory.sqlite"
    init_runtime_db(db_path)

    # PRAGMA values are connection-level — must use _connect() to see them applied
    conn = _connect(db_path)
    try:
        (busy_timeout,) = conn.execute("PRAGMA busy_timeout").fetchone()
        (synchronous,) = conn.execute("PRAGMA synchronous").fetchone()
    finally:
        conn.close()

    assert busy_timeout == 5000
    # NORMAL = 1 in SQLite's numeric encoding
    assert synchronous == 1


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
