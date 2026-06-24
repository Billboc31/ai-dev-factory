"""Integration tests for the ticket readiness API endpoints (T198)."""

from __future__ import annotations

import importlib.util
import json
import sys
import time
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "agent_runner"))


def _load_sqlite_db_module():
    import os as _os
    spec = importlib.util.spec_from_file_location(
        "_api_readiness_runtime_db_sqlite",
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
    import services.control_api.routes.readiness as _readiness_route

    app = create_app(project_root=tmp_path)
    isolated_db = tmp_path / ".runtime" / "adf-test-readiness.sqlite"
    _sqlite_db.init_runtime_db(isolated_db)
    app.state.db_path = isolated_db

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


# ── GET /tickets/{id}/readiness ──────────────────────────────────────────────

def test_get_readiness_404_when_ticket_missing(tmp_path):
    (tmp_path / "runs").mkdir()
    client = TestClient(_make_app(tmp_path))
    r = client.get("/tickets/T999/readiness")
    assert r.status_code == 404


def test_get_readiness_404_when_no_evaluation(tmp_path):
    _make_ticket(tmp_path, "T001")
    client = TestClient(_make_app(tmp_path))
    r = client.get("/tickets/T001/readiness")
    assert r.status_code == 404
    assert "no readiness evaluation" in r.json()["detail"]


def test_get_readiness_returns_persisted_row(tmp_path):
    _make_ticket(tmp_path, "T001")
    app = _make_app(tmp_path)
    db = app.state.db_path

    _sqlite_db.upsert_ticket_readiness(
        db, "T001",
        readiness_status="ready_candidate",
        ready_candidate=1,
        blocking_reasons_json=[],
        warnings_json=[],
        dependency_check_status="passed",
        approval_check_status="passed",
        context_freshness_status="fresh",
        evaluated_at="2025-01-01T00:00:00Z",
    )
    client = TestClient(app)
    r = client.get("/tickets/T001/readiness")
    assert r.status_code == 200
    body = r.json()
    assert body["ticket_id"] == "T001"
    assert body["readiness_status"] == "ready_candidate"
    assert body["ready_candidate"] is True
    assert body["blocking_reasons"] == []
    assert body["dependency_check_status"] == "passed"
    assert body["context_freshness_status"] == "fresh"


def test_get_readiness_returns_blocking_reasons(tmp_path):
    _make_ticket(tmp_path, "T002")
    app = _make_app(tmp_path)
    db = app.state.db_path

    _sqlite_db.upsert_ticket_readiness(
        db, "T002",
        readiness_status="blocked",
        ready_candidate=0,
        blocking_reasons_json=[
            "Dependency T001 not merged",
        ],
        warnings_json=["Human plan review may be required later"],
        dependency_check_status="failed",
        approval_check_status="advisory",
    )
    client = TestClient(app)
    r = client.get("/tickets/T002/readiness")
    assert r.status_code == 200
    body = r.json()
    assert body["readiness_status"] == "blocked"
    assert body["ready_candidate"] is False
    assert "Dependency T001 not merged" in body["blocking_reasons"]
    assert "Human plan approval missing" not in body["blocking_reasons"]
    assert "Human plan review may be required later" in body["warnings"]


def test_get_readiness_returns_warnings(tmp_path):
    _make_ticket(tmp_path, "T003")
    app = _make_app(tmp_path)
    db = app.state.db_path

    _sqlite_db.upsert_ticket_readiness(
        db, "T003",
        readiness_status="ready_candidate",
        ready_candidate=1,
        blocking_reasons_json=[],
        warnings_json=["Human plan review may be required later"],
        approval_check_status="advisory",
    )
    client = TestClient(app)
    r = client.get("/tickets/T003/readiness")
    assert r.status_code == 200
    body = r.json()
    assert "Human plan review may be required later" in body["warnings"]


def test_readiness_returns_warnings_not_blockers_when_approvals_pending(tmp_path):
    """T213: future approvals are warnings only — never blockers — in the payload."""
    _make_ticket(tmp_path, "T010")
    app = _make_app(tmp_path)
    db = app.state.db_path

    _sqlite_db.upsert_ticket_readiness(
        db, "T010",
        readiness_status="ready_candidate",
        ready_candidate=1,
        blocking_reasons_json=[],
        warnings_json=[
            "Human plan review may be required later",
            "Human execution approval may be required later",
        ],
        approval_check_status="advisory",
        human_approval_required=1,
        human_approval_present=0,
    )
    client = TestClient(app)
    r = client.get("/tickets/T010/readiness")
    assert r.status_code == 200
    body = r.json()
    assert body["blocking_reasons"] == []
    # The contract: no later-stage gate appears as a blocker.
    forbidden = ("approval", "plan review", "execution rule", "ready_to_take")
    for reason in body["blocking_reasons"]:
        for tok in forbidden:
            assert tok not in reason.lower()
    assert "Human plan review may be required later" in body["warnings"]
    assert "Human execution approval may be required later" in body["warnings"]


def test_readiness_status_ready_candidate_with_advisory_warnings_is_not_blocked(tmp_path):
    """T213: ready_candidate stays ready_candidate even with advisory warnings."""
    _make_ticket(tmp_path, "T011")
    app = _make_app(tmp_path)
    db = app.state.db_path

    _sqlite_db.upsert_ticket_readiness(
        db, "T011",
        readiness_status="ready_candidate",
        ready_candidate=1,
        blocking_reasons_json=[],
        warnings_json=["Human plan review may be required later"],
        approval_check_status="advisory",
    )
    client = TestClient(app)
    r = client.get("/tickets/T011/readiness")
    assert r.status_code == 200
    body = r.json()
    assert body["readiness_status"] == "ready_candidate"
    assert body["ready_candidate"] is True
    assert body["blocking_reasons"] == []


# ── POST /tickets/{id}/evaluate-readiness ────────────────────────────────────

def test_post_evaluate_404_when_ticket_missing(tmp_path):
    (tmp_path / "runs").mkdir()
    client = TestClient(_make_app(tmp_path))
    r = client.post("/tickets/T999/evaluate-readiness")
    assert r.status_code == 404


def test_post_evaluate_returns_202_queued(tmp_path):
    _make_ticket(tmp_path, "T001")
    app = _make_app(tmp_path)

    with patch("ticket_readiness_evaluator.run_evaluation") as mock_run:
        mock_run.return_value = None
        client = TestClient(app)
        r = client.post("/tickets/T001/evaluate-readiness")

    assert r.status_code == 202
    body = r.json()
    assert body["ticket_id"] == "T001"
    assert body["readiness_status"] == "queued"


def test_post_evaluate_sets_queued_in_db(tmp_path):
    _make_ticket(tmp_path, "T001")
    app = _make_app(tmp_path)
    db = app.state.db_path

    with patch("ticket_readiness_evaluator.run_evaluation") as mock_run:
        mock_run.return_value = None
        client = TestClient(app)
        client.post("/tickets/T001/evaluate-readiness")

    row = _sqlite_db.get_ticket_readiness(db, "T001")
    assert row is not None
    assert row["readiness_status"] in ("queued", "running", "ready_candidate", "blocked", "failed")


def test_post_evaluate_idempotent_while_queued(tmp_path):
    """Second POST while status is queued/running must return 202 without a new thread."""
    _make_ticket(tmp_path, "T001")
    app = _make_app(tmp_path)
    db = app.state.db_path

    _sqlite_db.upsert_ticket_readiness(db, "T001", readiness_status="running")

    with patch("ticket_readiness_evaluator.run_evaluation") as mock_run:
        mock_run.return_value = None
        client = TestClient(app)
        r = client.post("/tickets/T001/evaluate-readiness")

    assert r.status_code == 202
    assert r.json()["readiness_status"] == "running"
    mock_run.assert_not_called()


def test_post_evaluate_re_runs_after_completion(tmp_path):
    """A second POST after completion is allowed and queues a new evaluation."""
    _make_ticket(tmp_path, "T001")
    app = _make_app(tmp_path)
    db = app.state.db_path
    _sqlite_db.upsert_ticket_readiness(db, "T001", readiness_status="ready_candidate")

    with patch("ticket_readiness_evaluator.run_evaluation") as mock_run:
        mock_run.return_value = None
        client = TestClient(app)
        r = client.post("/tickets/T001/evaluate-readiness")

    assert r.status_code == 202
    assert r.json()["readiness_status"] == "queued"


def test_completed_evaluation_readable_after_evaluate(tmp_path):
    _make_ticket(tmp_path, "T001")
    app = _make_app(tmp_path)
    db = app.state.db_path

    def _fake_run(db_path, ticket_id, ticket_content, project_root):
        _sqlite_db.upsert_ticket_readiness(
            db_path, ticket_id,
            readiness_status="ready_candidate",
            ready_candidate=1,
            blocking_reasons_json=[],
            dependency_check_status="passed",
            approval_check_status="passed",
            context_freshness_status="fresh",
        )

    with patch("ticket_readiness_evaluator.run_evaluation", side_effect=_fake_run):
        client = TestClient(app)
        client.post("/tickets/T001/evaluate-readiness")
        time.sleep(0.2)

    r = client.get("/tickets/T001/readiness")
    assert r.status_code == 200
    body = r.json()
    assert body["readiness_status"] == "ready_candidate"
    assert body["ready_candidate"] is True


# ── Project-scoped variants ──────────────────────────────────────────────────

def test_project_scoped_get_readiness(tmp_path):
    _make_ticket(tmp_path, "T001")
    app = _make_app(tmp_path)
    db = app.state.db_path
    _sqlite_db.upsert_ticket_readiness(
        db, "T001",
        readiness_status="blocked",
        blocking_reasons_json=["Missing Ticket Intelligence analysis"],
    )
    client = TestClient(app)
    r = client.get("/projects/proj1/tickets/T001/readiness")
    assert r.status_code == 200
    body = r.json()
    assert body["readiness_status"] == "blocked"
    assert body["blocking_reasons"] == ["Missing Ticket Intelligence analysis"]


def test_project_scoped_post_evaluate(tmp_path):
    _make_ticket(tmp_path, "T001")
    app = _make_app(tmp_path)

    with patch("ticket_readiness_evaluator.run_evaluation") as mock_run:
        mock_run.return_value = None
        client = TestClient(app)
        r = client.post("/projects/proj1/tickets/T001/evaluate-readiness")

    assert r.status_code == 202
    assert r.json()["readiness_status"] == "queued"
