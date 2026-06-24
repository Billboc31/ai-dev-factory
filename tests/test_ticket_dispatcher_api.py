"""FastAPI tests for /dispatcher/* (T212)."""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(
    0, str(Path(__file__).resolve().parents[1] / "tools" / "agent_runner")
)


def _load_sqlite_db_module():
    spec = importlib.util.spec_from_file_location(
        "_api_dispatcher_runtime_db_sqlite",
        Path(__file__).resolve().parents[1]
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
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    monkeypatch.delenv("AI_DEV_FACTORY_DISPATCHER_MODE", raising=False)


def _make_app(tmp_path: Path):
    from services.control_api.main import create_app

    app = create_app(project_root=tmp_path)
    isolated_db = tmp_path / ".runtime" / "adf-test-dispatcher.sqlite"
    _sqlite_db.init_runtime_db(isolated_db)
    app.state.db_path = isolated_db

    import runtime_db as live_db
    import ticket_dispatcher as _disp
    import ticket_execution_eligibility as _elig

    for name in (
        "get_ticket_intelligence",
        "get_ticket_readiness",
        "get_ticket_rule_evaluation",
        "get_latest_ticket_approval",
        "list_ticket_runtime",
    ):
        setattr(live_db, name, getattr(_sqlite_db, name))
    _elig.runtime_db = live_db
    _disp.runtime_db = live_db
    return app


def _seed_ticket(tmp_path: Path, db_path, ticket_id: str, **intel) -> None:
    run_dir = tmp_path / "runs" / ticket_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "ticket.md").write_text(f"# {ticket_id}\n", encoding="utf-8")
    _sqlite_db.upsert_ticket_runtime(
        db_path, ticket_id, state="INIT", branch=f"ticket/{ticket_id}"
    )
    fields = {
        "analysis_status": "completed",
        "requires_human_plan_review": 0,
    }
    fields.update(intel)
    _sqlite_db.upsert_ticket_intelligence(db_path, ticket_id, **fields)
    _sqlite_db.upsert_ticket_readiness(
        db_path, ticket_id, readiness_status="ready_candidate"
    )
    _sqlite_db.upsert_ticket_rule_evaluation(
        db_path,
        ticket_id=ticket_id,
        project_id="proj-a",
        eligibility_status="eligible",
        passed_rules=[],
        failed_rules=[],
        warnings=[],
        evaluated_at="2026-06-24T00:00:00Z",
    )


# ── /dispatcher/status ────────────────────────────────────────────────────

def test_status_defaults_to_off_when_env_unset(tmp_path):
    app = _make_app(tmp_path)
    client = TestClient(app)
    r = client.get("/dispatcher/status")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["mode"] == "off"
    assert "advisory" in body["available_modes"]
    assert "manual" in body["available_modes"]
    assert body["auto_enabled"] is False


def test_status_reports_advisory_when_env_set(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_DEV_FACTORY_DISPATCHER_MODE", "advisory")
    app = _make_app(tmp_path)
    client = TestClient(app)
    r = client.get("/dispatcher/status")
    assert r.status_code == 200
    assert r.json()["mode"] == "advisory"


# ── /dispatcher/recommendations — off ────────────────────────────────────

def test_recommendations_empty_when_mode_off(tmp_path):
    app = _make_app(tmp_path)
    _seed_ticket(tmp_path, app.state.db_path, "T100", queue_rank=1)
    client = TestClient(app)
    r = client.get("/dispatcher/recommendations")
    assert r.status_code == 200
    body = r.json()
    assert body["mode"] == "off"
    assert body["recommendations"] == []
    assert body["blocked"] == []


# ── /projects/{id}/dispatcher/recommendations — advisory ─────────────────

def test_project_recommendations_in_advisory_mode(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_DEV_FACTORY_DISPATCHER_MODE", "advisory")
    app = _make_app(tmp_path)
    _seed_ticket(tmp_path, app.state.db_path, "T101", queue_rank=2, difficulty_label="simple")
    _seed_ticket(tmp_path, app.state.db_path, "T102", queue_rank=8, difficulty_label="moderate")

    client = TestClient(app)
    r = client.get("/projects/proj-a/dispatcher/recommendations")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["mode"] == "advisory"
    assert body["project_id"] == "proj-a"
    ids = [rec["ticket_id"] for rec in body["recommendations"]]
    assert ids[0] == "T101"  # lower queue_rank + simple bonus
    assert set(ids) == {"T101", "T102"}
    for rec in body["recommendations"]:
        assert rec["ready_to_take"] is True
        assert rec["score"] > 0
        assert "intelligence" in rec
        assert rec["reason"]


def test_project_recommendations_mode_override(tmp_path, monkeypatch):
    # With env unset (off) but caller passing ?mode=advisory we still get
    # recommendations (the override is read-only and has no side effects).
    monkeypatch.delenv("AI_DEV_FACTORY_DISPATCHER_MODE", raising=False)
    app = _make_app(tmp_path)
    _seed_ticket(tmp_path, app.state.db_path, "T103", queue_rank=1)

    client = TestClient(app)
    r = client.get(
        "/projects/proj-a/dispatcher/recommendations?mode=advisory"
    )
    assert r.status_code == 200
    body = r.json()
    assert body["mode"] == "advisory"
    assert any(rec["ticket_id"] == "T103" for rec in body["recommendations"])


# ── /dispatcher/recommendations — auto returns not_implemented ───────────

def test_auto_mode_returns_not_implemented(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_DEV_FACTORY_DISPATCHER_MODE", "auto")
    app = _make_app(tmp_path)
    _seed_ticket(tmp_path, app.state.db_path, "T104", queue_rank=1)
    client = TestClient(app)
    r = client.get("/dispatcher/recommendations")
    assert r.status_code == 200
    body = r.json()
    assert body["mode"] == "auto"
    assert body.get("not_implemented") is True
    assert body["recommendations"] == []


# ── Endpoint is read-only ─────────────────────────────────────────────────

def test_endpoint_does_not_persist(tmp_path, monkeypatch):
    monkeypatch.setenv("AI_DEV_FACTORY_DISPATCHER_MODE", "advisory")
    app = _make_app(tmp_path)
    db = app.state.db_path
    _seed_ticket(tmp_path, db, "T105", queue_rank=2)
    before = db.read_bytes()
    client = TestClient(app)
    client.get("/dispatcher/recommendations")
    client.get("/projects/proj-a/dispatcher/recommendations")
    assert db.read_bytes() == before


# ── No scheduler/daemon import ────────────────────────────────────────────

def test_dispatcher_modules_do_not_import_runner() -> None:
    mod_paths = [
        Path(__file__).resolve().parents[1]
        / "tools"
        / "agent_runner"
        / "ticket_dispatcher.py",
        Path(__file__).resolve().parents[1]
        / "services"
        / "control_api"
        / "routes"
        / "dispatcher.py",
    ]
    forbidden = ("run_ticket", "run_daemon", "supervisor")
    for path in mod_paths:
        src = path.read_text(encoding="utf-8")
        for symbol in forbidden:
            assert symbol not in src, (
                f"{path.name} must not reference {symbol!r} — dispatcher is "
                "advisory and must not invoke the execution pipeline."
            )
