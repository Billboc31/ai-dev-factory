"""Integration tests for ticket operations API endpoints (T204)."""

from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "agent_runner"))


def _load_sqlite_db_module():
    spec = importlib.util.spec_from_file_location(
        "_api_ops_runtime_db_sqlite",
        Path(__file__).resolve().parents[1] / "tools" / "agent_runner" / "runtime_db.py",
    )
    mod = importlib.util.module_from_spec(spec)
    saved = os.environ.get("RUNTIME_DB_BACKEND")
    os.environ["RUNTIME_DB_BACKEND"] = "sqlite"
    try:
        spec.loader.exec_module(mod)
    finally:
        if saved is None:
            os.environ.pop("RUNTIME_DB_BACKEND", None)
        else:
            os.environ["RUNTIME_DB_BACKEND"] = saved
    return mod


_sqlite_db = _load_sqlite_db_module()


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)


def _make_app(tmp_path: Path, *, project_id: str = "proj-a"):
    from services.control_api.main import create_app
    from services.control_api.services.project_registry import ProjectEntry, ProjectRegistry
    import services.control_api.routes.operations as _ops_route

    app = create_app(project_root=tmp_path)
    isolated_db = tmp_path / ".runtime" / "adf-test-operations.sqlite"
    _sqlite_db.init_runtime_db(isolated_db)
    app.state.db_path = isolated_db
    app.state.project_registry = ProjectRegistry(
        _entries=[
            ProjectEntry(
                id=project_id,
                root=tmp_path,
                project_runtime_root=tmp_path,
            )
        ],
    )

    # Patch the route's runtime_db and the operations module's runtime_db to
    # share the isolated SQLite DB.
    _ops_route._ops.runtime_db = _sqlite_db
    _ops_route._ops.ticket_approval_service.runtime_db = _sqlite_db
    _ops_route._ops.ticket_diagnostics.runtime_db = _sqlite_db
    if hasattr(_ops_route._ops.ticket_diagnostics, "ticket_approval_service"):
        _ops_route._ops.ticket_diagnostics.ticket_approval_service.runtime_db = _sqlite_db
    _ops_route.runtime_db = _sqlite_db
    return app, isolated_db


def _make_ticket(tmp_path: Path, ticket_id: str, state: str = "PLAN_APPROVED") -> Path:
    run_dir = tmp_path / "runs" / ticket_id
    run_dir.mkdir(parents=True)
    (run_dir / "state.json").write_text(
        json.dumps({"ticket_id": ticket_id, "state": state, "branch": f"ticket/{ticket_id}"}),
        encoding="utf-8",
    )
    (run_dir / "ticket.md").write_text(f"# {ticket_id}\n", encoding="utf-8")
    return run_dir


# ── GET /tickets/{id}/operations ─────────────────────────────────────────────

def test_get_operations_returns_full_registry(tmp_path):
    _make_ticket(tmp_path, "T001")
    app, _ = _make_app(tmp_path)
    client = TestClient(app)
    r = client.get("/tickets/T001/operations")
    assert r.status_code == 200
    body = r.json()
    assert body["ticket_id"] == "T001"
    keys = {op["operation_key"] for op in body["operations"]}
    assert keys == {
        "rerun_intelligence",
        "rerun_readiness",
        "rerun_rules",
        "rerun_diagnostics",
        "approve_execution",
        "reject_execution",
        "mark_blocked",
        "reset_to_planning",
        "reset_to_coding",
        "clear_stuck_state",
        "delete_worktree",
        "archive_ticket",
    }
    # Each row carries the required safety metadata.
    by_key = {op["operation_key"]: op for op in body["operations"]}
    assert by_key["reset_to_planning"]["safety_level"] == "high"
    assert by_key["reset_to_planning"]["requires_typed_ticket_id"] is True
    assert by_key["delete_worktree"]["safety_level"] == "destructive"
    assert by_key["mark_blocked"]["requires_reason"] is True


def test_get_operations_404_when_ticket_missing(tmp_path):
    app, _ = _make_app(tmp_path)
    client = TestClient(app)
    r = client.get("/tickets/T999/operations")
    assert r.status_code == 404


# ── POST /tickets/{id}/operations/{operation_key} ────────────────────────────

def test_post_unknown_operation_returns_404(tmp_path):
    _make_ticket(tmp_path, "T001")
    app, _ = _make_app(tmp_path)
    client = TestClient(app)
    r = client.post("/tickets/T001/operations/made_up", json={})
    assert r.status_code == 404


def test_post_high_safety_rejects_without_typed_id(tmp_path):
    _make_ticket(tmp_path, "T001")
    app, db_path = _make_app(tmp_path)
    client = TestClient(app)
    r = client.post(
        "/tickets/T001/operations/reset_to_planning",
        json={"reason": "stale", "typed_ticket_id": "wrong"},
    )
    assert r.status_code == 400
    # Rejected attempt still audited.
    rows = _sqlite_db.list_ticket_operation_audit(db_path, "T001")
    assert any(r["status"] == "rejected" and r["operation_key"] == "reset_to_planning" for r in rows)


