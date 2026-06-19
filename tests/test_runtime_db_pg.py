"""Tests for the Postgres backend of the runtime store (runtime_db_pg).

The Postgres backend uses ONE database with project-scoped rows. These tests
cover, without a running server or psycopg installed (psycopg is imported
lazily, only when a real connection is opened):

- project_id resolution and the Path-compatible handle,
- backend selection wiring in runtime_db,
- project ISOLATION at the query level (every statement filters/sets project_id),
  proven with a fake connection that records SQL + params.
"""

import importlib.util
import sys
from pathlib import Path

import pytest

_AGENT_RUNNER = Path(__file__).parent.parent / "tools" / "agent_runner"
sys.path.insert(0, str(_AGENT_RUNNER))

import runtime_db_pg as pg  # noqa: E402


# ── project_id resolution ─────────────────────────────────────────────────────

def test_resolve_project_id_prefers_explicit_arg(monkeypatch):
    monkeypatch.setenv("PROJECT_NAME", "env-project")
    assert pg.resolve_project_id("explicit") == "explicit"


def test_resolve_project_id_falls_back_to_project_name_env(monkeypatch):
    monkeypatch.setenv("PROJECT_NAME", "demo-app")
    assert pg.resolve_project_id(None) == "demo-app"


def test_resolve_project_id_default(monkeypatch):
    monkeypatch.delenv("PROJECT_NAME", raising=False)
    assert pg.resolve_project_id(None) == "ai-dev-factory"


def test_single_database_name(monkeypatch):
    monkeypatch.setenv("RUNTIME_DB_NAME", "adf")
    assert pg.database_name() == "adf"
    # All projects share the one database — the handle's dbname never varies.
    assert pg.get_handle("a").dbname == pg.get_handle("b").dbname == "adf"


# ── PgHandle / get_handle ────────────────────────────────────────────────────

def test_pg_handle_quacks_like_path_and_carries_project(monkeypatch):
    monkeypatch.setenv("RUNTIME_DB_HOST", "db")
    handle = pg.get_handle("svc")
    assert handle is not None
    assert handle.exists() is True
    assert handle.project_id == "svc"
    desc = handle.describe()
    assert "backend=postgres" in desc and "project_id=svc" in desc and "host=db" in desc


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
    with pytest.raises(TypeError):
        mod.get_db_path("anything")  # SQLite get_db_path takes no project_id


def test_postgres_backend_rebinds_and_scopes_by_project(monkeypatch):
    monkeypatch.setenv("RUNTIME_DB_BACKEND", "postgres")
    monkeypatch.setenv("PROJECT_NAME", "ai-dev-factory")
    mod = _load_runtime_db_fresh()
    handle = mod.get_db_path("proj-x")
    assert type(handle).__name__ == "PgHandle"
    assert handle.exists() is True
    assert handle.project_id == "proj-x"
    # No project_id → falls back to PROJECT_NAME.
    assert mod.get_db_path().project_id == "ai-dev-factory"
    assert mod.check_and_recover_db(handle) is True


# ── project isolation at the query level (fake connection) ────────────────────

class _FakeCursor:
    def __init__(self, rows):
        self._rows = rows

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def fetchall(self):
        return list(self._rows)


class _FakeConn:
    """Records every (sql, params) and returns canned rows; context-manager safe."""

    def __init__(self, recorder, rows):
        self._recorder = recorder
        self._rows = rows

    def execute(self, sql, params=None):
        self._recorder.append((sql, params))
        return _FakeCursor(self._rows)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


@pytest.fixture()
def captured(monkeypatch):
    calls: list[tuple] = []
    rows: list = []

    def fake_connect(handle):
        return _FakeConn(calls, rows)

    monkeypatch.setattr(pg, "_connect", fake_connect)
    return calls, rows


def test_list_filters_by_project_id(captured):
    calls, _ = captured
    pg.list_ticket_runtime(pg.get_handle("proj-a"))
    sql, params = calls[-1]
    assert "project_id = %s" in sql
    assert params == ("proj-a",)


def test_insert_tags_rows_with_project_id(captured):
    calls, rows = captured  # rows empty → upsert takes the INSERT branch
    pg.upsert_ticket_runtime(pg.get_handle("proj-b"), "T1", state="CODING")
    # First statement is the existence SELECT scoped by project.
    select_sql, select_params = calls[0]
    assert "project_id = %s AND ticket_id = %s" in select_sql
    assert select_params == ("proj-b", "T1")
    # Second is the INSERT carrying project_id.
    insert_sql, insert_params = calls[1]
    assert insert_sql.strip().startswith("INSERT INTO ticket_runtime")
    assert "proj-b" in insert_params and "T1" in insert_params


def test_two_projects_are_isolated(captured):
    calls, _ = captured
    pg.list_workers(pg.get_handle("alpha"))
    pg.list_workers(pg.get_handle("beta"))
    assert calls[0][1] == ("alpha",)
    assert calls[1][1] == ("beta",)


def test_events_filter_by_project_and_ticket(captured):
    calls, _ = captured
    pg.list_runtime_events(pg.get_handle("proj-c"), ticket_id="T9", limit=5)
    sql, params = calls[-1]
    assert "project_id = %s AND ticket_id = %s" in sql
    assert params == ("proj-c", "T9", 5)
