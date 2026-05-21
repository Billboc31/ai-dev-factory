"""Integration tests for the deployer API routes."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _make_app(tmp_path: Path):
    from services.control_api.main import create_app

    proj = tmp_path / "myproject"
    proj.mkdir()
    (proj / ".git").mkdir()
    return create_app(project_root=proj, projects_root=tmp_path), proj


def test_deployer_status_no_profile(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    from fastapi.testclient import TestClient

    app, proj = _make_app(tmp_path)
    client = TestClient(app)
    r = client.get("/projects/myproject/deployer/status")
    assert r.status_code == 200
    data = r.json()
    assert data["state"] == "idle"
    assert data["project_id"] == "myproject"
    assert data["profile_present"] is False


def test_deployer_status_with_profile(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    from fastapi.testclient import TestClient

    app, proj = _make_app(tmp_path)
    ai_dir = proj / ".ai-dev-factory"
    ai_dir.mkdir()
    (ai_dir / "deploy.yml").write_text(
        "version: 1\nproject: myproject\nrequired_tools: []\ncomponents: []\n",
        encoding="utf-8",
    )
    client = TestClient(app)
    r = client.get("/projects/myproject/deployer/status")
    assert r.status_code == 200
    assert r.json()["profile_present"] is True


def test_deployer_status_unknown_project_returns_404(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    from fastapi.testclient import TestClient

    app, _ = _make_app(tmp_path)
    client = TestClient(app)
    r = client.get("/projects/no-such-project/deployer/status")
    assert r.status_code == 404


def test_deployer_scan_returns_docker_services(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    from fastapi.testclient import TestClient

    app, proj = _make_app(tmp_path)
    (proj / "docker-compose.yml").write_text(
        "services:\n  api:\n    image: python\n  web:\n    image: node\n",
        encoding="utf-8",
    )
    client = TestClient(app)
    r = client.post("/projects/myproject/deployer/scan")
    assert r.status_code == 200
    data = r.json()
    assert "api" in data["docker_services"]
    assert "web" in data["docker_services"]


def test_deployer_scan_unknown_project_returns_404(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    from fastapi.testclient import TestClient

    app, _ = _make_app(tmp_path)
    client = TestClient(app)
    r = client.post("/projects/no-such-project/deployer/scan")
    assert r.status_code == 404
