"""Postgres-backed claim helpers for the ticket pipeline."""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest

pytest.importorskip("psycopg")

_TOOLS = Path(__file__).parent.parent / "tools" / "agent_runner"
sys.path.insert(0, str(_TOOLS))


def _load_pg_modules():
    pg_spec = importlib.util.spec_from_file_location(
        "runtime_db_pg_claim_test",
        _TOOLS / "runtime_db_pg.py",
    )
    pg_mod = importlib.util.module_from_spec(pg_spec)  # type: ignore[arg-type]
    pg_spec.loader.exec_module(pg_mod)  # type: ignore[union-attr]

    db_spec = importlib.util.spec_from_file_location(
        "runtime_db_claim_test",
        _TOOLS / "runtime_db.py",
    )
    db_mod = importlib.util.module_from_spec(db_spec)  # type: ignore[arg-type]
    old = os.environ.get("RUNTIME_DB_BACKEND")
    os.environ["RUNTIME_DB_BACKEND"] = "postgres"
    os.environ.setdefault("RUNTIME_DB_HOST", "127.0.0.1")
    os.environ.setdefault("RUNTIME_DB_PORT", "5432")
    os.environ.setdefault("RUNTIME_DB_USER", "adf")
    os.environ.setdefault("RUNTIME_DB_PASSWORD", "adf")
    os.environ.setdefault("RUNTIME_DB_NAME", "adf")
    os.environ["PROJECT_NAME"] = "claim-pipeline-test"
    try:
        db_spec.loader.exec_module(db_mod)  # type: ignore[union-attr]
    finally:
        if old is None:
            os.environ.pop("RUNTIME_DB_BACKEND", None)
        else:
            os.environ["RUNTIME_DB_BACKEND"] = old
    return db_mod, pg_mod


_db, _pg = _load_pg_modules()


@pytest.fixture()
def handle():
    h = _db.get_db_path("claim-pipeline-test")
    _db.init_runtime_db(h)
    yield h
    with _pg._connect(h) as conn:
        conn.execute(
            "DELETE FROM ticket_intelligence WHERE project_id = %s",
            (h.project_id,),
        )
        conn.execute(
            "DELETE FROM ticket_readiness WHERE project_id = %s",
            (h.project_id,),
        )
        conn.execute(
            "DELETE FROM issue_intake WHERE project_id = %s",
            (h.project_id,),
        )


def test_claim_ticket_intelligence_pg(handle):
    assert _db.claim_ticket_intelligence(handle, "T900") is True
    row = _db.get_ticket_intelligence(handle, "T900")
    assert row["analysis_status"] == "running"
    assert _db.claim_ticket_intelligence(handle, "T900") is False


def test_claim_ticket_readiness_pg(handle):
    assert _db.claim_ticket_readiness(handle, "T901") is True
    row = _db.get_ticket_readiness(handle, "T901")
    assert row["readiness_status"] == "running"
    assert _db.claim_ticket_readiness(handle, "T901") is False


def test_record_intake_once_pg(handle):
    assert _db.record_intake_once(handle, 42, "T902", branch="ticket/T902") is True
    assert _db.record_intake_once(handle, 42, "T902", branch="ticket/T902") is False
