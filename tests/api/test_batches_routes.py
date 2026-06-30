"""FastAPI tests for /dispatcher/batches/* (T219)."""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

# Make ../ and ../tools/agent_runner importable.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
sys.path.insert(
    0, str(Path(__file__).resolve().parents[2] / "tools" / "agent_runner")
)


def _load_sqlite_db_module():
    spec = importlib.util.spec_from_file_location(
        "_api_batches_runtime_db_sqlite",
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
    # Force the SQLite backend in tests so create_app does not try to reach a
    # Postgres instance — the project-scoped DB resolver consults the live
    # runtime_db module to compute the file path.
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
    isolated_db = tmp_path / ".runtime" / "adf-test-batches.sqlite"
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
        "update_backlog_batch",
        "append_runtime_event",
        # Project-scoped resolver: in Postgres mode the live module returns a
        # PgHandle whose __str__ is "postgres:adf#<project>". The route then
        # hands that string to the SQLite functions reinjected above, and
        # sqlite3.connect() materialises a real file in CWD. Alias the SQLite
        # resolver so the route stays on the fixture's isolated .sqlite path.
        "resolve_db_path_for_project",
    ):
        setattr(live_db, name, getattr(_sqlite_db, name))
    _bb.runtime_db = live_db
    _disp.runtime_db = live_db
    _batch_routes.runtime_db = live_db
    return app


def _seed_batch(
    db_path,
    batch_id: str,
    *,
    status: str = "collecting",
    created_at: str = "2026-06-30T10:00:00Z",
    last_activity_at: str = "2026-06-30T10:00:00Z",
    frozen_at: str | None = None,
    completed_at: str | None = None,
    dependency_analysis_attempts: int = 0,
    last_dependency_analysis_error: str | None = None,
    next_dependency_analysis_retry_at: str | None = None,
    freeze_blocked: bool = False,
) -> None:
    _sqlite_db.insert_backlog_batch(
        db_path,
        batch_id,
        status=status,
        created_at=created_at,
        last_activity_at=last_activity_at,
        freeze_blocked=freeze_blocked,
    )
    fields: dict = {}
    if status != "collecting":
        fields["status"] = status
    if frozen_at is not None:
        fields["frozen_at"] = frozen_at
    if completed_at is not None:
        fields["completed_at"] = completed_at
    if dependency_analysis_attempts:
        fields["dependency_analysis_attempts"] = dependency_analysis_attempts
    if last_dependency_analysis_error is not None:
        fields["last_dependency_analysis_error"] = last_dependency_analysis_error
    if next_dependency_analysis_retry_at is not None:
        fields["next_dependency_analysis_retry_at"] = next_dependency_analysis_retry_at
    if fields:
        _sqlite_db.update_backlog_batch(db_path, batch_id, **fields)


def _seed_membership(db_path, batch_id: str, ticket_id: str) -> None:
    _sqlite_db.insert_backlog_batch_ticket(
        db_path, batch_id, ticket_id, "2026-06-30T10:00:00Z"
    )


def _seed_ticket_runtime(
    db_path,
    ticket_id: str,
    state: str = "INIT",
) -> None:
    _sqlite_db.upsert_ticket_runtime(
        db_path, ticket_id, state=state, branch=f"ticket/{ticket_id}"
    )


def _seed_analysis(
    db_path,
    *,
    batch_id: str,
    ticket_id: str,
    execution_phase: int | None = None,
    depends_on: list[str] | None = None,
    blocks: list[str] | None = None,
    conflicting: list[str] | None = None,
    parallel_group: str | None = None,
) -> None:
    _sqlite_db.upsert_dependency_analysis(
        db_path,
        ticket_id=ticket_id,
        batch_id=batch_id,
        depends_on=depends_on or [],
        blocks=blocks or [],
        parallel_group=parallel_group,
        conflicting_tickets=conflicting or [],
        execution_phase=str(execution_phase) if execution_phase is not None else None,
        relationship_classifications=[],
        analyzed_at="2026-06-30T10:00:00Z",
    )


# ── list endpoint ────────────────────────────────────────────────────────────