def test_post_archive_ticket_writes_archive_metadata(tmp_path):
    run_dir = _make_ticket(tmp_path, "T001", state="PLAN_APPROVED")
    app, _ = _make_app(tmp_path)
    client = TestClient(app)
    r = client.post(
        "/tickets/T001/operations/archive_ticket",
        json={"reason": "no longer needed"},
        headers={"X-Operator-Name": "alice"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "completed"
    assert body["operation_key"] == "archive_ticket"
    state = json.loads((run_dir / "state.json").read_text(encoding="utf-8"))
    assert state["archived"] is True
    assert state["archived_by"] == "alice"
    assert state["state"] == "PLAN_APPROVED"


def test_post_reset_to_planning_writes_init(tmp_path):
    run_dir = _make_ticket(tmp_path, "T001", state="PLAN_APPROVED")
    (run_dir / "plan.md").write_text("p", encoding="utf-8")
    app, _ = _make_app(tmp_path)
    client = TestClient(app)
    r = client.post(
        "/tickets/T001/operations/reset_to_planning",
        json={"reason": "stale", "typed_ticket_id": "T001"},
    )
    assert r.status_code == 200
    state = json.loads((run_dir / "state.json").read_text(encoding="utf-8"))
    assert state["state"] == "INIT"


def test_post_reset_to_coding_writes_plan_approved(tmp_path):
    run_dir = _make_ticket(tmp_path, "T001", state="IMPLEMENTATION_APPROVED")
    (run_dir / "plan.md").write_text("p", encoding="utf-8")
    (run_dir / "implementation-output.md").write_text("i", encoding="utf-8")
    app, _ = _make_app(tmp_path)
    client = TestClient(app)
    r = client.post(
        "/tickets/T001/operations/reset_to_coding",
        json={"reason": "regen impl", "typed_ticket_id": "T001"},
    )
    assert r.status_code == 200
    state = json.loads((run_dir / "state.json").read_text(encoding="utf-8"))
    assert state["state"] == "PLAN_APPROVED"
    assert (run_dir / "plan.md").exists()
    assert not (run_dir / "implementation-output.md").exists()


def test_post_rerun_diagnostics_low_safety_succeeds(tmp_path, monkeypatch):
    _make_ticket(tmp_path, "T001")
    app, _ = _make_app(tmp_path)

    # Patch the diagnostics module so we don't run the real pipeline.
    import services.control_api.routes.operations as _ops_route
    monkeypatch.setattr(
        _ops_route._ops.ticket_diagnostics,
        "diagnose_ticket",
        lambda *a, **k: {"is_stuck": False, "severity": "info"},
    )

    client = TestClient(app)
    r = client.post("/tickets/T001/operations/rerun_diagnostics", json={})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "completed"


def test_project_scoped_routes_work(tmp_path, monkeypatch):
    _make_ticket(tmp_path, "T001")
    app, _ = _make_app(tmp_path)
    import services.control_api.routes.operations as _ops_route
    monkeypatch.setattr(
        _ops_route._ops.ticket_diagnostics,
        "diagnose_ticket",
        lambda *a, **k: {"is_stuck": False, "severity": "info"},
    )

    client = TestClient(app)
    r_get = client.get("/projects/proj-a/tickets/T001/operations")
    assert r_get.status_code == 200

    r_post = client.post(
        "/projects/proj-a/tickets/T001/operations/rerun_diagnostics",
        json={},
    )
    assert r_post.status_code == 200


def _make_worktree_ticket(
    tmp_path: Path,
    ticket_id: str,
    state: str = "IMPLEMENTATION_FIX_REQUIRED",
) -> Path:
    run_dir = tmp_path / "worktrees" / ticket_id / "runs" / ticket_id
    run_dir.mkdir(parents=True)
    (run_dir / "state.json").write_text(
        json.dumps({"ticket_id": ticket_id, "state": state, "branch": f"ticket/{ticket_id}"}),
        encoding="utf-8",
    )
    (run_dir / "ticket.md").write_text(f"# {ticket_id}\n", encoding="utf-8")
    (run_dir / "plan.md").write_text("plan", encoding="utf-8")
    return run_dir


def test_project_scoped_reset_to_planning_finds_worktree_run_dir(tmp_path):
    run_dir = _make_worktree_ticket(tmp_path, "T027")
    app, _ = _make_app(tmp_path)
    client = TestClient(app)
    r = client.post(
        "/projects/proj-a/tickets/T027/operations/reset_to_planning",
        json={"reason": "stale plan", "typed_ticket_id": "T027"},
    )
    assert r.status_code == 200, r.text
    state = json.loads((run_dir / "state.json").read_text(encoding="utf-8"))
    assert state["state"] == "INIT"


def test_audit_recorded_for_success(tmp_path, monkeypatch):
    _make_ticket(tmp_path, "T001")
    app, db_path = _make_app(tmp_path)
    import services.control_api.routes.operations as _ops_route
    monkeypatch.setattr(
        _ops_route._ops.ticket_diagnostics,
        "diagnose_ticket",
        lambda *a, **k: {"is_stuck": False, "severity": "info"},
    )
    client = TestClient(app)
    r = client.post("/tickets/T001/operations/rerun_diagnostics", json={})
    assert r.status_code == 200
    rows = _sqlite_db.list_ticket_operation_audit(db_path, "T001")
    assert any(
        r["operation_key"] == "rerun_diagnostics" and r["status"] == "completed"
        for r in rows
    )
