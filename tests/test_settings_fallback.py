"""T221 — invalid / non-positive settings fall back to a safe default.

Covers ``GITHUB_POLL_INTERVAL_SECONDS``, ``MAX_ISSUES_INTAKED_PER_POLL``,
``MAX_PARALLEL_TICKET_INTELLIGENCE``, ``MAX_PARALLEL_READINESS`` — the four
knobs added in T221. Bad values (``"0"``, ``""``, ``"abc"``) must resolve to
the documented safe default and emit exactly one warning per key.
"""

from __future__ import annotations

import importlib.util
import logging
import os
import sys
from pathlib import Path

import pytest

_TOOLS = Path(__file__).parent.parent / "tools" / "agent_runner"
sys.path.insert(0, str(_TOOLS))


def _load_sqlite_runtime_db():
    spec = importlib.util.spec_from_file_location(
        "_runtime_db_sqlite_settings_fallback",
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
    name = "_runtime_settings_test_fallback"
    spec = importlib.util.spec_from_file_location(name, _TOOLS / "runtime_settings.py")
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    sys.modules[name] = mod
    try:
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
    except Exception:
        sys.modules.pop(name, None)
        raise
    mod.runtime_db = rdb_module
    return mod


_db = _load_sqlite_runtime_db()
_rs = _load_runtime_settings(_db)


# Each entry: (setting key, safe-default used at call site, spec-default value)
T221_SETTINGS = [
    ("GITHUB_POLL_INTERVAL_SECONDS", 30, 5),
    ("MAX_ISSUES_INTAKED_PER_POLL", 1, 50),
    ("MAX_PARALLEL_TICKET_INTELLIGENCE", 1, 4),
    ("MAX_PARALLEL_READINESS", 1, 4),
]


@pytest.fixture()
def db(tmp_path: Path) -> Path:
    db_path = tmp_path / ".runtime" / "fallback.sqlite"
    _db.init_runtime_db(db_path)
    return db_path


@pytest.fixture(autouse=True)
def _clear_env(monkeypatch):
    for key, _, _ in T221_SETTINGS:
        monkeypatch.delenv(key, raising=False)
    _rs._warned_invalid_values.clear()


@pytest.mark.parametrize("bad_value", ["0", "abc"])
def test_invalid_env_falls_back_to_safe_default(db, monkeypatch, caplog, bad_value):
    for key, safe_default, _spec_default in T221_SETTINGS:
        monkeypatch.setenv(key, bad_value)
        _rs._warned_invalid_values.discard(key)
        with caplog.at_level(logging.WARNING, logger="runtime-settings"):
            got = _rs.get_setting_int_positive(db, key, safe_default)
        assert got == safe_default, f"{key} bad_value={bad_value!r} got={got!r}"
        matching = [
            r for r in caplog.records
            if key in r.getMessage() and "invalid value" in r.getMessage()
        ]
        assert len(matching) == 1, (
            f"expected exactly one warning for {key}, got "
            f"{[r.getMessage() for r in matching]}"
        )
        caplog.clear()


def test_empty_env_falls_back_to_spec_default(db, monkeypatch, caplog):
    for key, safe_default, spec_default in T221_SETTINGS:
        monkeypatch.setenv(key, "")
        _rs._warned_invalid_values.discard(key)
        with caplog.at_level(logging.WARNING, logger="runtime-settings"):
            got = _rs.get_setting_int_positive(db, key, safe_default)
        # Empty string is treated as "unset" (see runtime_settings._env_value),
        # so the spec default kicks in — no warning expected.
        assert got == spec_default, f"{key} got={got!r} expected={spec_default!r}"
        matching = [
            r for r in caplog.records if key in r.getMessage()
        ]
        assert matching == [], f"unexpected warnings for {key}: {matching}"
        caplog.clear()


def test_missing_env_returns_spec_default(db):
    for key, safe_default, spec_default in T221_SETTINGS:
        got = _rs.get_setting_int_positive(db, key, safe_default)
        assert got == spec_default


def test_valid_env_override_wins(db, monkeypatch):
    monkeypatch.setenv("MAX_PARALLEL_TICKET_INTELLIGENCE", "7")
    assert _rs.get_setting_int_positive(db, "MAX_PARALLEL_TICKET_INTELLIGENCE", 1) == 7


def test_warning_emitted_once_per_key(db, monkeypatch, caplog):
    monkeypatch.setenv("MAX_PARALLEL_READINESS", "abc")
    _rs._warned_invalid_values.discard("MAX_PARALLEL_READINESS")
    with caplog.at_level(logging.WARNING, logger="runtime-settings"):
        _rs.get_setting_int_positive(db, "MAX_PARALLEL_READINESS", 1)
        _rs.get_setting_int_positive(db, "MAX_PARALLEL_READINESS", 1)
    matching = [
        r for r in caplog.records if "MAX_PARALLEL_READINESS" in r.getMessage()
    ]
    assert len(matching) == 1
