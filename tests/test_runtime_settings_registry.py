"""Registry-level tests for runtime_settings (T215)."""

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
        "_runtime_db_sqlite_test_registry",
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


def _load_runtime_settings(rdb_module):
    name = "_runtime_settings_test"
    spec = importlib.util.spec_from_file_location(
        name,
        _TOOLS / "runtime_settings.py",
    )
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    # Register in sys.modules BEFORE exec_module so dataclass introspection
    # on Python 3.13+ can resolve the owning module while creating frozen
    # dataclasses (it calls ``sys.modules.get(cls.__module__).__dict__``).
    sys.modules[name] = mod
    try:
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
    except Exception:
        sys.modules.pop(name, None)
        raise
    # Re-bind the runtime_db dependency to the isolated SQLite module so
    # tests don't depend on the process-wide backend selection.
    mod.runtime_db = rdb_module
    return mod


_db = _load_sqlite_runtime_db()
_rs = _load_runtime_settings(_db)


@pytest.fixture()
def db(tmp_path: Path) -> Path:
    db_path = tmp_path / ".runtime" / "test.sqlite"
    _db.init_runtime_db(db_path)
    return db_path


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    # Strip every env var the registry may consult so tests are deterministic.
    for spec in _rs.SETTING_SPECS.values():
        if spec.env_var:
            monkeypatch.delenv(spec.env_var, raising=False)


def test_get_setting_falls_back_to_default(db: Path) -> None:
    assert _rs.get_setting(db, "MAX_WORKERS") == 1
    assert _rs.get_setting(db, "INTELLIGENCE_TIMEOUT_SECONDS") == 120
    assert _rs.get_setting(db, "DISPATCHER_ENABLED") == "off"


def test_get_setting_reads_env_when_no_db_row(db: Path, monkeypatch) -> None:
    monkeypatch.setenv("DAEMON_MAX_WORKERS", "3")
    assert _rs.get_setting(db, "MAX_WORKERS") == 3


def test_get_setting_db_overrides_env(db: Path, monkeypatch) -> None:
    monkeypatch.setenv("DAEMON_MAX_WORKERS", "3")
    _rs.set_setting(db, "MAX_WORKERS", "7")
    assert _rs.get_setting(db, "MAX_WORKERS") == 7


def test_set_setting_coerces_to_value_type(db: Path) -> None:
    row = _rs.set_setting(db, "MAX_WORKERS", "9")
    assert row["value"] == 9
    assert row["value_type"] == "int"
    assert row["source"] == "db"


def test_set_setting_rejects_bad_int(db: Path) -> None:
    with pytest.raises(ValueError):
        _rs.set_setting(db, "MAX_WORKERS", "not-an-int")


def test_set_setting_rejects_unknown_key(db: Path) -> None:
    with pytest.raises(_rs.UnknownSettingError):
        _rs.set_setting(db, "UNKNOWN_KEY", "x")


def test_set_setting_rejects_sensitive(db: Path) -> None:
    with pytest.raises(_rs.SensitiveSettingWriteError):
        _rs.set_setting(db, "OPENAI_API_KEY", "sk-test")


def test_delete_setting_restores_env_or_default(db: Path, monkeypatch) -> None:
    monkeypatch.setenv("DAEMON_MAX_WORKERS", "4")
    _rs.set_setting(db, "MAX_WORKERS", "8")
    assert _rs.get_setting(db, "MAX_WORKERS") == 8
    _rs.delete_setting(db, "MAX_WORKERS")
    assert _rs.get_setting(db, "MAX_WORKERS") == 4
    monkeypatch.delenv("DAEMON_MAX_WORKERS")
    assert _rs.get_setting(db, "MAX_WORKERS") == 1


def test_resolve_effective_source_attribution(db: Path, monkeypatch) -> None:
    # default
    row = _rs.resolve_effective_setting(db, "MAX_WORKERS")
    assert row["source"] == "default"
    assert row["value"] == 1
    # env
    monkeypatch.setenv("DAEMON_MAX_WORKERS", "2")
    row = _rs.resolve_effective_setting(db, "MAX_WORKERS")
    assert row["source"] == "env"
    assert row["value"] == 2
    # db
    _rs.set_setting(db, "MAX_WORKERS", "5")
    row = _rs.resolve_effective_setting(db, "MAX_WORKERS")
    assert row["source"] == "db"
    assert row["value"] == 5
    assert row["editable"] is True


def test_resolve_sensitive_redacts_value(db: Path, monkeypatch) -> None:
    row = _rs.resolve_effective_setting(db, "OPENAI_API_KEY")
    assert row["value"] == "not_configured"
    assert row["editable"] is False
    assert row["source"] == "default"
    monkeypatch.setenv("OPENAI_API_KEY", "sk-secret")
    row = _rs.resolve_effective_setting(db, "OPENAI_API_KEY")
    assert row["value"] == "configured"
    assert row["source"] == "env"
    assert row["editable"] is False


def test_bool_coercion(db: Path) -> None:
    # Inject a temporary bool spec so we exercise the coercion path directly.
    bool_spec = _rs.SettingSpec(
        key="TEST_FLAG",
        value_type="bool",
        description="test flag",
        default=False,
        env_var="TEST_FLAG_ENV",
    )
    _rs.SETTING_SPECS["TEST_FLAG"] = bool_spec
    try:
        row = _rs.set_setting(db, "TEST_FLAG", "true")
        assert row["value"] is True
        assert _rs.get_setting(db, "TEST_FLAG") is True
        _rs.set_setting(db, "TEST_FLAG", False)
        assert _rs.get_setting(db, "TEST_FLAG") is False
    finally:
        del _rs.SETTING_SPECS["TEST_FLAG"]
        _rs.delete_setting.__wrapped__ if hasattr(_rs.delete_setting, "__wrapped__") else None  # no-op
        try:
            _db.delete_runtime_setting(db, "TEST_FLAG")
        except Exception:
            pass


def test_list_effective_settings_returns_one_per_spec(db: Path) -> None:
    rows = _rs.list_effective_settings(db)
    keys = {r["key"] for r in rows}
    assert keys == set(_rs.SETTING_SPECS.keys())
