"""Integration tests for sandbox API routes using FastAPI TestClient."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _ok_compose(*args, **kwargs):
    m = MagicMock()
    m.returncode = 0
    m.stdout = "done"
    m.stderr = ""
    return m


def _make_app(tmp_path: Path):
    from services.control_api.main import create_app
    from services.control_api.services.sandbox_manager import SandboxManager

    proj = tmp_path / "myproject"
    proj.mkdir()
    (proj / ".git").mkdir()

    app = create_app(project_root=proj, projects_root=tmp_path)
    # Wire in a sandbox manager backed by tmp_path so tests are isolated
    app.state._sandbox_manager = SandboxManager(sandboxes_dir=tmp_path / "sandboxes")
    return app


def test_create_sandbox_returns_201(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    from fastapi.testclient import TestClient

    app = _make_app(tmp_path)
    client = TestClient(app)
    r = client.post("/sandboxes", json={"ticket_id": "T001", "project_root": "/project"})
    assert r.status_code == 201
    data = r.json()
    assert data["ticket_id"] == "T001"
    assert data["slot"] >= 1
    assert "web" in data["ports"]
    assert data["ports"]["web"] != 3000


def test_list_sandboxes_empty(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    from fastapi.testclient import TestClient

    app = _make_app(tmp_path)
    client = TestClient(app)
    r = client.get("/sandboxes")
    assert r.status_code == 200
    assert r.json() == []


def test_list_sandboxes_populated(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    from fastapi.testclient import TestClient

    app = _make_app(tmp_path)
    client = TestClient(app)
    client.post("/sandboxes", json={"ticket_id": "T001", "project_root": "/project"})
    client.post("/sandboxes", json={"ticket_id": "T002", "project_root": "/project"})
    r = client.get("/sandboxes")
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_get_sandbox_status(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    from fastapi.testclient import TestClient

    app = _make_app(tmp_path)
    client = TestClient(app)
    created = client.post("/sandboxes", json={"ticket_id": "T001", "project_root": "/project"}).json()
    sandbox_id = created["id"]

    r = client.get(f"/sandboxes/{sandbox_id}")
    assert r.status_code == 200
    assert r.json()["id"] == sandbox_id


def test_get_sandbox_status_unknown_returns_404(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    from fastapi.testclient import TestClient

    app = _make_app(tmp_path)
    client = TestClient(app)
    r = client.get("/sandboxes/doesnotexist")
    assert r.status_code == 404


def test_start_stop_sequence(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    from fastapi.testclient import TestClient

    app = _make_app(tmp_path)
    client = TestClient(app)
    created = client.post("/sandboxes", json={"ticket_id": "T001", "project_root": "/project"}).json()
    sandbox_id = created["id"]

    with patch("services.control_api.services.sandbox_manager.subprocess.run", side_effect=_ok_compose):
        r = client.post(f"/sandboxes/{sandbox_id}/start")
        assert r.status_code == 200
        assert r.json()["status"] == "running"

        r = client.post(f"/sandboxes/{sandbox_id}/stop")
        assert r.status_code == 200
        assert r.json()["status"] == "stopped"


def test_destroy_removes_sandbox(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    from fastapi.testclient import TestClient

    app = _make_app(tmp_path)
    client = TestClient(app)
    created = client.post("/sandboxes", json={"ticket_id": "T001", "project_root": "/project"}).json()
    sandbox_id = created["id"]

    with patch("services.control_api.services.sandbox_manager.subprocess.run", side_effect=_ok_compose):
        r = client.delete(f"/sandboxes/{sandbox_id}")
        assert r.status_code == 204

    r = client.get(f"/sandboxes/{sandbox_id}")
    assert r.status_code == 404


def test_destroy_releases_port(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    from fastapi.testclient import TestClient

    app = _make_app(tmp_path)
    client = TestClient(app)
    s1 = client.post("/sandboxes", json={"ticket_id": "T001", "project_root": "/project"}).json()
    slot1 = s1["slot"]

    with patch("services.control_api.services.sandbox_manager.subprocess.run", side_effect=_ok_compose):
        client.delete(f"/sandboxes/{s1['id']}")

    s2 = client.post("/sandboxes", json={"ticket_id": "T002", "project_root": "/project"}).json()
    assert s2["slot"] == slot1


def test_logs_endpoint_returns_text(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    from fastapi.testclient import TestClient

    app = _make_app(tmp_path)
    client = TestClient(app)
    created = client.post("/sandboxes", json={"ticket_id": "T001", "project_root": "/project"}).json()
    sandbox_id = created["id"]

    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "container log line\n"
    mock_result.stderr = ""
    with patch("services.control_api.services.sandbox_manager.subprocess.run", return_value=mock_result):
        r = client.get(f"/sandboxes/{sandbox_id}/logs")
    assert r.status_code == 200
    assert "container log line" in r.json()["logs"]


def test_cleanup_endpoint(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    from fastapi.testclient import TestClient

    app = _make_app(tmp_path)
    client = TestClient(app)
    r = client.post("/sandboxes/cleanup", params={"max_age_days": 0})
    assert r.status_code == 200
    assert "destroyed" in r.json()


def test_restart_endpoint_200(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    from fastapi.testclient import TestClient

    app = _make_app(tmp_path)
    client = TestClient(app)
    created = client.post("/sandboxes", json={"ticket_id": "T001", "project_root": "/project"}).json()
    sandbox_id = created["id"]

    with patch("services.control_api.services.sandbox_manager.subprocess.run", side_effect=_ok_compose):
        r = client.post(f"/sandboxes/{sandbox_id}/restart")
    assert r.status_code == 200
    assert r.json()["status"] == "running"


def test_restart_endpoint_404(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    from fastapi.testclient import TestClient

    app = _make_app(tmp_path)
    client = TestClient(app)
    with patch("services.control_api.services.sandbox_manager.subprocess.run", side_effect=_ok_compose):
        r = client.post("/sandboxes/doesnotexist/restart")
    assert r.status_code == 404


def test_refresh_endpoint_200(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    from fastapi.testclient import TestClient

    app = _make_app(tmp_path)
    client = TestClient(app)
    created = client.post("/sandboxes", json={"ticket_id": "T001", "project_root": "/project"}).json()
    sandbox_id = created["id"]

    r = client.post(f"/sandboxes/{sandbox_id}/refresh")
    assert r.status_code == 200
    assert r.json()["id"] == sandbox_id


def test_refresh_endpoint_404(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    from fastapi.testclient import TestClient

    app = _make_app(tmp_path)
    client = TestClient(app)
    r = client.post("/sandboxes/doesnotexist/refresh")
    assert r.status_code == 404
