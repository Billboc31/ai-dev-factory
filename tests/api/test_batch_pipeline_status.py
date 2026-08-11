"""Tests for GET /{batch_id}/pipeline-status (T230)."""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(
    0, str(Path(__file__).resolve().parents[2] / "tools" / "agent_runner")
)


def _load_sqlite_db_module():
    spec = importlib.util.spec_from_file_location(
        "_api_pipeline_status_runtime_db_sqlite",
        Path(__file__).resolve().parents[2]
        / "tools"
        / "agent_runner"
        / "runtime_db.py",
    )
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    saved = os.environ.get("RUNTIME_DB_BACKEND")
    os.environ["RUNTIME_DB_BACKEND"] = "sqlite"
    try:
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
    finally:
        if saved is None:
            os.environ.pop("RUNTIME_DB_BACKEND", None)
        else:
            os.environ["RUNTIME_DB_BACKEND"] = saved
    return mod


_sqlite_db = _load_sqlite_db_module()


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch):
    monkeypatch.setenv("RUNTIME_DB_BACKEND", "sqlite")
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    monkeypatch.delenv("AI_DEV_FACTORY_DISPATCHER_MODE", raising=False)


def _make_app(tmp_path: Path):
    from services.control_api.main import create_app
    from services.control_api.services.project_registry import (
        ProjectEntry,
        ProjectRegistry,
    )

    app = create_app(project_root=tmp_path)
    isolated_db = tmp_path / ".runtime" / "adf-test-pipeline.sqlite"
    _sqlite_db.init_runtime_db(isolated_db)
    app.state.db_path = isolated_db
    app.state.project_registry = ProjectRegistry(
        _entries=[
            ProjectEntry(
                id="proj-a", root=tmp_path, project_runtime_root=tmp_path
            )
        ],
    )

    import runtime_db as live_db
    import backlog_batch as _bb
    import ticket_dispatcher as _disp
    from services.control_api.routes import batches as _batch_routes

    for name in (
        "list_backlog_batches",
        "get_backlog_batch",
        "list_backlog_batch_ticket_ids",
        "list_ticket_runtime",
        "get_ticket_runtime",
        "get_dependency_analysis",
        "get_ticket_readiness",
        "get_ticket_intelligence",
        "update_backlog_batch",
        "append_runtime_event",
        "get_batch_analysis_summary",
        "resolve_db_path_for_project",
    ):
        setattr(live_db, name, getattr(_sqlite_db, name))
    _bb.runtime_db = live_db
    _disp.runtime_db = live_db
    _batch_routes.runtime_db = live_db
    return app


def _seed_batch(db_path, batch_id: str, *, status: str = "frozen") -> None:
    _sqlite_db.insert_backlog_batch(
        db_path,
        batch_id,
        status=status,
        created_at="2026-07-01T10:00:00Z",
        last_activity_at="2026-07-01T10:00:00Z",
        freeze_blocked=False,
    )
    if status != "collecting":
        _sqlite_db.update_backlog_batch(db_path, batch_id, status=status)


def _seed_membership(db_path, batch_id: str, ticket_id: str) -> None:
    _sqlite_db.insert_backlog_batch_ticket(
        db_path, batch_id, ticket_id, "2026-07-01T10:00:00Z"
    )


def _seed_intelligence(db_path, ticket_id: str, analysis_status: str) -> None:
    _sqlite_db.upsert_ticket_intelligence(
        db_path, ticket_id, analysis_status=analysis_status
    )


def _seed_readiness(db_path, ticket_id: str, readiness_status: str) -> None:
    _sqlite_db.upsert_ticket_readiness(
        db_path, ticket_id, readiness_status=readiness_status
    )


def _seed_runtime(db_path, ticket_id: str, state: str) -> None:
    _sqlite_db.upsert_ticket_runtime(
        db_path, ticket_id, state=state, branch=f"ticket/{ticket_id}"
    )


# ── case 1 ────────────────────────────────────────────────────────────────────

