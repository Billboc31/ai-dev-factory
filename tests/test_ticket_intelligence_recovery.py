"""Tests for ticket_intelligence_recovery (T206)."""

from __future__ import annotations

import datetime
import importlib.util
import os
import sys
import time
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

_TOOLS = Path(__file__).parent.parent / "tools" / "agent_runner"
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(_TOOLS))


def _load_sqlite_runtime_db():
    spec = importlib.util.spec_from_file_location(
        "_recovery_test_runtime_db_sqlite",
        _TOOLS / "runtime_db.py",
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


def _load_recovery_against(sqlite_db_mod):
    spec = importlib.util.spec_from_file_location(
        "_recovery_test_recovery_module",
        _TOOLS / "ticket_intelligence_recovery.py",
    )
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    # Bind the recovery module to the SQLite-only runtime_db so reaping does not
    # accidentally call the Postgres backend when tests run in a mixed env.
    mod.runtime_db = sqlite_db_mod
    return mod


_db = _load_sqlite_runtime_db()
_recovery = _load_recovery_against(_db)


@pytest.fixture()
def db(tmp_path: Path) -> Path:
    db_path = tmp_path / ".runtime" / "test.sqlite"
    _db.init_runtime_db(db_path)
    return db_path


def _set_updated_at(db_path: Path, ticket_id: str, updated_at_iso: str) -> None:
    """Backdate updated_at directly so we don't have to sleep for ten minutes."""
    import sqlite3
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(
            "UPDATE ticket_intelligence SET updated_at = ? WHERE ticket_id = ?",
            (updated_at_iso, ticket_id),
        )


def _iso(now: datetime.datetime) -> str:
    return now.strftime("%Y-%m-%dT%H:%M:%SZ")


def test_reaper_transitions_stale_queued_to_failed(db: Path) -> None:
    now = datetime.datetime(2026, 6, 23, 10, 0, 0, tzinfo=datetime.timezone.utc)
    _db.upsert_ticket_intelligence(db, "T001", analysis_status="queued")
    _set_updated_at(db, "T001", _iso(now - datetime.timedelta(seconds=601)))

    recovered = _recovery.reap_stale_intelligence(db, now=now)

    assert len(recovered) == 1
    assert recovered[0]["ticket_id"] == "T001"
    assert recovered[0]["previous_status"] == "queued"
    assert recovered[0]["age_seconds"] >= 600

    row = _db.get_ticket_intelligence(db, "T001")
    assert row["analysis_status"] == "failed"
    assert "queued" in (row["analysis_summary"] or "").lower()
    assert "auto-recovered" in (row["analysis_summary"] or "").lower()


def test_reaper_transitions_stale_running_to_failed(db: Path) -> None:
    now = datetime.datetime(2026, 6, 23, 10, 0, 0, tzinfo=datetime.timezone.utc)
    _db.upsert_ticket_intelligence(db, "T001", analysis_status="running")
    _set_updated_at(db, "T001", _iso(now - datetime.timedelta(seconds=901)))

    recovered = _recovery.reap_stale_intelligence(db, now=now)

    assert len(recovered) == 1
    assert recovered[0]["previous_status"] == "running"

    row = _db.get_ticket_intelligence(db, "T001")
    assert row["analysis_status"] == "failed"
    assert "running" in (row["analysis_summary"] or "").lower()


def test_reaper_leaves_fresh_rows_untouched(db: Path) -> None:
    now = datetime.datetime(2026, 6, 23, 10, 0, 0, tzinfo=datetime.timezone.utc)
    _db.upsert_ticket_intelligence(db, "Tfresh_queued", analysis_status="queued")
    _set_updated_at(db, "Tfresh_queued", _iso(now - datetime.timedelta(seconds=30)))
    _db.upsert_ticket_intelligence(db, "Tfresh_running", analysis_status="running")
    _set_updated_at(db, "Tfresh_running", _iso(now - datetime.timedelta(seconds=60)))

    recovered = _recovery.reap_stale_intelligence(db, now=now)
    assert recovered == []

    assert _db.get_ticket_intelligence(db, "Tfresh_queued")["analysis_status"] == "queued"
    assert _db.get_ticket_intelligence(db, "Tfresh_running")["analysis_status"] == "running"


def test_reaper_ignores_completed_and_failed(db: Path) -> None:
    now = datetime.datetime(2026, 6, 23, 10, 0, 0, tzinfo=datetime.timezone.utc)
    _db.upsert_ticket_intelligence(db, "Tdone", analysis_status="completed")
    _set_updated_at(db, "Tdone", _iso(now - datetime.timedelta(hours=2)))
    _db.upsert_ticket_intelligence(db, "Tfail", analysis_status="failed")
    _set_updated_at(db, "Tfail", _iso(now - datetime.timedelta(hours=2)))

    recovered = _recovery.reap_stale_intelligence(db, now=now)
    assert recovered == []


def test_reaper_skips_rows_with_unparseable_updated_at(db: Path) -> None:
    now = datetime.datetime(2026, 6, 23, 10, 0, 0, tzinfo=datetime.timezone.utc)
    _db.upsert_ticket_intelligence(db, "T001", analysis_status="queued")
    _set_updated_at(db, "T001", "not-a-date")

    recovered = _recovery.reap_stale_intelligence(db, now=now)
    assert recovered == []
    assert _db.get_ticket_intelligence(db, "T001")["analysis_status"] == "queued"


def test_reaper_returns_empty_when_db_missing(tmp_path: Path) -> None:
    recovered = _recovery.reap_stale_intelligence(tmp_path / "missing.sqlite")
    assert recovered == []


# ── GET endpoint triggers the reaper ──────────────────────────────────────────


def _make_ticket(tmp_path: Path, ticket_id: str) -> None:
    import json
    run_dir = tmp_path / "runs" / ticket_id
    run_dir.mkdir(parents=True)
    (run_dir / "state.json").write_text(
        json.dumps({"ticket_id": ticket_id, "state": "PLAN_APPROVED", "branch": "test"}),
        encoding="utf-8",
    )
    (run_dir / "ticket.md").write_text(f"# {ticket_id}\n\nbody\n", encoding="utf-8")


def _make_app(tmp_path: Path):
    import services.control_api.routes.intelligence as _intel_route
    from services.control_api.main import create_app

    app = create_app(project_root=tmp_path)
    isolated_db = tmp_path / ".runtime" / "adf-test.sqlite"
    _db.init_runtime_db(isolated_db)
    app.state.db_path = isolated_db

    # Rebind runtime_db and recovery so the route uses the SQLite test bindings
    # regardless of any postgres env in the running shell.
    _intel_route.runtime_db = _db
    _intel_route._recovery = _recovery
    return app


def test_get_intelligence_triggers_reaper(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    _make_ticket(tmp_path, "T001")
    app = _make_app(tmp_path)
    db_path = app.state.db_path

    now = datetime.datetime.now(datetime.timezone.utc)
    _db.upsert_ticket_intelligence(db_path, "T001", analysis_status="running")
    _set_updated_at(db_path, "T001", _iso(now - datetime.timedelta(seconds=1000)))

    client = TestClient(app)
    r = client.get("/tickets/T001/intelligence")
    assert r.status_code == 200
    body = r.json()
    assert body["analysis_status"] == "failed"
    assert "auto-recovered" in (body["analysis_summary"] or "").lower()
