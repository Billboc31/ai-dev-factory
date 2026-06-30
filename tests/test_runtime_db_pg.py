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


def test_case_c_postgres_never_falls_back_to_sqlite_when_psycopg_missing(monkeypatch):
    """Case C: backend=postgres but the Postgres backend cannot be initialised.

    Backend selection MUST stay postgres (never silently switch to SQLite) and
    the health/verify path MUST fail fast with a clear RuntimeError.
    """
    monkeypatch.setenv("RUNTIME_DB_BACKEND", "postgres")
    monkeypatch.setenv("PROJECT_NAME", "ai-dev-factory")
    # Make `import psycopg` raise ImportError everywhere (simulates "fails to load").
    monkeypatch.setitem(sys.modules, "psycopg", None)

    # Wiring is psycopg-free, so the module still imports — and stays postgres.
    mod = _load_runtime_db_fresh()
    handle = mod.get_db_path("proj")
    assert type(handle).__name__ == "PgHandle"  # NOT a SQLite Path — no fallback

    # Fail fast with a clear, psycopg-mentioning error; no SQLite degrade.
    with pytest.raises(RuntimeError, match="psycopg"):
        mod.verify_backend_available()
    with pytest.raises(RuntimeError, match="psycopg"):
        mod.healthcheck(handle)


def test_unknown_backend_is_rejected(monkeypatch):
    """An unrecognised backend value is a deterministic configuration error."""
    monkeypatch.setenv("RUNTIME_DB_BACKEND", "mysql")
    with pytest.raises(RuntimeError, match="unknown RUNTIME_DB_BACKEND"):
        _load_runtime_db_fresh()


# ── startup diagnostics (unambiguous backend banner) ─────────────────────────

def test_describe_backend_postgres_lines(monkeypatch):
    monkeypatch.setenv("RUNTIME_DB_BACKEND", "postgres")
    monkeypatch.setenv("RUNTIME_DB_HOST", "db")
    monkeypatch.setenv("RUNTIME_DB_NAME", "adf")
    monkeypatch.setenv("PROJECT_NAME", "ai-dev-factory")
    mod = _load_runtime_db_fresh()
    lines = mod.describe_backend()
    assert "runtime_db backend=postgres" in lines
    assert "runtime_db host=db" in lines
    assert "runtime_db database=adf" in lines
    assert "runtime_db project_id=ai-dev-factory" in lines


def test_describe_backend_sqlite_lines(monkeypatch):
    monkeypatch.delenv("RUNTIME_DB_BACKEND", raising=False)
    mod = _load_runtime_db_fresh()
    lines = mod.describe_backend()
    assert lines[0] == "runtime_db backend=sqlite"
    assert lines[1].startswith("runtime_db path=")


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


# ── T208 — ticket_intelligence lifecycle column parity with SQLite ────────────


def test_ticket_intelligence_ddl_declares_lifecycle_columns():
    """A freshly created ticket_intelligence table must carry the four lifecycle columns."""
    for col in ("started_at", "completed_at", "failed_at", "failure_origin"):
        # Each appears at least once in the CREATE TABLE block.
        assert col in pg._DDL


def test_ticket_intelligence_lifecycle_migration_is_idempotent_alter():
    """The migration block uses ADD COLUMN IF NOT EXISTS for every new column."""
    migration = pg._TICKET_INTELLIGENCE_LIFECYCLE_MIGRATION
    for col in ("started_at", "completed_at", "failed_at", "failure_origin"):
        # Each column has an ALTER ... ADD COLUMN IF NOT EXISTS entry.
        needle = f"ADD COLUMN IF NOT EXISTS {col}"
        assert needle in migration, f"missing idempotent ALTER for {col}"


def test_init_runtime_db_runs_lifecycle_migration(monkeypatch):
    """init_runtime_db must execute both the DDL and the lifecycle migration."""
    executed: list[str] = []

    class _Conn:
        def execute(self, sql, params=None):  # noqa: ARG002
            executed.append(sql)

        def __enter__(self):
            return self

        def __exit__(self, *exc):  # noqa: D401
            return False

    monkeypatch.setattr(pg, "_connect", lambda handle: _Conn())
    pg.init_runtime_db(pg.get_handle("proj-x"))

    assert any("CREATE TABLE IF NOT EXISTS ticket_intelligence" in s for s in executed)
    assert any("ADD COLUMN IF NOT EXISTS started_at" in s for s in executed)


# ── T218 — backlog batches / dependency analysis parity with SQLite ──────────