def test_frozen_with_blocking_intelligence(tmp_path):
    """frozen + some intelligence not completed → blocking IDs in summary."""
    app = _make_app(tmp_path)
    db = app.state.db_path
    _seed_batch(db, "B001", status="frozen")
    for tid in ("T001", "T002", "T003"):
        _seed_membership(db, "B001", tid)
    _seed_intelligence(db, "T001", "completed")
    _seed_intelligence(db, "T002", "running")
    _seed_intelligence(db, "T003", "queued")

    client = TestClient(app)
    r = client.get("/dispatcher/batches/B001/pipeline-status")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["batch_status"] == "frozen"
    assert "T002" in body["waiting_summary"]
    assert "T003" in body["waiting_summary"]
    assert "T001" not in body["waiting_summary"]

    by_id = {t["ticket_id"]: t for t in body["tickets"]}
    assert by_id["T001"]["is_blocking"] is False
    assert by_id["T002"]["is_blocking"] is True
    assert by_id["T002"]["blocking_reason"] == "Intelligence running"
    assert by_id["T003"]["is_blocking"] is True
    assert by_id["T003"]["blocking_reason"] == "Intelligence queued"


# ── case 2 ────────────────────────────────────────────────────────────────────

def test_frozen_all_intelligence_completed(tmp_path):
    """frozen + all intelligence completed → 'Ready for dependency analysis'."""
    app = _make_app(tmp_path)
    db = app.state.db_path
    _seed_batch(db, "B002", status="frozen")
    for tid in ("T001", "T002"):
        _seed_membership(db, "B002", tid)
        _seed_intelligence(db, tid, "completed")

    client = TestClient(app)
    r = client.get("/dispatcher/batches/B002/pipeline-status")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["waiting_summary"] == "Ready for dependency analysis"
    assert all(not t["is_blocking"] for t in body["tickets"])


# ── case 3 ────────────────────────────────────────────────────────────────────

def test_readiness_running_with_blocking_tickets(tmp_path):
    """readiness_running + some not completed → waiting summary names those IDs."""
    app = _make_app(tmp_path)
    db = app.state.db_path
    _seed_batch(db, "B003", status="readiness_running")
    for tid in ("T003", "T004", "T005"):
        _seed_membership(db, "B003", tid)
    _seed_readiness(db, "T003", "completed")
    _seed_readiness(db, "T004", "running")
    _seed_readiness(db, "T005", "not_started")

    client = TestClient(app)
    r = client.get("/dispatcher/batches/B003/pipeline-status")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["waiting_summary"].startswith("Waiting on readiness:")
    assert "T004" in body["waiting_summary"]
    assert "T005" in body["waiting_summary"]
    by_id = {t["ticket_id"]: t for t in body["tickets"]}
    assert by_id["T003"]["is_blocking"] is False
    assert by_id["T004"]["is_blocking"] is True
    assert by_id["T005"]["is_blocking"] is True


# ── case 4 ────────────────────────────────────────────────────────────────────

def test_readiness_running_all_completed(tmp_path):
    """readiness_running + all completed → 'Readiness complete — awaiting dispatch'."""
    app = _make_app(tmp_path)
    db = app.state.db_path
    _seed_batch(db, "B004", status="readiness_running")
    for tid in ("T006", "T007"):
        _seed_membership(db, "B004", tid)
        _seed_readiness(db, tid, "completed")

    client = TestClient(app)
    r = client.get("/dispatcher/batches/B004/pipeline-status")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["waiting_summary"] == "Readiness complete — awaiting dispatch"
    assert all(not t["is_blocking"] for t in body["tickets"])


# ── case 5 ────────────────────────────────────────────────────────────────────

def test_missing_intelligence_row_treated_as_not_started(tmp_path):
    """Ticket absent from ticket_intelligence → not_started, blocking during frozen."""
    app = _make_app(tmp_path)
    db = app.state.db_path
    _seed_batch(db, "B005", status="frozen")
    _seed_membership(db, "B005", "T010")
    # deliberately no _seed_intelligence call

    client = TestClient(app)
    r = client.get("/dispatcher/batches/B005/pipeline-status")
    assert r.status_code == 200, r.text
    body = r.json()
    ticket = body["tickets"][0]
    assert ticket["ticket_id"] == "T010"
    assert ticket["intelligence_status"] == "not_started"
    assert ticket["is_blocking"] is True
    assert ticket["blocking_reason"] == "Intelligence not started"


