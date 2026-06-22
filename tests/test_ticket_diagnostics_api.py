"""Integration tests for ticket diagnostics API endpoints (T203)."""

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
        "_api_diag_runtime_db_sqlite",
        Path(__file__).resolve().parents[1] / "tools" / "agent_runner" / "runtime_db.py",
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
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)


def _make_app(tmp_path: Path):
    from services.control_api.main import create_app
    import services.control_api.routes.diagnostics as _diag_route

    app = create_app(project_root=tmp_path)
    isolated_db = tmp_path / ".runtime" / "adf-test-diagnostics.sqlite"
    _sqlite_db.init_runtime_db(isolated_db)
    app.state.db_path = isolated_db

    # Patch the route's runtime_db AND the diagnostics module's runtime_db so
    # everything points at the isolated SQLite DB (regardless of
    # RUNTIME_DB_BACKEND env at import time).
    _diag_route.runtime_db = _sqlite_db
    _diag_route._diagnostics.runtime_db = _sqlite_db
    if hasattr(_diag_route._diagnostics, "ticket_approval_service"):
        _diag_route._diagnostics.ticket_approval_service.runtime_db = _sqlite_db
    return app


def _make_ticket(tmp_path: Path, ticket_id: str) -> None:
    run_dir = tmp_path / "runs" / ticket_id
    run_dir.mkdir(parents=True)
    (run_dir / "state.json").write_text(
        json.dumps({"ticket_id": ticket_id, "state": "PLAN_APPROVED", "branch": f"ticket/{ticket_id}"}),
        encoding="utf-8",
    )
    (run_dir / "ticket.md").write_text(f"# {ticket_id}\n", encoding="utf-8")


def test_get_diagnostics_404_before_run(tmp_path):
    _make_ticket(tmp_path, "T001")
    client = TestClient(_make_app(tmp_path))
    r = client.get("/tickets/T001/diagnostics")
    assert r.status_code == 404


def test_post_run_404_when_ticket_missing(tmp_path):
    (tmp_path / "runs").mkdir()
    client = TestClient(_make_app(tmp_path))
    r = client.post("/tickets/T999/diagnostics/run")
    assert r.status_code == 404


def test_post_run_persists_result(tmp_path):
    _make_ticket(tmp_path, "T001")
    app = _make_app(tmp_path)
    client = TestClient(app)
    r = client.post("/tickets/T001/diagnostics/run")
    assert r.status_code == 200
    body = r.json()
    assert body["ticket_id"] == "T001"
    assert "checks" in body
    assert "recommended_actions" in body
    # Persisted: GET should now succeed.
    g = client.get("/tickets/T001/diagnostics")
    assert g.status_code == 200
    g_body = g.json()
    assert g_body["ticket_id"] == "T001"
    # Persisted row contains the same checks.
    assert [c["key"] for c in g_body["checks"]] == [c["key"] for c in body["checks"]]


def test_project_scoped_get_returns_same_payload(tmp_path):
    _make_ticket(tmp_path, "T001")
    app = _make_app(tmp_path)
    client = TestClient(app)
    client.post("/tickets/T001/diagnostics/run")

    a = client.get("/tickets/T001/diagnostics").json()
    b = client.get("/projects/proj-a/tickets/T001/diagnostics").json()
    # Same persisted row, same payload.
    assert a == b


def test_project_scoped_post_run(tmp_path):
    _make_ticket(tmp_path, "T001")
    app = _make_app(tmp_path)
    client = TestClient(app)
    r = client.post("/projects/proj-a/tickets/T001/diagnostics/run")
    assert r.status_code == 200
    body = r.json()
    assert body["ticket_id"] == "T001"
    # Persisted.
    g = client.get("/tickets/T001/diagnostics")
    assert g.status_code == 200
