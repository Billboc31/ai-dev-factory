"""Unit tests for control_api.create_app() — runtime_base_root resolution."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

# Import at module level so the module-level `app = create_app()` runs once
# during test collection (before any monkeypatch is active), leaving the module
# cached in sys.modules. Individual tests then call create_app() directly.
from services.control_api.main import create_app  # noqa: E402


def test_create_app_raises_only_for_explicit_runtime_base_root_filesystem_root(
    tmp_path, monkeypatch
):
    """Only an explicit RUNTIME_BASE_ROOT=/ is rejected at startup."""
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    monkeypatch.setenv("RUNTIME_BASE_ROOT", "/")
    with pytest.raises(RuntimeError, match="filesystem root"):
        create_app(project_root=tmp_path)


def test_create_app_starts_with_runtime_root_slash_runtime(tmp_path, monkeypatch):
    """AI_DEV_FACTORY_RUNTIME_ROOT=/runtime must NOT crash the API (Docker case)."""
    monkeypatch.delenv("RUNTIME_BASE_ROOT", raising=False)
    monkeypatch.setenv("AI_DEV_FACTORY_RUNTIME_ROOT", "/runtime")
    app = create_app(project_root=tmp_path)
    # No multi-project base derived from a '/'-parent runtime root.
    assert app.state.runtime_base_root is None
    assert app.state.runtime_root == Path("/runtime")


def test_create_app_starts_without_runtime_base_root(tmp_path, monkeypatch):
    """Absence of RUNTIME_BASE_ROOT does not break startup (UI stays available)."""
    monkeypatch.delenv("RUNTIME_BASE_ROOT", raising=False)
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    app = create_app(project_root=tmp_path)
    assert app.state.runtime_base_root is None


def test_create_app_uses_explicit_runtime_base_root(tmp_path, monkeypatch):
    """A valid RUNTIME_BASE_ROOT is resolved and stored on app.state."""
    base = tmp_path / "multi-runtime"
    monkeypatch.setenv("RUNTIME_BASE_ROOT", str(base))
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    app = create_app(project_root=tmp_path)
    assert app.state.runtime_base_root == base.resolve()


def test_settings_router_is_registered(tmp_path, monkeypatch):
    """T215 — /api/settings router is mounted and reachable.

    Loads a private SQLite runtime_db so the smoke test never reaches a
    process-wide Postgres handle that may not be available in CI, and
    restores the runtime_settings module binding on exit so subsequent
    tests in the same process are not contaminated.
    """
    import importlib.util
    import os
    from fastapi.testclient import TestClient

    monkeypatch.delenv("RUNTIME_BASE_ROOT", raising=False)
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)

    saved_backend = os.environ.get("RUNTIME_DB_BACKEND")
    os.environ["RUNTIME_DB_BACKEND"] = "sqlite"
    try:
        spec = importlib.util.spec_from_file_location(
            "_smoke_runtime_db_sqlite",
            Path(__file__).resolve().parents[1] / "tools" / "agent_runner" / "runtime_db.py",
        )
        sqlite_db = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(sqlite_db)
    finally:
        if saved_backend is None:
            os.environ.pop("RUNTIME_DB_BACKEND", None)
        else:
            os.environ["RUNTIME_DB_BACKEND"] = saved_backend

    import services.control_api.routes.settings as _settings_route
    original_binding = _settings_route._runtime_settings.runtime_db
    try:
        app = create_app(project_root=tmp_path)
        isolated_db = tmp_path / ".runtime" / "adf-smoke.sqlite"
        sqlite_db.init_runtime_db(isolated_db)
        app.state.db_path = isolated_db
        _settings_route._runtime_settings.runtime_db = sqlite_db
        client = TestClient(app)
        r = client.get("/api/settings")
        assert r.status_code == 200
    finally:
        _settings_route._runtime_settings.runtime_db = original_binding