# ── case 6 ────────────────────────────────────────────────────────────────────

def test_missing_readiness_row_treated_as_blocking(tmp_path):
    """Ticket absent from ticket_readiness → readiness_status None, blocking during readiness_running."""
    app = _make_app(tmp_path)
    db = app.state.db_path
    _seed_batch(db, "B006", status="readiness_running")
    _seed_membership(db, "B006", "T011")
    # deliberately no _seed_readiness call

    client = TestClient(app)
    r = client.get("/dispatcher/batches/B006/pipeline-status")
    assert r.status_code == 200, r.text
    body = r.json()
    ticket = body["tickets"][0]
    assert ticket["ticket_id"] == "T011"
    assert ticket["readiness_status"] is None
    assert ticket["is_blocking"] is True
    assert ticket["blocking_reason"] == "Readiness not started"


# ── case 7 ────────────────────────────────────────────────────────────────────

def test_intelligence_failed_is_blocking(tmp_path):
    """intelligence_status == 'failed' during frozen → blocking_reason 'Intelligence failed'."""
    app = _make_app(tmp_path)
    db = app.state.db_path
    _seed_batch(db, "B007", status="frozen")
    _seed_membership(db, "B007", "T020")
    _seed_intelligence(db, "T020", "failed")

    client = TestClient(app)
    r = client.get("/dispatcher/batches/B007/pipeline-status")
    assert r.status_code == 200, r.text
    body = r.json()
    ticket = body["tickets"][0]
    assert ticket["is_blocking"] is True
    assert ticket["blocking_reason"] == "Intelligence failed"


# ── case 8 ────────────────────────────────────────────────────────────────────

def test_readiness_failed_is_blocking(tmp_path):
    """readiness_status == 'failed' during readiness_running → 'Readiness failed — cannot dispatch'."""
    app = _make_app(tmp_path)
    db = app.state.db_path
    _seed_batch(db, "B008", status="readiness_running")
    _seed_membership(db, "B008", "T021")
    _seed_readiness(db, "T021", "failed")

    client = TestClient(app)
    r = client.get("/dispatcher/batches/B008/pipeline-status")
    assert r.status_code == 200, r.text
    body = r.json()
    ticket = body["tickets"][0]
    assert ticket["is_blocking"] is True
    assert ticket["blocking_reason"] == "Readiness failed — cannot dispatch"


# ── case 9 ────────────────────────────────────────────────────────────────────

def test_dispatching_no_tickets_blocking(tmp_path):
    """dispatching batch → all is_blocking=False regardless of intelligence/readiness."""
    app = _make_app(tmp_path)
    db = app.state.db_path
    _seed_batch(db, "B009", status="dispatching")
    for tid in ("T030", "T031"):
        _seed_membership(db, "B009", tid)
    _seed_intelligence(db, "T030", "running")
    _seed_readiness(db, "T031", "failed")

    client = TestClient(app)
    r = client.get("/dispatcher/batches/B009/pipeline-status")
    assert r.status_code == 200, r.text
    body = r.json()
    assert all(not t["is_blocking"] for t in body["tickets"])
    assert all(t["blocking_reason"] is None for t in body["tickets"])
    assert body["waiting_summary"] == "Dispatching tickets"


# ── case 10 ───────────────────────────────────────────────────────────────────

def test_runtime_state_informational_only(tmp_path):
    """runtime_state is populated but never makes a ticket blocking."""
    app = _make_app(tmp_path)
    db = app.state.db_path
    _seed_batch(db, "B010", status="frozen")
    _seed_membership(db, "B010", "T040")
    _seed_intelligence(db, "T040", "completed")
    _seed_runtime(db, "T040", "PLANNING")

    client = TestClient(app)
    r = client.get("/dispatcher/batches/B010/pipeline-status")
    assert r.status_code == 200, r.text
    body = r.json()
    ticket = body["tickets"][0]
    assert ticket["runtime_state"] == "PLANNING"
    assert ticket["is_blocking"] is False
    assert ticket["blocking_reason"] is None