def test_list_batches_returns_summaries(tmp_path):
    app = _make_app(tmp_path)
    db = app.state.db_path
    _seed_batch(db, "B0001", status="dispatching", created_at="2026-06-30T09:00:00Z")
    _seed_batch(db, "B0002", status="collecting", created_at="2026-06-30T10:00:00Z")
    _seed_ticket_runtime(db, "T1", state="DONE")
    _seed_ticket_runtime(db, "T2", state="CODING")
    _seed_membership(db, "B0001", "T1")
    _seed_membership(db, "B0001", "T2")
    _seed_analysis(db, batch_id="B0001", ticket_id="T1", execution_phase=1)
    _seed_analysis(db, batch_id="B0001", ticket_id="T2", execution_phase=2)

    client = TestClient(app)
    r = client.get("/dispatcher/batches")
    assert r.status_code == 200, r.text
    body = r.json()
    ids = [b["batch_id"] for b in body["batches"]]
    assert set(ids) == {"B0001", "B0002"}
    by_id = {b["batch_id"]: b for b in body["batches"]}
    assert by_id["B0001"]["ticket_count"] == 2
    assert by_id["B0001"]["progress"]["done"] == 1
    assert by_id["B0001"]["progress"]["running"] == 1
    assert by_id["B0001"]["current_phase"] == 1  # phase 1 fully done
    assert by_id["B0002"]["ticket_count"] == 0


# ── current/next selection ───────────────────────────────────────────────────

def test_current_next_selection(tmp_path):
    app = _make_app(tmp_path)
    db = app.state.db_path
    _seed_batch(db, "B0001", status="dispatching", created_at="2026-06-30T09:00:00Z")
    _seed_batch(db, "B0002", status="collecting", created_at="2026-06-30T10:00:00Z")
    _seed_batch(db, "B0003", status="completed", created_at="2026-06-30T08:00:00Z")

    client = TestClient(app)
    r = client.get("/dispatcher/batches/current")
    assert r.status_code == 200
    body = r.json()
    assert body["current"]["batch_id"] == "B0001"
    assert body["next"]["batch_id"] == "B0002"


def test_current_is_null_when_none_dispatching(tmp_path):
    app = _make_app(tmp_path)
    db = app.state.db_path
    _seed_batch(db, "B0010", status="collecting")
    client = TestClient(app)
    body = client.get("/dispatcher/batches/current").json()
    assert body["current"] is None
    assert body["next"]["batch_id"] == "B0010"


# ── detail endpoint ──────────────────────────────────────────────────────────

def test_detail_endpoint_lists_tickets(tmp_path):
    app = _make_app(tmp_path)
    db = app.state.db_path
    _seed_batch(db, "B0001", status="dispatching")
    _seed_ticket_runtime(db, "T1", state="DONE")
    _seed_ticket_runtime(db, "T2", state="INIT")
    _seed_membership(db, "B0001", "T1")
    _seed_membership(db, "B0001", "T2")
    _seed_analysis(db, batch_id="B0001", ticket_id="T1", execution_phase=1)
    _seed_analysis(
        db,
        batch_id="B0001",
        ticket_id="T2",
        execution_phase=2,
        depends_on=["T1"],
    )
    # Write a ticket.md so title is populated.
    runs_dir = tmp_path / "runs" / "T1"
    runs_dir.mkdir(parents=True, exist_ok=True)
    (runs_dir / "ticket.md").write_text("# T1 — first ticket\n", encoding="utf-8")

    client = TestClient(app)
    r = client.get("/dispatcher/batches/B0001")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["batch"]["batch_id"] == "B0001"
    by_id = {t["ticket_id"]: t for t in body["tickets"]}
    assert by_id["T1"]["status"] == "DONE"
    assert by_id["T1"]["execution_phase"] == 1
    assert by_id["T1"]["title"] == "T1 — first ticket"
    assert by_id["T2"]["depends_on"] == ["T1"]


def test_detail_unknown_batch_returns_404(tmp_path):
    app = _make_app(tmp_path)
    client = TestClient(app)
    r = client.get("/dispatcher/batches/BNOPE")
    assert r.status_code == 404


