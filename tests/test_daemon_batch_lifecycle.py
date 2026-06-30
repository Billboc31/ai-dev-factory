"""End-to-end-ish lifecycle tests for backlog batches driven by the daemon (T218).

These tests do not spawn subprocesses or workers — they drive the lifecycle
helpers (``process_backlog_batches`` + the readiness/dispatcher gates)
directly and assert the observable state transitions.
"""

from __future__ import annotations

import datetime
import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest

_TOOLS = Path(__file__).parent.parent / "tools" / "agent_runner"
sys.path.insert(0, str(_TOOLS))


def _load_sqlite_runtime_db():
    name = "_runtime_db_sqlite_daemon_batch"
    spec = importlib.util.spec_from_file_location(name, _TOOLS / "runtime_db.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
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


def _load_module(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, _TOOLS / filename)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


bb = _load_module("_bb_for_lifecycle", "backlog_batch.py")
bb.runtime_db = _db

gda = _load_module("_gda_for_lifecycle", "global_dependency_analyzer.py")
gda.runtime_db = _db

dispatcher = _load_module("_dispatcher_for_lifecycle", "ticket_dispatcher.py")
dispatcher.runtime_db = _db
dispatcher._backlog_batch = bb

pipeline = _load_module("_pipeline_for_lifecycle", "ticket_pipeline.py")
pipeline.runtime_db = _db
pipeline._backlog_batch = bb


@pytest.fixture()
def db(tmp_path: Path) -> Path:
    path = tmp_path / ".runtime" / "lifecycle.sqlite"
    _db.init_runtime_db(path)
    return path


@pytest.fixture()
def runs_dir(tmp_path: Path) -> Path:
    d = tmp_path / "runs"
    d.mkdir()
    return d


def _iso(dt: datetime.datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _intake_ticket(db: Path, runs_dir: Path, ticket_id: str, *, now: str | None = None) -> str:
    """Simulate the daemon's intake step for one ticket."""
    run_dir = runs_dir / ticket_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "ticket.md").write_text(f"# {ticket_id}\n\nbody\n", encoding="utf-8")
    _db.upsert_ticket_runtime(db, ticket_id, state="INIT")
    batch_id = bb.get_or_create_collecting_batch(
        db, allow_parallel_batches=False, now=now,
    )
    bb.add_ticket_to_batch(db, batch_id, ticket_id, now=now)
    return batch_id


def test_pipeline_readiness_gated_on_batch(db, runs_dir):
    batch_id = _intake_ticket(db, runs_dir, "T001")
    _db.upsert_ticket_intelligence(db, "T001", analysis_status="completed")

    # While the batch is still collecting, readiness is gated off.
    next_id = pipeline.find_next_ticket(db, ["T001"])
    assert next_id is None

    # Move the batch through to readiness_running — pipeline picks it up.
    bb.transition_batch(db, batch_id, "collecting", "frozen")
    bb.mark_dependency_analysis_attempt_started(db, batch_id)
    bb.mark_dependency_analysis_succeeded(db, batch_id)

    next_id = pipeline.find_next_ticket(db, ["T001"])
    assert next_id == "T001"


def test_dispatcher_excludes_tickets_not_in_dispatching_batch(db, runs_dir, monkeypatch):
    _intake_ticket(db, runs_dir, "T001")
    _db.upsert_ticket_intelligence(db, "T001", analysis_status="completed", queue_rank=1)
    _db.upsert_ticket_readiness(db, "T001", readiness_status="ready_candidate")

    # Force eligibility to think the ticket is ready_to_take — without the
    # batch gate, the dispatcher would surface it.
    def _stub_eligibility(*_a, **_k):
        return {"ready_to_take": True, "status": "READY_TO_TAKE"}

    monkeypatch.setattr(dispatcher._eligibility, "evaluate_eligibility", _stub_eligibility)
    monkeypatch.setattr(dispatcher, "get_dispatcher_mode", lambda *_a, **_kw: "advisory")

    payload = dispatcher.get_recommended_tickets(db, runs_dir, mode="advisory")
    assert payload["recommendations"] == []

    # Now move the batch all the way to dispatching.
    batch_id = bb.get_batch_id_for_ticket(db, "T001")
    bb.transition_batch(db, batch_id, "collecting", "frozen")
    bb.mark_dependency_analysis_attempt_started(db, batch_id)
    bb.mark_dependency_analysis_succeeded(db, batch_id)
    bb.transition_batch(db, batch_id, "readiness_running", "dispatching")

    payload = dispatcher.get_recommended_tickets(db, runs_dir, mode="advisory")
    ticket_ids = [r["ticket_id"] for r in payload["recommendations"]]
    assert ticket_ids == ["T001"]


def test_ticket_arriving_during_dispatch_lands_in_blocked_batch(db, runs_dir):
    base = datetime.datetime(2026, 6, 30, 12, 0, 0, tzinfo=datetime.timezone.utc)
    t0 = _iso(base)
    _intake_ticket(db, runs_dir, "T001", now=t0)
    a = bb.get_batch_id_for_ticket(db, "T001")
    bb.transition_batch(db, a, "collecting", "frozen")
    bb.mark_dependency_analysis_attempt_started(db, a)
    bb.mark_dependency_analysis_succeeded(db, a)
    bb.transition_batch(db, a, "readiness_running", "dispatching")

    t1 = _iso(base + datetime.timedelta(minutes=1))
    _intake_ticket(db, runs_dir, "T002", now=t1)
    b = bb.get_batch_id_for_ticket(db, "T002")
    assert b != a
    row_b = _db.get_backlog_batch(db, b)
    assert row_b["freeze_blocked"] == 1


def test_retry_path_then_success(db, runs_dir, monkeypatch):
    """First analysis attempt fails, second one succeeds after cooldown."""
    base = datetime.datetime(2026, 6, 30, 12, 0, 0, tzinfo=datetime.timezone.utc)
    t0 = _iso(base)
    _intake_ticket(db, runs_dir, "T001", now=t0)
    batch_id = bb.get_batch_id_for_ticket(db, "T001")
    bb.transition_batch(db, batch_id, "collecting", "frozen")

    # First attempt: malformed JSON.
    bb.mark_dependency_analysis_attempt_started(db, batch_id, now=t0)
    result = bb.mark_dependency_analysis_failed(
        db, batch_id,
        error="malformed",
        cooldown_minutes=5,
        max_attempts=3,
        now=t0,
    )
    assert result["attempts"] == 1
    assert result["exhausted"] is False

    # Before cooldown, the batch is not picked.
    early = _iso(base + datetime.timedelta(minutes=2))
    assert bb.pick_batches_ready_for_dependency_analysis(
        db, now=early, max_attempts=3,
    ) == []

    # After cooldown, the batch is picked, the second attempt succeeds.
    later = _iso(base + datetime.timedelta(minutes=10))
    assert bb.pick_batches_ready_for_dependency_analysis(
        db, now=later, max_attempts=3,
    ) == [batch_id]
    bb.mark_dependency_analysis_attempt_started(db, batch_id, now=later)
    bb.mark_dependency_analysis_succeeded(db, batch_id)

    row = _db.get_backlog_batch(db, batch_id)
    assert row["status"] == "readiness_running"
    assert row["dependency_analysis_attempts"] == 2
    assert row["last_dependency_analysis_error"] is None


def test_max_attempts_emits_exhausted_event_once(db, runs_dir):
    base = datetime.datetime(2026, 6, 30, 12, 0, 0, tzinfo=datetime.timezone.utc)
    t0 = _iso(base)
    _intake_ticket(db, runs_dir, "T001", now=t0)
    batch_id = bb.get_batch_id_for_ticket(db, "T001")
    bb.transition_batch(db, batch_id, "collecting", "frozen")
    for _ in range(3):
        bb.mark_dependency_analysis_attempt_started(db, batch_id, now=t0)
        bb.mark_dependency_analysis_failed(
            db, batch_id,
            error="boom",
            cooldown_minutes=5,
            max_attempts=3,
            now=t0,
        )
    events = _db.list_runtime_events(db, limit=200)
    exhausted = [e for e in events if e["event_type"] == "batch.dependency_analysis_exhausted"]
    assert len(exhausted) == 1
