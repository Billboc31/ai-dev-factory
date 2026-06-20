"""Integration tests for ticket intelligence API endpoints (T197)."""

from __future__ import annotations

import json
import sys
import threading
import time
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "agent_runner"))


def _load_sqlite_db_module():
    """Load runtime_db in SQLite mode regardless of current RUNTIME_DB_BACKEND env."""
    import importlib.util, os as _os
    spec = importlib.util.spec_from_file_location(
        "_api_test_runtime_db_sqlite",
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
    """Remove AI_DEV_FACTORY_RUNTIME_ROOT so routes resolve tickets via project_root/runs."""
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)


def _make_app(tmp_path: Path):
    from services.control_api.main import create_app
    import services.control_api.routes.intelligence as _intel_route

    app = create_app(project_root=tmp_path)
    # Each test gets its own isolated SQLite DB to avoid shared-DB cross-test pollution.
    isolated_db = tmp_path / ".runtime" / "adf-test.sqlite"
    _sqlite_db.init_runtime_db(isolated_db)
    app.state.db_path = isolated_db

    # The route imports runtime_db at module level; in a postgres env that module is
    # rebound to postgres functions expecting a PgHandle. Override the reference so the
    # route's DB calls use our isolated SQLite DB (Path) instead.
    _intel_route.runtime_db = _sqlite_db

    return app


def _make_ticket(tmp_path: Path, ticket_id: str, state: str = "PLAN_APPROVED") -> None:
    run_dir = tmp_path / "runs" / ticket_id
    run_dir.mkdir(parents=True)
    (run_dir / "state.json").write_text(
        json.dumps({"ticket_id": ticket_id, "state": state, "branch": f"ticket/{ticket_id}-work"}),
        encoding="utf-8",
    )
    (run_dir / "ticket.md").write_text(
        f"# {ticket_id} — Test ticket\n\nThis is a test ticket with database and backend keywords.\n\n## Acceptance criteria\n\n- criterion one\n- criterion two\n",
        encoding="utf-8",
    )


# ── GET /tickets/{id}/intelligence ────────────────────────────────────────────

def test_get_intelligence_404_when_ticket_missing(tmp_path):
    (tmp_path / "runs").mkdir()
    client = TestClient(_make_app(tmp_path))
    r = client.get("/tickets/T999/intelligence")
    assert r.status_code == 404


def test_get_intelligence_404_when_no_analysis(tmp_path):
    _make_ticket(tmp_path, "T001")
    client = TestClient(_make_app(tmp_path))
    r = client.get("/tickets/T001/intelligence")
    assert r.status_code == 404
    assert "no intelligence analysis" in r.json()["detail"]


def test_get_intelligence_returns_analysis(tmp_path):
    _make_ticket(tmp_path, "T001")
    app = _make_app(tmp_path)
    db = app.state.db_path

    _sqlite_db.upsert_ticket_intelligence(
        db, "T001",
        analysis_status="completed",
        difficulty_score=5,
        difficulty_label="medium",
        risk_score=4,
        risk_label="moderate",
        complexity_factors='["backend"]',
        analysis_summary="test summary",
    )

    client = TestClient(app)
    r = client.get("/tickets/T001/intelligence")
    assert r.status_code == 200
    body = r.json()
    assert body["ticket_id"] == "T001"
    assert body["analysis_status"] == "completed"
    assert body["difficulty_score"] == 5
    assert body["difficulty_label"] == "medium"
    assert body["complexity_factors"] == ["backend"]
    assert body["analysis_summary"] == "test summary"


def test_get_intelligence_deserializes_json_fields(tmp_path):
    _make_ticket(tmp_path, "T001")
    app = _make_app(tmp_path)
    db = app.state.db_path

    _sqlite_db.upsert_ticket_intelligence(
        db, "T001",
        analysis_status="completed",
        complexity_factors='["backend", "database", "UI"]',
        dependency_hints='["T010", "T042"]',
        computed_signals_json='{"text_length": 500, "changes_scheduler": false}',
    )

    client = TestClient(app)
    r = client.get("/tickets/T001/intelligence")
    assert r.status_code == 200
    body = r.json()
    assert body["complexity_factors"] == ["backend", "database", "UI"]
    assert body["dependency_hints"] == ["T010", "T042"]
    assert body["computed_signals_json"] == {"text_length": 500, "changes_scheduler": False}


# ── POST /tickets/{id}/intelligence/analyze ───────────────────────────────────

def test_post_analyze_404_when_ticket_missing(tmp_path):
    (tmp_path / "runs").mkdir()
    client = TestClient(_make_app(tmp_path))
    r = client.post("/tickets/T999/intelligence/analyze")
    assert r.status_code == 404


def test_post_analyze_returns_202_queued(tmp_path):
    _make_ticket(tmp_path, "T001")
    app = _make_app(tmp_path)

    with patch("ticket_intelligence_analyzer.run_analysis") as mock_run:
        mock_run.return_value = None
        client = TestClient(app)
        r = client.post("/tickets/T001/intelligence/analyze")

    assert r.status_code == 202
    body = r.json()
    assert body["ticket_id"] == "T001"
    assert body["analysis_status"] == "queued"


