"""Integration tests for the Global Settings API (T215)."""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "agent_runner"))


def _load_sqlite_db_module():
    spec = importlib.util.spec_from_file_location(
        "_api_settings_runtime_db_sqlite",
        Path(__file__).resolve().parents[1] / "tools" / "agent_runner" / "runtime_db.py",
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


_sqlite_db = _load_sqlite_db_module()


@pytest.fixture(autouse=True)
def _isolate_env(monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    monkeypatch.delenv("DAEMON_MAX_WORKERS", raising=False)
    monkeypatch.delenv("AI_DEV_FACTORY_INTEL_TIMEOUT", raising=False)
    monkeypatch.delenv("AI_DEV_FACTORY_DISPATCHER_MODE", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)


@pytest.fixture(autouse=True)
def _restore_runtime_settings_binding():
    """Tests rebind ``runtime_settings.runtime_db`` to the isolated SQLite
    module; restore the original after each test so subsequent tests in the
    same process don't accidentally call SQLite helpers with a Postgres handle.
    """
    import services.control_api.routes.settings as _settings_route
    original = _settings_route._runtime_settings.runtime_db
    try:
        yield
    finally:
        _settings_route._runtime_settings.runtime_db = original


def _make_app(tmp_path: Path):
    from services.control_api.main import create_app
    import services.control_api.routes.settings as _settings_route

    app = create_app(project_root=tmp_path)
    isolated_db = tmp_path / ".runtime" / "adf-test-settings.sqlite"
    _sqlite_db.init_runtime_db(isolated_db)
    app.state.db_path = isolated_db

    # Re-bind the settings module's runtime_db dependency to the isolated
    # SQLite module so the test never accidentally hits a process-wide
    # Postgres handle.
    _settings_route._runtime_settings.runtime_db = _sqlite_db
    return app


def test_list_returns_one_entry_per_spec(tmp_path):
    from services.control_api.routes import settings as _settings_route

    client = TestClient(_make_app(tmp_path))
    r = client.get("/api/settings")
    assert r.status_code == 200
    body = r.json()
    keys = {row["key"] for row in body["settings"]}
    assert keys == set(_settings_route._runtime_settings.SETTING_SPECS.keys())


def test_get_unknown_key_returns_404(tmp_path):
    client = TestClient(_make_app(tmp_path))
    r = client.get("/api/settings/UNKNOWN_KEY")
    assert r.status_code == 404


def test_put_persists_value_and_source_switches_to_db(tmp_path):
    client = TestClient(_make_app(tmp_path))
    r = client.put("/api/settings/MAX_WORKERS", json={"value": "5"})
    assert r.status_code == 200
    body = r.json()
    assert body["value"] == 5
    assert body["source"] == "db"

    r = client.get("/api/settings/MAX_WORKERS")
    assert r.status_code == 200
    assert r.json()["value"] == 5
    assert r.json()["source"] == "db"


def test_delete_resets_to_env(tmp_path, monkeypatch):
    monkeypatch.setenv("DAEMON_MAX_WORKERS", "2")
    client = TestClient(_make_app(tmp_path))

    client.put("/api/settings/MAX_WORKERS", json={"value": "9"})
    r = client.delete("/api/settings/MAX_WORKERS")
    assert r.status_code == 204

    r = client.get("/api/settings/MAX_WORKERS")
    body = r.json()
    assert body["value"] == 2
    assert body["source"] == "env"


def test_put_bad_int_returns_422(tmp_path):
    client = TestClient(_make_app(tmp_path))
    r = client.put("/api/settings/MAX_WORKERS", json={"value": "not-an-int"})
    assert r.status_code == 422


def test_put_unknown_key_returns_404(tmp_path):
    client = TestClient(_make_app(tmp_path))
    r = client.put("/api/settings/UNKNOWN_KEY", json={"value": "x"})
    assert r.status_code == 404


def test_sensitive_get_is_redacted(tmp_path):
    client = TestClient(_make_app(tmp_path))
    r = client.get("/api/settings/OPENAI_API_KEY")
    assert r.status_code == 200
    body = r.json()
    assert body["value"] in ("configured", "not_configured")
    assert body["is_sensitive"] is True
    assert body["editable"] is False


def test_sensitive_put_is_rejected(tmp_path):
    client = TestClient(_make_app(tmp_path))
    r = client.put("/api/settings/OPENAI_API_KEY", json={"value": "sk-test"})
    assert r.status_code == 403
    # The DB must never store a sensitive value.
    rows = _sqlite_db.list_runtime_settings(
        next(iter(
            [p for p in tmp_path.glob(".runtime/adf-test-settings.sqlite")]
        ))
    )
    assert all(row["key"] != "OPENAI_API_KEY" for row in rows)


def test_sensitive_status_reads_from_env(tmp_path, monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-xxx")
    client = TestClient(_make_app(tmp_path))
    r = client.get("/api/settings/OPENAI_API_KEY")
    body = r.json()
    assert body["value"] == "configured"
    assert body["source"] == "env"


def test_router_smoke_registered(tmp_path):
    client = TestClient(_make_app(tmp_path))
    r = client.get("/api/settings")
    assert r.status_code == 200