def test_backlog_ddl_declares_three_new_tables():
    """The three T218 tables must be in _DDL so init_runtime_db creates them."""
    for table in ("backlog_batches", "backlog_batch_tickets", "ticket_dependency_analysis"):
        assert f"CREATE TABLE IF NOT EXISTS {table}" in pg._DDL, f"missing table: {table}"


def test_backlog_ddl_carries_project_id_for_isolation():
    """Every new table must carry project_id and key on it for cross-project isolation."""
    # backlog_batches: composite PK starts with project_id
    assert "PRIMARY KEY (project_id, batch_id)" in pg._DDL
    # backlog_batch_tickets: composite PK + UNIQUE both scoped by project_id
    assert "PRIMARY KEY (project_id, batch_id, ticket_id)" in pg._DDL
    assert "UNIQUE (project_id, ticket_id)" in pg._DDL
    # ticket_dependency_analysis: composite PK starts with project_id
    assert "PRIMARY KEY (project_id, ticket_id, batch_id)" in pg._DDL


def test_insert_backlog_batch_tags_with_project_id(captured):
    calls, _ = captured
    pg.insert_backlog_batch(
        pg.get_handle("proj-a"),
        "batch-1",
        status="collecting",
        created_at="2026-06-30T15:00:00Z",
        last_activity_at="2026-06-30T15:00:00Z",
    )
    sql, params = calls[-1]
    assert sql.strip().startswith("INSERT INTO backlog_batches")
    assert "project_id" in sql
    assert params[0] == "proj-a"
    assert params[1] == "batch-1"


def test_list_backlog_batches_filters_by_project_id(captured):
    calls, _ = captured
    pg.list_backlog_batches(pg.get_handle("proj-b"))
    sql, params = calls[-1]
    assert "FROM backlog_batches WHERE project_id = %s" in sql
    assert params == ("proj-b",)


def test_list_backlog_batches_with_status_scopes_by_project(captured):
    calls, _ = captured
    pg.list_backlog_batches(pg.get_handle("proj-c"), status="collecting")
    sql, params = calls[-1]
    assert "WHERE project_id = %s AND status = %s" in sql
    assert params == ("proj-c", "collecting")


def test_update_backlog_batch_scopes_by_project(captured):
    calls, _ = captured
    pg.update_backlog_batch(
        pg.get_handle("proj-d"), "batch-2", status="frozen", frozen_at="2026-06-30T15:30:00Z"
    )
    sql, params = calls[-1]
    assert sql.strip().startswith("UPDATE backlog_batches")
    assert "status=%s" in sql and "frozen_at=%s" in sql
    assert "WHERE project_id=%s AND batch_id=%s" in sql
    # Trailing two parameters are (project_id, batch_id).
    assert params[-2:] == ["proj-d", "batch-2"]


def test_update_backlog_batch_with_no_fields_is_noop(captured):
    calls, _ = captured
    pg.update_backlog_batch(pg.get_handle("proj-d"), "batch-2")
    assert calls == []


def test_insert_backlog_batch_ticket_returns_true_when_inserted(monkeypatch):
    calls: list = []

    class _Cur:
        rowcount = 1

    class _Conn:
        def execute(self, sql, params=None):
            calls.append((sql, params))
            return _Cur()

        def __enter__(self):
            return self

        def __exit__(self, *exc):  # noqa: D401
            return False

    monkeypatch.setattr(pg, "_connect", lambda handle: _Conn())
    ok = pg.insert_backlog_batch_ticket(
        pg.get_handle("proj-e"), "batch-3", "T123", "2026-06-30T15:00:00Z"
    )
    assert ok is True
    sql, params = calls[-1]
    assert "ON CONFLICT DO NOTHING" in sql
    assert params[0] == "proj-e"


def test_insert_backlog_batch_ticket_returns_false_on_conflict(monkeypatch):
    """ON CONFLICT DO NOTHING → rowcount==0 → helper returns False (mirrors SQLite contract)."""

    class _Cur:
        rowcount = 0

    class _Conn:
        def execute(self, sql, params=None):  # noqa: ARG002
            return _Cur()

        def __enter__(self):
            return self

        def __exit__(self, *exc):  # noqa: D401
            return False

    monkeypatch.setattr(pg, "_connect", lambda handle: _Conn())
    assert (
        pg.insert_backlog_batch_ticket(
            pg.get_handle("proj-f"), "batch-4", "T456", "2026-06-30T15:00:00Z"
        )
        is False
    )


