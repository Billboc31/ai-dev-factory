"""Tests for the backlog batch lifecycle (T218)."""

from __future__ import annotations

import datetime
import importlib.util
import os
import sys
from pathlib import Path

import pytest

_TOOLS = Path(__file__).parent.parent / "tools" / "agent_runner"
sys.path.insert(0, str(_TOOLS))


def _load_sqlite_runtime_db():
    spec = importlib.util.spec_from_file_location(
        "_runtime_db_sqlite_test_backlog",
        _TOOLS / "runtime_db.py",
    )
    mod = importlib.util.module_from_spec(spec)
    old = os.environ.get("RUNTIME_DB_BACKEND")
    os.environ["RUNTIME_DB_BACKEND"] = "sqlite"
    try:
        spec.loader.exec_module(mod)
    finally:
        if old is None:
            os.environ.pop("RUNTIME_DB_BACKEND", None)
        else:
            os.environ["RUNTIME_DB_BACKEND"] = old
    return mod


_db = _load_sqlite_runtime_db()


def _load_backlog_batch():
    mod_name = "_backlog_batch_under_test"
    spec = importlib.util.spec_from_file_location(mod_name, _TOOLS / "backlog_batch.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)
    mod.runtime_db = _db
    return mod


bb = _load_backlog_batch()


@pytest.fixture()
def db(tmp_path: Path) -> Path:
    path = tmp_path / ".runtime" / "backlog.sqlite"
    _db.init_runtime_db(path)
    return path


def _iso(dt: datetime.datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def test_batch_status_does_not_contain_pending_collecting():
    values = {member.value for member in bb.BatchStatus}
    assert "pending_collecting" not in values
    assert values == {
        "collecting",
        "frozen",
        "dependency_analysis_running",
        "dependency_analysis_failed",
        "readiness_running",
        "dispatching",
        "completed",
    }


def test_get_or_create_collecting_batch_creates_new(db):
    batch_id = bb.get_or_create_collecting_batch(
        db, allow_parallel_batches=False,
    )
    row = _db.get_backlog_batch(db, batch_id)
    assert row["status"] == "collecting"
    assert row["freeze_blocked"] == 0


def test_add_ticket_to_batch_is_idempotent(db):
    batch_id = bb.get_or_create_collecting_batch(db, allow_parallel_batches=True)
    assert bb.add_ticket_to_batch(db, batch_id, "T001") is True
    assert bb.add_ticket_to_batch(db, batch_id, "T001") is False
    members = bb.list_batch_tickets(db, batch_id)
    assert members == ["T001"]


def test_add_ticket_unique_across_batches(db):
    b1 = bb.get_or_create_collecting_batch(db, allow_parallel_batches=True)
    bb.add_ticket_to_batch(db, b1, "T001")
    # Force a second batch by transitioning B1 out of collecting then asking
    # for a new collecting batch.
    bb.transition_batch(db, b1, "collecting", "frozen")
    b2 = bb.get_or_create_collecting_batch(db, allow_parallel_batches=True)
    assert b2 != b1
    inserted = bb.add_ticket_to_batch(db, b2, "T001")
    assert inserted is False  # UNIQUE(ticket_id) holds across batches


def test_idle_freeze_after_timeout(db):
    base = datetime.datetime(2026, 6, 30, 12, 0, 0, tzinfo=datetime.timezone.utc)
    now = _iso(base)
    batch_id = bb.get_or_create_collecting_batch(
        db, allow_parallel_batches=True, now=now,
    )
    bb.add_ticket_to_batch(db, batch_id, "T001", now=now)

    later = _iso(base + datetime.timedelta(minutes=5))
    frozen = bb.try_freeze_idle_batches(
        db, idle_timeout_minutes=10, max_batch_size=50, now=later,
    )
    assert frozen == []

    much_later = _iso(base + datetime.timedelta(minutes=15))
    frozen = bb.try_freeze_idle_batches(
        db, idle_timeout_minutes=10, max_batch_size=50, now=much_later,
    )
    assert frozen == [batch_id]
    row = _db.get_backlog_batch(db, batch_id)
    assert row["status"] == "frozen"


def test_size_triggers_immediate_freeze(db):
    base = datetime.datetime(2026, 6, 30, 12, 0, 0, tzinfo=datetime.timezone.utc)
    now = _iso(base)
    batch_id = bb.get_or_create_collecting_batch(
        db, allow_parallel_batches=True, now=now,
    )
    for n in range(3):
        bb.add_ticket_to_batch(db, batch_id, f"T00{n}", now=now)

    frozen = bb.try_freeze_idle_batches(
        db, idle_timeout_minutes=60, max_batch_size=3, now=now,
    )
    assert frozen == [batch_id]


def test_allow_parallel_batches_false_blocks_freezing(db):
    """While Batch A is dispatching, Batch B stays collecting + freeze_blocked."""
    base = datetime.datetime(2026, 6, 30, 12, 0, 0, tzinfo=datetime.timezone.utc)
    t0 = _iso(base)
    a = bb.get_or_create_collecting_batch(db, allow_parallel_batches=False, now=t0)
    bb.add_ticket_to_batch(db, a, "T100", now=t0)

    # Drive A through to dispatching.
    bb.transition_batch(db, a, "collecting", "frozen")
    bb.mark_dependency_analysis_attempt_started(db, a)
    bb.mark_dependency_analysis_succeeded(db, a)
    bb.transition_batch(db, a, "readiness_running", "dispatching")

    # New ticket discovered while A is dispatching.
    t1 = _iso(base + datetime.timedelta(minutes=1))
    b = bb.get_or_create_collecting_batch(
        db, allow_parallel_batches=False, now=t1,
    )
    assert b != a
    bb.add_ticket_to_batch(db, b, "T200", now=t1)
    row_b = _db.get_backlog_batch(db, b)
    assert row_b["freeze_blocked"] == 1
    assert row_b["freeze_blocked_reason"] == "prior_batch_dispatching"

    # Even after the idle timeout, B is NOT frozen.
    t2 = _iso(base + datetime.timedelta(minutes=60))
    assert bb.try_freeze_idle_batches(
        db, idle_timeout_minutes=10, max_batch_size=50, now=t2,
    ) == []
    row_b = _db.get_backlog_batch(db, b)
    assert row_b["status"] == "collecting"

    # Complete A → B becomes eligible.
    bb.transition_batch(db, a, "dispatching", "completed")
    cleared = bb.unblock_freezing_for_pending_collecting_batches(db)
    assert cleared == [b]
    row_b = _db.get_backlog_batch(db, b)
    assert row_b["freeze_blocked"] == 0

    t3 = _iso(base + datetime.timedelta(minutes=80))
    frozen = bb.try_freeze_idle_batches(
        db, idle_timeout_minutes=10, max_batch_size=50, now=t3,
    )
    assert frozen == [b]


def test_dependency_analysis_failure_records_retry(db):
    base = datetime.datetime(2026, 6, 30, 12, 0, 0, tzinfo=datetime.timezone.utc)
    now = _iso(base)
    batch_id = bb.get_or_create_collecting_batch(
        db, allow_parallel_batches=True, now=now,
    )
    bb.add_ticket_to_batch(db, batch_id, "T001", now=now)
    bb.transition_batch(db, batch_id, "collecting", "frozen")
    bb.mark_dependency_analysis_attempt_started(db, batch_id, now=now)

    result = bb.mark_dependency_analysis_failed(
        db, batch_id,
        error="bad json",
        cooldown_minutes=5,
        max_attempts=3,
        now=now,
    )
    assert result["attempts"] == 1
    assert result["exhausted"] is False
    assert result["next_retry_at"] is not None

    row = _db.get_backlog_batch(db, batch_id)
    assert row["status"] == "dependency_analysis_failed"
    assert row["last_dependency_analysis_error"] == "bad json"

    # Before cooldown elapses, the batch is not eligible to retry.
    eligible = bb.pick_batches_ready_for_dependency_analysis(
        db, now=now, max_attempts=3,
    )
    assert batch_id not in eligible

    # After cooldown the batch is eligible again.
    later = _iso(base + datetime.timedelta(minutes=10))
    eligible = bb.pick_batches_ready_for_dependency_analysis(
        db, now=later, max_attempts=3,
    )
    assert eligible == [batch_id]


def test_dependency_analysis_exhausted_terminal(db):
    base = datetime.datetime(2026, 6, 30, 12, 0, 0, tzinfo=datetime.timezone.utc)
    now = _iso(base)
    batch_id = bb.get_or_create_collecting_batch(
        db, allow_parallel_batches=True, now=now,
    )
    bb.add_ticket_to_batch(db, batch_id, "T001", now=now)
    bb.transition_batch(db, batch_id, "collecting", "frozen")

    for _ in range(3):
        bb.mark_dependency_analysis_attempt_started(db, batch_id, now=now)
        result = bb.mark_dependency_analysis_failed(
            db, batch_id,
            error="boom",
            cooldown_minutes=5,
            max_attempts=3,
            now=now,
        )

    assert result["attempts"] == 3
    assert result["exhausted"] is True
    assert result["next_retry_at"] is None

    # Even way after the would-be cooldown, the exhausted batch is not picked.
    much_later = _iso(base + datetime.timedelta(hours=24))
    assert bb.pick_batches_ready_for_dependency_analysis(
        db, now=much_later, max_attempts=3,
    ) == []


def test_transition_guard_rejects_wrong_source(db):
    batch_id = bb.get_or_create_collecting_batch(db, allow_parallel_batches=True)
    with pytest.raises(bb.BatchTransitionError):
        bb.transition_batch(db, batch_id, "frozen", "dispatching")


def test_get_batch_status_returns_dict(db):
    batch_id = bb.get_or_create_collecting_batch(db, allow_parallel_batches=True)
    bb.add_ticket_to_batch(db, batch_id, "T001")
    info = bb.get_batch_status(db, batch_id)
    assert info["status"] == "collecting"
    assert info["ticket_count"] == 1
    assert info["attempts"] == 0