# ── graph endpoint ───────────────────────────────────────────────────────────

def test_graph_payload_shape(tmp_path):
    app = _make_app(tmp_path)
    db = app.state.db_path
    _seed_batch(db, "B0001", status="dispatching")
    _seed_ticket_runtime(db, "T1", state="DONE")
    _seed_ticket_runtime(db, "T2", state="CODING")
    _seed_membership(db, "B0001", "T1")
    _seed_membership(db, "B0001", "T2")
    _seed_analysis(db, batch_id="B0001", ticket_id="T1", execution_phase=1)
    _seed_analysis(
        db,
        batch_id="B0001",
        ticket_id="T2",
        execution_phase=2,
        depends_on=["T1"],
        conflicting=["T1"],
    )

    client = TestClient(app)
    r = client.get("/dispatcher/batches/B0001/graph")
    assert r.status_code == 200, r.text
    body = r.json()
    node_ids = {n["id"] for n in body["nodes"]}
    assert node_ids == {"T1", "T2"}
    colors = {n["id"]: n["color_key"] for n in body["nodes"]}
    assert colors["T1"] == "done"
    assert colors["T2"] == "running"
    edges = body["edges"]
    assert any(
        e["from"] == "T1" and e["to"] == "T2" and e["type"] == "depends_on"
        for e in edges
    )
    assert any(e["type"] == "conflicts_with" for e in edges)


# ── phases endpoint ──────────────────────────────────────────────────────────

def test_phases_endpoint_groups_by_execution_phase(tmp_path):
    app = _make_app(tmp_path)
    db = app.state.db_path
    _seed_batch(db, "B0001", status="dispatching")
    for ticket_id in ("T1", "T2", "T3", "T4"):
        _seed_ticket_runtime(db, ticket_id, state="INIT")
        _seed_membership(db, "B0001", ticket_id)
    _seed_analysis(db, batch_id="B0001", ticket_id="T1", execution_phase=1)
    _seed_analysis(db, batch_id="B0001", ticket_id="T2", execution_phase=2)
    _seed_analysis(db, batch_id="B0001", ticket_id="T3", execution_phase=2)
    # T4 has no analysis row → ends up in "null" bucket at the end.

    client = TestClient(app)
    body = client.get("/dispatcher/batches/B0001/phases").json()
    phases = body["phases"]
    assert [p["phase"] for p in phases] == [1, 2, None]
    assert phases[0]["tickets"] == ["T1"]
    assert sorted(phases[1]["tickets"]) == ["T2", "T3"]
    assert phases[2]["tickets"] == ["T4"]


# ── insights endpoint ────────────────────────────────────────────────────────

def test_insights_uses_dispatcher_recommendations(tmp_path, monkeypatch):
    app = _make_app(tmp_path)
    db = app.state.db_path
    _seed_batch(db, "B0001", status="dispatching")
    for ticket_id in ("T1", "T2", "T3"):
        _seed_ticket_runtime(db, ticket_id, state="INIT")
        _seed_membership(db, "B0001", ticket_id)
    _seed_analysis(db, batch_id="B0001", ticket_id="T1", execution_phase=1)
    _seed_analysis(
        db,
        batch_id="B0001",
        ticket_id="T2",
        execution_phase=2,
        depends_on=["T1"],
    )
    _seed_analysis(
        db,
        batch_id="B0001",
        ticket_id="T3",
        execution_phase=2,
        conflicting=["T2"],
    )

    # Stub the dispatcher payload — keeps the test isolated from the full
    # eligibility chain (intelligence + readiness + rules) which is exercised
    # by its own dedicated suite.
    from services.control_api.routes import batches as _batch_routes

    def _fake_dispatcher(*_args, **_kwargs):
        return {
            "mode": "advisory",
            "recommendations": [
                {"ticket_id": "T1", "rank": 1, "score": 100, "ready_to_take": True}
            ],
            "blocked": [
                {"ticket_id": "T2", "ready_to_take": False, "status": "BLOCKED"}
            ],
        }

    monkeypatch.setattr(_batch_routes, "_dispatcher_payload", _fake_dispatcher)

    client = TestClient(app)
    body = client.get("/dispatcher/batches/B0001/insights").json()
    assert body["runnable"] == ["T1"]
    blocked_ids = {b["ticket_id"]: b["blocked_by"] for b in body["blocked"]}
    assert blocked_ids == {"T2": ["T1"]}
    conflict_ids = {c["ticket_id"]: c["conflicts_with"] for c in body["conflicts"]}
    # Both T2 and T3 reference each other once their conflicting_tickets
    # arrays are walked.
    assert "T3" in conflict_ids
    assert conflict_ids["T3"] == ["T2"]


