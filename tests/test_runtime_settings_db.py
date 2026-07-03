"""Persistence tests for runtime_settings (T215, SQLite backend)."""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest

_TOOLS = Path(__file__).parent.parent / "tools" / "agent_runner"
sys.path.insert(0, str(_TOOLS))


def _load_sqlite_runtime_db():
    spec = importlib.util.spec_from_file_location(
        "_runtime_db_sqlite_test_settings",
        _TOOLS / "runtime_db.py",
    )
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    old = os.environ.get("RUNTIME_DB_BACKEND")
    os.environ["RUNTIME_DB_BACKEND"] = "sqlite"
    try:
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
    finally:
        if old is None:
            os.environ.pop("RUNTIME_DB_BACKEND", None)
        else:
            os.environ["RUNTIME_DB_BACKEND"] = old
    return mod


_db = _load_sqlite_runtime_db()


@pytest.fixture()
def db(tmp_path: Path) -> Path:
    db_path = tmp_path / ".runtime" / "test.sqlite"
    _db.init_runtime_db(db_path)
    return db_path


def test_schema_creates_runtime_settings(db: Path) -> None:
    import sqlite3
    with sqlite3.connect(str(db)) as conn:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='runtime_settings'"
        ).fetchone()
    assert row is not None


def test_init_is_idempotent(db: Path) -> None:
    _db.init_runtime_db(db)
    _db.init_runtime_db(db)
    import sqlite3
    with sqlite3.connect(str(db)) as conn:
        cols = [r[1] for r in conn.execute("PRAGMA table_info('runtime_settings')")]
    assert cols.count("value") == 1
    assert cols.count("requires_restart") == 1


def test_list_runtime_settings_empty(db: Path) -> None:
    assert _db.list_runtime_settings(db) == []


def test_upsert_and_get_round_trip(db: Path) -> None:
    _db.upsert_runtime_setting(
        db,
        "MAX_WORKERS",
        value="5",
        value_type="int",
        description="Daemon worker pool size.",
        requires_restart=True,
        updated_by="alice",
    )
    row = _db.get_runtime_setting(db, "MAX_WORKERS")
    assert row is not None
    assert row["key"] == "MAX_WORKERS"
    assert row["value"] == "5"
    assert row["value_type"] == "int"
    assert row["scope"] == "global"
    assert row["description"] == "Daemon worker pool size."
    assert row["is_sensitive"] is False
    assert row["requires_restart"] is True
    assert row["updated_by"] == "alice"
    assert row["updated_at"]


def test_upsert_updates_existing(db: Path) -> None:
    _db.upsert_runtime_setting(db, "LOG_LEVEL", value="INFO", value_type="string")
    _db.upsert_runtime_setting(db, "LOG_LEVEL", value="DEBUG", value_type="string")
    row = _db.get_runtime_setting(db, "LOG_LEVEL")
    assert row["value"] == "DEBUG"
    rows = _db.list_runtime_settings(db)
    assert len(rows) == 1


def test_sensitive_flag_round_trip(db: Path) -> None:
    _db.upsert_runtime_setting(
        db,
        "FAKE_SECRET",
        value="redacted",
        value_type="secret",
        is_sensitive=True,
    )
    row = _db.get_runtime_setting(db, "FAKE_SECRET")
    assert row["is_sensitive"] is True


def test_delete_removes_row(db: Path) -> None:
    _db.upsert_runtime_setting(db, "LOG_LEVEL", value="INFO", value_type="string")
    _db.delete_runtime_setting(db, "LOG_LEVEL")
    assert _db.get_runtime_setting(db, "LOG_LEVEL") is None


def test_list_returns_rows_ordered(db: Path) -> None:
    _db.upsert_runtime_setting(db, "Z_KEY", value="z", value_type="string")
    _db.upsert_runtime_setting(db, "A_KEY", value="a", value_type="string")
    keys = [r["key"] for r in _db.list_runtime_settings(db)]
    assert keys == ["A_KEY", "Z_KEY"]


def test_resolve_daemon_max_workers_reads_setting(db: Path) -> None:
    import runtime_settings as rs

    assert rs.resolve_daemon_max_workers(db) == 1
    _db.upsert_runtime_setting(
        db, "MAX_WORKERS", value="5", value_type="int", requires_restart=True,
    )
    assert rs.resolve_daemon_max_workers(db) == 5
    _db.upsert_runtime_setting(db, "MAX_WORKERS", value="0", value_type="int")
    assert rs.resolve_daemon_max_workers(db) == 1