def test_post_analyze_sets_queued_in_db(tmp_path):
    _make_ticket(tmp_path, "T001")
    app = _make_app(tmp_path)
    db = app.state.db_path

    with patch("ticket_intelligence_analyzer.run_analysis") as mock_run:
        mock_run.return_value = None
        client = TestClient(app)
        client.post("/tickets/T001/intelligence/analyze")

    row = _sqlite_db.get_ticket_intelligence(db, "T001")
    assert row is not None
    # status is 'queued' (set before thread starts) or may have changed if mock ran fast
    assert row["analysis_status"] in ("queued", "running", "completed", "failed")


def test_post_analyze_idempotent(tmp_path):
    _make_ticket(tmp_path, "T001")
    app = _make_app(tmp_path)

    with patch("ticket_intelligence_analyzer.run_analysis") as mock_run:
        mock_run.return_value = None
        client = TestClient(app)
        r1 = client.post("/tickets/T001/intelligence/analyze")
        r2 = client.post("/tickets/T001/intelligence/analyze")

    assert r1.status_code == 202
    assert r2.status_code == 202


def test_completed_analysis_readable_after_analyze(tmp_path):
    """Simulate a successful background analysis and verify GET returns completed data."""
    _make_ticket(tmp_path, "T001")
    app = _make_app(tmp_path)
    db = app.state.db_path

    def _fake_run(db_path, ticket_id, ticket_content, exec_cmd, project_root):
        _sqlite_db.upsert_ticket_intelligence(
            db_path, ticket_id,
            analysis_status="completed",
            difficulty_score=7,
            difficulty_label="complex",
            risk_score=6,
            risk_label="high",
            analysis_summary="Fake completed analysis.",
        )

    with patch("ticket_intelligence_analyzer.run_analysis", side_effect=_fake_run):
        client = TestClient(app)
        client.post("/tickets/T001/intelligence/analyze")
        time.sleep(0.2)

    r = client.get("/tickets/T001/intelligence")
    assert r.status_code == 200
    body = r.json()
    assert body["analysis_status"] == "completed"
    assert body["difficulty_score"] == 7


# ── GET /projects/{project_id}/tickets/{id}/intelligence ──────────────────────

def test_project_get_intelligence_returns_analysis(tmp_path):
    _make_ticket(tmp_path, "T001")
    app = _make_app(tmp_path)
    db = app.state.db_path

    _sqlite_db.upsert_ticket_intelligence(
        db, "T001",
        analysis_status="completed",
        difficulty_score=3,
        difficulty_label="simple",
        analysis_summary="project-scoped test",
    )

    client = TestClient(app)
    r = client.get("/projects/proj1/tickets/T001/intelligence")
    assert r.status_code == 200
    body = r.json()
    assert body["ticket_id"] == "T001"
    assert body["difficulty_label"] == "simple"


def test_project_post_analyze_returns_202(tmp_path):
    _make_ticket(tmp_path, "T001")
    app = _make_app(tmp_path)

    with patch("ticket_intelligence_analyzer.run_analysis") as mock_run:
        mock_run.return_value = None
        client = TestClient(app)
        r = client.post("/projects/proj1/tickets/T001/intelligence/analyze")

    assert r.status_code == 202
    assert r.json()["ticket_id"] == "T001"
    assert r.json()["analysis_status"] == "queued"


def test_post_analyze_idempotency_guard(tmp_path):
    """Second POST while status is queued/running must return 202 without a new thread."""
    _make_ticket(tmp_path, "T001")
    app = _make_app(tmp_path)
    db = app.state.db_path

    _sqlite_db.upsert_ticket_intelligence(db, "T001", analysis_status="running")

    with patch("ticket_intelligence_analyzer.run_analysis") as mock_run:
        mock_run.return_value = None
        client = TestClient(app)
        r = client.post("/tickets/T001/intelligence/analyze")

    assert r.status_code == 202
    assert r.json()["analysis_status"] == "running"
    mock_run.assert_not_called()


def test_failed_analysis_persisted(tmp_path):
    """Simulate a timeout/failure and verify it is persisted as failed."""
    _make_ticket(tmp_path, "T001")
    app = _make_app(tmp_path)
    db = app.state.db_path

    def _fake_fail(db_path, ticket_id, ticket_content, exec_cmd, project_root):
        _sqlite_db.upsert_ticket_intelligence(
            db_path, ticket_id,
            analysis_status="failed",
            analysis_summary="Analysis timed out after 120 seconds.",
        )

    with patch("ticket_intelligence_analyzer.run_analysis", side_effect=_fake_fail):
        client = TestClient(app)
        client.post("/tickets/T001/intelligence/analyze")
        time.sleep(0.2)

    r = client.get("/tickets/T001/intelligence")
    assert r.status_code == 200
    body = r.json()
    assert body["analysis_status"] == "failed"
    assert "timed out" in (body["analysis_summary"] or "").lower()