# ── action guards ────────────────────────────────────────────────────────────

def test_freeze_succeeds_from_collecting(tmp_path):
    app = _make_app(tmp_path)
    db = app.state.db_path
    _seed_batch(db, "B0001", status="collecting")
    client = TestClient(app)
    r = client.post("/dispatcher/batches/B0001/freeze")
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "frozen"
    assert _sqlite_db.get_backlog_batch(db, "B0001")["status"] == "frozen"


def test_freeze_rejects_non_collecting(tmp_path):
    app = _make_app(tmp_path)
    db = app.state.db_path
    _seed_batch(db, "B0001", status="dispatching")
    client = TestClient(app)
    r = client.post("/dispatcher/batches/B0001/freeze")
    assert r.status_code == 409


def test_retry_dependency_analysis_succeeds_when_failed(tmp_path):
    app = _make_app(tmp_path)
    db = app.state.db_path
    _seed_batch(
        db,
        "B0001",
        status="dependency_analysis_failed",
        dependency_analysis_attempts=1,
    )
    client = TestClient(app)
    r = client.post("/dispatcher/batches/B0001/retry-dependency-analysis")
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "dependency_analysis_running"


def test_retry_dependency_analysis_rejects_other_states(tmp_path):
    app = _make_app(tmp_path)
    db = app.state.db_path
    _seed_batch(db, "B0001", status="collecting")
    client = TestClient(app)
    r = client.post("/dispatcher/batches/B0001/retry-dependency-analysis")
    assert r.status_code == 409


def test_recompute_dependencies_resets_to_frozen(tmp_path):
    app = _make_app(tmp_path)
    db = app.state.db_path
    _seed_batch(
        db,
        "B0001",
        status="dependency_analysis_failed",
        dependency_analysis_attempts=3,
        last_dependency_analysis_error="boom",
    )
    client = TestClient(app)
    r = client.post("/dispatcher/batches/B0001/recompute-dependencies")
    assert r.status_code == 200, r.text
    row = _sqlite_db.get_backlog_batch(db, "B0001")
    assert row["status"] == "frozen"
    assert int(row["dependency_analysis_attempts"]) == 0


def test_recompute_dependencies_rejects_dispatching(tmp_path):
    app = _make_app(tmp_path)
    db = app.state.db_path
    _seed_batch(db, "B0001", status="dispatching")
    client = TestClient(app)
    r = client.post("/dispatcher/batches/B0001/recompute-dependencies")
    assert r.status_code == 409


def test_cancel_succeeds_from_collecting(tmp_path):
    app = _make_app(tmp_path)
    db = app.state.db_path
    _seed_batch(db, "B0001", status="collecting")
    client = TestClient(app)
    r = client.post("/dispatcher/batches/B0001/cancel")
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "completed"


def test_cancel_rejects_dispatching(tmp_path):
    app = _make_app(tmp_path)
    db = app.state.db_path
    _seed_batch(db, "B0001", status="dispatching")
    client = TestClient(app)
    r = client.post("/dispatcher/batches/B0001/cancel")
    assert r.status_code == 409


# ── project-scoped variant smoke check ───────────────────────────────────────

def test_project_scoped_list_uses_project_router(tmp_path):
    app = _make_app(tmp_path)
    db = app.state.db_path
    _seed_batch(db, "B0001", status="collecting")
    client = TestClient(app)
    r = client.get("/projects/proj-a/dispatcher/batches")
    assert r.status_code == 200, r.text
    body = r.json()
    assert [b["batch_id"] for b in body["batches"]] == ["B0001"]
