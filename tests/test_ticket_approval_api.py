"""Integration tests for the ticket approval API endpoints (T199)."""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "agent_runner"))


def _load_sqlite_db_module():
    import os as _os
    spec = importlib.util.spec_from_file_location(
        "_api_approvals_runtime_db_sqlite",
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
    import services.control_api.routes.approvals as _approvals_route
    import services.control_api.routes.readiness as _readiness_route
    # Use the same import path as the route so we share the module instance.
    import ticket_approval_service as _service

    app = create_app(project_root=tmp_path)
    isolated_db = tmp_path / ".runtime" / "adf-test-approvals.sqlite"
    _sqlite_db.init_runtime_db(isolated_db)
    app.state.db_path = isolated_db

    # Rebind every module that holds a runtime_db reference so the test is
    # insulated from any RUNTIME_DB_BACKEND env pollution by other tests
    # (matches the pattern used in test_ticket_readiness_api.py).
    _service.runtime_db = _sqlite_db
    _approvals_route._service = _service
    _readiness_route.runtime_db = _sqlite_db
    return app


def _make_ticket(tmp_path: Path, ticket_id: str) -> None:
    run_dir = tmp_path / "runs" / ticket_id
    run_dir.mkdir(parents=True)
    (run_dir / "state.json").write_text(
        json.dumps({"ticket_id": ticket_id, "state": "PLAN_APPROVED", "branch": f"ticket/{ticket_id}"}),
        encoding="utf-8",
    )
    (run_dir / "ticket.md").write_text(
        f"# {ticket_id}\n\nA test ticket.\n",
        encoding="utf-8",
    )


def _seed_ready_candidate(db_path: Path, ticket_id: str) -> None:
    _sqlite_db.upsert_ticket_readiness(
        db_path, ticket_id,
        readiness_status="ready_candidate",
        ready_candidate=1,
        blocking_reasons_json=[],
    )


# ── GET /tickets/{id}/approvals ──────────────────────────────────────────────

def test_get_approvals_404_when_ticket_missing(tmp_path):
    (tmp_path / "runs").mkdir()
    client = TestClient(_make_app(tmp_path))
    r = client.get("/tickets/T999/approvals")
    assert r.status_code == 404


def test_get_approvals_returns_empty_history(tmp_path):
    _make_ticket(tmp_path, "T001")
    client = TestClient(_make_app(tmp_path))
    r = client.get("/tickets/T001/approvals")
    assert r.status_code == 200
    body = r.json()
    assert body["ticket_id"] == "T001"
    assert body["approvals"] == []


def test_get_approvals_returns_history_after_decisions(tmp_path):
    _make_ticket(tmp_path, "T001")
    app = _make_app(tmp_path)
    db = app.state.db_path
    _seed_ready_candidate(db, "T001")
    client = TestClient(app)
    r = client.post(
        "/tickets/T001/approve-execution",
        json={"approved_by": "pierre", "comment": "ok"},
    )
    assert r.status_code == 200
    r = client.get("/tickets/T001/approvals")
    body = r.json()
    assert len(body["approvals"]) == 1
    assert body["approvals"][0]["approval_status"] == "approved"
    assert body["approvals"][0]["approved_by"] == "pierre"
    assert body["approvals"][0]["approval_comment"] == "ok"


# ── POST /tickets/{id}/approve-execution ─────────────────────────────────────

def test_approve_404_when_ticket_missing(tmp_path):
    (tmp_path / "runs").mkdir()
    client = TestClient(_make_app(tmp_path))
    r = client.post(
        "/tickets/T999/approve-execution",
        json={"approved_by": "pierre"},
    )
    assert r.status_code == 404


def test_approve_happy_path_promotes_to_ready_to_take(tmp_path):
    _make_ticket(tmp_path, "T001")
    app = _make_app(tmp_path)
    db = app.state.db_path
    _seed_ready_candidate(db, "T001")
    client = TestClient(app)

    r = client.post(
        "/tickets/T001/approve-execution",
        json={"approved_by": "pierre", "comment": "safe"},
    )
    assert r.status_code == 200
    assert r.json()["approval_status"] == "approved"

    r2 = client.get("/tickets/T001/readiness")
    assert r2.status_code == 200
    assert r2.json()["readiness_status"] == "ready_to_take"


def test_approve_idempotent_replay_returns_200_same_row(tmp_path):
    _make_ticket(tmp_path, "T001")
    app = _make_app(tmp_path)
    db = app.state.db_path
    _seed_ready_candidate(db, "T001")
    client = TestClient(app)

    r1 = client.post(
        "/tickets/T001/approve-execution",
        json={"approved_by": "pierre"},
    )
    r2 = client.post(
        "/tickets/T001/approve-execution",
        json={"approved_by": "pierre"},
    )
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["id"] == r2.json()["id"]

    r = client.get("/tickets/T001/approvals")
    assert len(r.json()["approvals"]) == 1


def test_approve_after_reject_returns_409(tmp_path):
    _make_ticket(tmp_path, "T001")
    app = _make_app(tmp_path)
    db = app.state.db_path
    _seed_ready_candidate(db, "T001")
    client = TestClient(app)

    client.post("/tickets/T001/reject-execution", json={"approved_by": "p"})
    r = client.post("/tickets/T001/approve-execution", json={"approved_by": "p"})
    assert r.status_code == 409


def test_approve_invalid_state_returns_409(tmp_path):
    _make_ticket(tmp_path, "T001")
    app = _make_app(tmp_path)
    # No readiness row at all → invalid_state
    client = TestClient(app)
    r = client.post("/tickets/T001/approve-execution", json={"approved_by": "p"})
    assert r.status_code == 409


# ── POST /tickets/{id}/reject-execution ──────────────────────────────────────

def test_reject_404_when_ticket_missing(tmp_path):
    (tmp_path / "runs").mkdir()
    client = TestClient(_make_app(tmp_path))
    r = client.post(
        "/tickets/T999/reject-execution",
        json={"approved_by": "pierre"},
    )
    assert r.status_code == 404


def test_reject_happy_path_blocks_with_reason(tmp_path):
    _make_ticket(tmp_path, "T001")
    app = _make_app(tmp_path)
    db = app.state.db_path
    _seed_ready_candidate(db, "T001")
    client = TestClient(app)

    r = client.post(
        "/tickets/T001/reject-execution",
        json={"approved_by": "pierre"},
    )
    assert r.status_code == 200
    assert r.json()["approval_status"] == "rejected"

    r2 = client.get("/tickets/T001/readiness")
    assert r2.status_code == 200
    body = r2.json()
    assert body["readiness_status"] == "blocked"
    assert "Execution approval rejected by pierre" in body["blocking_reasons"]


def test_reject_idempotent_replay_does_not_duplicate_reason(tmp_path):
    _make_ticket(tmp_path, "T001")
    app = _make_app(tmp_path)
    db = app.state.db_path
    _seed_ready_candidate(db, "T001")
    client = TestClient(app)

    r1 = client.post("/tickets/T001/reject-execution", json={"approved_by": "pierre"})
    r2 = client.post("/tickets/T001/reject-execution", json={"approved_by": "pierre"})
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["id"] == r2.json()["id"]

    history = client.get("/tickets/T001/approvals").json()
    assert len(history["approvals"]) == 1

    readiness = client.get("/tickets/T001/readiness").json()
    reasons = readiness["blocking_reasons"]
    assert reasons.count("Execution approval rejected by pierre") == 1


def test_reject_after_approve_returns_409(tmp_path):
    _make_ticket(tmp_path, "T001")
    app = _make_app(tmp_path)
    db = app.state.db_path
    _seed_ready_candidate(db, "T001")
    client = TestClient(app)

    client.post("/tickets/T001/approve-execution", json={"approved_by": "p"})
    r = client.post("/tickets/T001/reject-execution", json={"approved_by": "p"})
    assert r.status_code == 409


# ── Project-scoped mounts ────────────────────────────────────────────────────

def test_project_scoped_get_approvals(tmp_path):
    _make_ticket(tmp_path, "T001")
    client = TestClient(_make_app(tmp_path))
    r = client.get("/projects/proj1/tickets/T001/approvals")
    assert r.status_code == 200
    assert r.json()["approvals"] == []


def test_project_scoped_approve(tmp_path):
    _make_ticket(tmp_path, "T001")
    app = _make_app(tmp_path)
    db = app.state.db_path
    _seed_ready_candidate(db, "T001")
    client = TestClient(app)
    r = client.post(
        "/projects/proj1/tickets/T001/approve-execution",
        json={"approved_by": "pierre"},
    )
    assert r.status_code == 200
    assert r.json()["approval_status"] == "approved"