def test_list_backlog_batch_ticket_ids_scopes_by_project(captured):
    calls, rows = captured
    rows.append({"ticket_id": "T1"})
    out = pg.list_backlog_batch_ticket_ids(pg.get_handle("proj-g"), "batch-5")
    sql, params = calls[-1]
    assert "WHERE project_id = %s AND batch_id = %s" in sql
    assert params == ("proj-g", "batch-5")
    assert out == ["T1"]


def test_get_batch_for_ticket_scopes_by_project(captured):
    calls, rows = captured
    rows.append({"batch_id": "batch-6"})
    out = pg.get_batch_for_ticket(pg.get_handle("proj-h"), "T789")
    sql, params = calls[-1]
    assert "WHERE project_id = %s AND ticket_id = %s" in sql
    assert params == ("proj-h", "T789")
    assert out == "batch-6"


def test_get_batch_for_ticket_returns_none_when_missing(captured):
    calls, _ = captured  # rows empty
    assert pg.get_batch_for_ticket(pg.get_handle("proj-h"), "T-missing") is None
    assert "WHERE project_id = %s AND ticket_id = %s" in calls[-1][0]


def test_upsert_dependency_analysis_persists_and_scopes(captured):
    calls, _ = captured
    pg.upsert_dependency_analysis(
        pg.get_handle("proj-i"),
        ticket_id="T1",
        batch_id="batch-7",
        depends_on=["T0"],
        blocks=["T2"],
        parallel_group=None,
        conflicting_tickets=[],
        execution_phase="bootstrap",
        relationship_classifications=[{"target": "T0", "type": "HARD_DEPENDENCY"}],
        analyzed_at="2026-06-30T16:00:00Z",
    )
    sql, params = calls[-1]
    assert sql.strip().startswith("INSERT INTO ticket_dependency_analysis")
    assert "ON CONFLICT (project_id, ticket_id, batch_id) DO UPDATE" in sql
    # JSON fields must be serialised before binding.
    import json as _json
    assert _json.loads(params[3]) == ["T0"]  # depends_on_json
    assert _json.loads(params[4]) == ["T2"]  # blocks_json
    assert _json.loads(params[6]) == []  # conflicting_tickets_json
    assert params[0] == "proj-i"


def test_get_dependency_analysis_decodes_json_lists(captured):
    calls, rows = captured
    import json as _json
    rows.append(
        {
            "project_id": "proj-j",
            "ticket_id": "T1",
            "batch_id": "batch-8",
            "depends_on_json": _json.dumps(["T0"]),
            "blocks_json": _json.dumps([]),
            "parallel_group": None,
            "conflicting_tickets_json": _json.dumps([]),
            "execution_phase": "bootstrap",
            "relationship_classifications_json": _json.dumps([]),
            "analyzed_at": "2026-06-30T16:00:00Z",
        }
    )
    out = pg.get_dependency_analysis(pg.get_handle("proj-j"), "T1", "batch-8")
    sql, params = calls[-1]
    assert "WHERE project_id = %s AND ticket_id = %s AND batch_id = %s" in sql
    assert params == ("proj-j", "T1", "batch-8")
    assert out is not None
    assert out["depends_on"] == ["T0"]
    assert out["blocks"] == []
    assert out["conflicting_tickets"] == []
    assert out["relationship_classifications"] == []


def test_get_dependency_analysis_latest_when_batch_omitted(captured):
    calls, _ = captured
    pg.get_dependency_analysis(pg.get_handle("proj-k"), "T1")
    sql, params = calls[-1]
    assert "ORDER BY analyzed_at DESC LIMIT 1" in sql
    assert "WHERE project_id = %s AND ticket_id = %s" in sql
    assert params == ("proj-k", "T1")


# ── T218 — runtime_db rebind block must expose the 9 new helpers ─────────────


def test_runtime_db_postgres_rebind_exposes_backlog_helpers(monkeypatch):
    """In postgres mode, runtime_db.<helper> must be the PG implementation."""
    monkeypatch.setenv("RUNTIME_DB_BACKEND", "postgres")
    monkeypatch.setenv("PROJECT_NAME", "ai-dev-factory")
    mod = _load_runtime_db_fresh()
    for name in (
        "insert_backlog_batch",
        "get_backlog_batch",
        "list_backlog_batches",
        "update_backlog_batch",
        "insert_backlog_batch_ticket",
        "list_backlog_batch_ticket_ids",
        "get_batch_for_ticket",
        "upsert_dependency_analysis",
        "get_dependency_analysis",
    ):
        helper = getattr(mod, name)
        # Source module of the rebound symbol is runtime_db_pg, not runtime_db.
        assert helper.__module__ == "runtime_db_pg", (
            f"{name} is not rebound to the Postgres backend "
            f"(__module__={helper.__module__})"
        )
