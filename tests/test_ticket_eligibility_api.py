"""FastAPI tests for /tickets/{id}/eligibility (T211)."""

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
        "_api_eligibility_runtime_db_sqlite",
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

    app = create_app(project_root=tmp_path)
    isolated_db = tmp_path / ".runtime" / "adf-test-eligibility.sqlite"
    _sqlite_db.init_runtime_db(isolated_db)
    app.state.db_path = isolated_db

    # The aggregator module reads through ``runtime_db``; in this dev shell
    # that defaults to Postgres. Rebind the read-side accessors to the
    # freshly loaded SQLite module so the test seeds and the aggregator reads
    # talk to the same file.
    import runtime_db as live_db
    import ticket_execution_eligibility as _elig
    for name in (
        "get_ticket_intelligence",
        "get_ticket_readiness",
        "get_ticket_rule_evaluation",
        "get_latest_ticket_approval",
    ):
        setattr(live_db, name, getattr(_sqlite_db, name))
    _elig.runtime_db = live_db
    return app


def _make_ticket(tmp_path: Path, ticket_id: str, body: str = "") -> None:
    run_dir = tmp_path / "runs" / ticket_id
    run_dir.mkdir(parents=True)
    (run_dir / "state.json").write_text(
        json.dumps({"ticket_id": ticket_id, "state": "INIT", "branch": f"ticket/{ticket_id}"}),
        encoding="utf-8",
    )
    (run_dir / "ticket.md").write_text(f"# {ticket_id}\n\n{body}\n", encoding="utf-8")


def _seed_all_green(db_path, ticket_id: str) -> None:
    _sqlite_db.upsert_ticket_intelligence(
        db_path, ticket_id, analysis_status="completed", requires_human_plan_review=0
    )
    _sqlite_db.upsert_ticket_readiness(db_path, ticket_id, readiness_status="ready_candidate")
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


# ── Happy path ────────────────────────────────────────────────────────────

def test_eligibility_returns_ready_to_take_when_all_pass(tmp_path):
    _make_ticket(tmp_path, "T001")
    app = _make_app(tmp_path)
    _seed_all_green(app.state.db_path, "T001")

    client = TestClient(app)
    r = client.get("/tickets/T001/eligibility")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ticket_id"] == "T001"
    assert body["ready_to_take"] is True
    assert body["status"] == "READY_TO_TAKE"
    assert body["blocking_step"] is None
    assert set(body["checks"].keys()) == {
        "intelligence", "dependencies", "readiness", "rules", "approval",
    }


def test_eligibility_404_when_ticket_missing(tmp_path):
    (tmp_path / "runs").mkdir()
    app = _make_app(tmp_path)
    client = TestClient(app)
    r = client.get("/tickets/T404/eligibility")
    assert r.status_code == 404


# ── Documented scenarios ─────────────────────────────────────────────────

def test_eligibility_blocked_by_plan_approval(tmp_path):
    _make_ticket(tmp_path, "T002")
    app = _make_app(tmp_path)
    db = app.state.db_path
    _sqlite_db.upsert_ticket_intelligence(
        db, "T002", analysis_status="completed", requires_human_plan_review=1
    )
    _sqlite_db.upsert_ticket_readiness(db, "T002", readiness_status="ready_candidate")
    _sqlite_db.upsert_ticket_rule_evaluation(
        db,
        ticket_id="T002",
        project_id="proj-a",
        eligibility_status="eligible",
        passed_rules=[],
        failed_rules=[],
        warnings=[],
        evaluated_at="2026-06-24T00:00:00Z",
    )

    client = TestClient(app)
    r = client.get("/tickets/T002/eligibility")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "WAITING_HUMAN_ACTION"
    assert body["blocking_step"] == "approval"
    assert body["next_action"] == "Approve plan review"


def test_eligibility_blocked_by_dependency(tmp_path, monkeypatch):
    _make_ticket(tmp_path, "T003", body="Depends on T001.")
    app = _make_app(tmp_path)
    _seed_all_green(app.state.db_path, "T003")

    # Stub merge resolution so we don't hit gh/git.
    import ticket_execution_eligibility as _elig

    class _Res:
        def __init__(self, status):
            self.status = status

    monkeypatch.setattr(_elig, "is_ticket_merged", lambda _r, t: _Res("not_merged"))

    client = TestClient(app)
    r = client.get("/tickets/T003/eligibility")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "DEPENDENCY_BLOCKED"
    assert body["blocking_step"] == "dependencies"
    assert body["checks"]["dependencies"]["unmet"] == ["T001"]


# ── Project-scoped mount ─────────────────────────────────────────────────

def test_eligibility_project_scoped_route(tmp_path):
    _make_ticket(tmp_path, "T004")
    app = _make_app(tmp_path)
    _seed_all_green(app.state.db_path, "T004")

    client = TestClient(app)
    r = client.get("/projects/proj-a/tickets/T004/eligibility")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["status"] == "READY_TO_TAKE"
    assert body["ticket_id"] == "T004"


# ── No-write contract ────────────────────────────────────────────────────

def test_eligibility_endpoint_does_not_persist(tmp_path):
    _make_ticket(tmp_path, "T005")
    app = _make_app(tmp_path)
    db = app.state.db_path
    _seed_all_green(db, "T005")

    before_readiness = _sqlite_db.get_ticket_readiness(db, "T005")

    client = TestClient(app)
    client.get("/tickets/T005/eligibility")
    client.get("/tickets/T005/eligibility")

    after_readiness = _sqlite_db.get_ticket_readiness(db, "T005")
    assert before_readiness == after_readiness


# ── No scheduler/daemon import ───────────────────────────────────────────

def test_eligibility_module_does_not_import_scheduler() -> None:
    """Static guard — the aggregator must not pull in execution code paths."""
    mod_paths = [
        Path(__file__).resolve().parents[1]
        / "tools" / "agent_runner" / "ticket_execution_eligibility.py",
        Path(__file__).resolve().parents[1]
        / "services" / "control_api" / "routes" / "eligibility.py",
    ]
    forbidden = ("run_ticket", "run_daemon", "supervisor")
    for path in mod_paths:
        src = path.read_text(encoding="utf-8")
        for symbol in forbidden:
            assert symbol not in src, (
                f"{path.name} must not reference {symbol!r} — eligibility is "
                "advisory and must not invoke the execution pipeline."
            )
