"""Per-project DB path resolution for ticket intelligence (T206)."""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest

_TOOLS = Path(__file__).parent.parent / "tools" / "agent_runner"
sys.path.insert(0, str(_TOOLS))


def _load_sqlite_runtime_db():
    """Load runtime_db in SQLite mode regardless of current RUNTIME_DB_BACKEND env."""
    spec = importlib.util.spec_from_file_location(
        "_runtime_db_sqlite_resolution_test",
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


_db = _load_sqlite_runtime_db()


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    monkeypatch.delenv("RUNTIME_BASE_ROOT", raising=False)


def test_get_db_path_with_project_id_uses_runtime_root(monkeypatch, tmp_path):
    monkeypatch.setenv("AI_DEV_FACTORY_RUNTIME_ROOT", str(tmp_path))
    result = _db.get_db_path(project_id="P1")
    assert result == tmp_path / "P1" / ".runtime" / "ai-dev-factory.sqlite"


def test_get_db_path_with_project_id_prefers_runtime_base_root(monkeypatch, tmp_path):
    base = tmp_path / "base"
    other = tmp_path / "other"
    monkeypatch.setenv("AI_DEV_FACTORY_RUNTIME_ROOT", str(other))
    monkeypatch.setenv("RUNTIME_BASE_ROOT", str(base))
    result = _db.get_db_path(project_id="P1")
    assert result == base / "P1" / ".runtime" / "ai-dev-factory.sqlite"


def test_get_db_path_without_project_id_unchanged(monkeypatch, tmp_path):
    monkeypatch.setenv("AI_DEV_FACTORY_RUNTIME_ROOT", str(tmp_path))
    result = _db.get_db_path()
    assert result == tmp_path / ".runtime" / "ai-dev-factory.sqlite"


def test_resolve_db_path_for_project_explicit_root_wins(monkeypatch, tmp_path):
    explicit = tmp_path / "explicit-runtime"
    monkeypatch.setenv("AI_DEV_FACTORY_RUNTIME_ROOT", str(tmp_path / "env"))
    result = _db.resolve_db_path_for_project("P1", project_runtime_root=explicit)
    assert result == explicit / ".runtime" / "ai-dev-factory.sqlite"


def test_resolve_db_path_for_project_env_fallback(monkeypatch, tmp_path):
    monkeypatch.setenv("AI_DEV_FACTORY_RUNTIME_ROOT", str(tmp_path))
    result = _db.resolve_db_path_for_project("P1")
    assert result == tmp_path / "P1" / ".runtime" / "ai-dev-factory.sqlite"


def test_resolve_db_path_for_project_legacy_when_no_project(monkeypatch, tmp_path):
    monkeypatch.setenv("AI_DEV_FACTORY_RUNTIME_ROOT", str(tmp_path))
    result = _db.resolve_db_path_for_project(None)
    assert result == tmp_path / ".runtime" / "ai-dev-factory.sqlite"
