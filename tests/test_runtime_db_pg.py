"""Tests for the Postgres backend of the runtime store (runtime_db_pg).

These tests exercise the pure, connection-free logic (database-name resolution,
the Path-compatible handle) and the backend-selection wiring in runtime_db.
They do NOT require a running Postgres server or the psycopg package — psycopg
is imported lazily, only when a real connection is opened.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

_AGENT_RUNNER = Path(__file__).parent.parent / "tools" / "agent_runner"
sys.path.insert(0, str(_AGENT_RUNNER))

import runtime_db_pg as pg  # noqa: E402


# ── db_name_for ───────────────────────────────────────────────────────────────

def test_db_name_for_sanitises_project_id():
    assert pg.db_name_for("ai-dev-factory") == "adf_ai_dev_factory"
    assert pg.db_name_for("My.Project/01") == "adf_my_project_01"


def test_db_name_for_falls_back_to_project_name_env(monkeypatch):
    monkeypatch.setenv("PROJECT_NAME", "demo-app")
    assert pg.db_name_for(None) == "adf_demo_app"


def test_db_name_for_falls_back_to_maintenance_db(monkeypatch):
    monkeypatch.delenv("PROJECT_NAME", raising=False)
    monkeypatch.setenv("RUNTIME_DB_NAME", "maint")
    assert pg.db_name_for(None) == "maint"


# ── PgHandle / get_handle ────────────────────────────────────────────────────

def test_pg_handle_quacks_like_path():
    handle = pg.get_handle("svc")
    # Callers do `if handle is None or not handle.exists()` — must be truthy.
    assert handle is not None
    assert handle.exists() is True
    assert handle.dbname == "adf_svc"
    assert "adf_svc" in str(handle)


# ── backend selection in runtime_db ──────────────────────────────────────────

def _load_runtime_db_fresh():
    spec = importlib.util.spec_from_file_location(
        "_rdb_pg_test", _AGENT_RUNNER / "runtime_db.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_default_backend_is_sqlite(monkeypatch):
    monkeypatch.delenv("RUNTIME_DB_BACKEND", raising=False)
    mod = _load_runtime_db_fresh()
    # SQLite get_db_path takes no project_id; calling with one must fail.
    with pytest.raises(TypeError):
        mod.get_db_path("anything")


def test_postgres_backend_rebinds_public_api(monkeypatch):
    monkeypatch.setenv("RUNTIME_DB_BACKEND", "postgres")
    monkeypatch.setenv("PROJECT_NAME", "ai-dev-factory")
    mod = _load_runtime_db_fresh()
    handle = mod.get_db_path("proj-x")
    # runtime_db loads runtime_db_pg as a separate module instance, so compare by
    # class name + behaviour rather than identity.
    assert type(handle).__name__ == "PgHandle"
    assert handle.exists() is True
    assert handle.dbname == "adf_proj_x"
    # No project_id → falls back to PROJECT_NAME.
    assert mod.get_db_path().dbname == "adf_ai_dev_factory"
    # check_and_recover_db is a no-op for Postgres and must report healthy.
    assert mod.check_and_recover_db(handle) is True
