"""Regression tests for dashboard 500 errors after project-scoped routing (T126)."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _make_app(tmp_path: Path):
    from services.control_api.main import create_app

    proj = tmp_path / "my-project"
    proj.mkdir()
    (proj / ".git").mkdir()
    (proj / "runs").mkdir()

    return create_app(project_root=proj, projects_root=tmp_path), proj


# ── daemon board ───────────────────────────────────────────────────────────────

def test_project_daemon_board_returns_200(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    from fastapi.testclient import TestClient
    app, _ = _make_app(tmp_path)
    client = TestClient(app)
    r = client.get("/projects/my-project/daemon/board")
    assert r.status_code == 200
    assert "columns" in r.json()


def test_project_daemon_board_unknown_project_returns_404(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    from fastapi.testclient import TestClient
    app, _ = _make_app(tmp_path)
    client = TestClient(app)
    r = client.get("/projects/no-such-id/daemon/board")
    assert r.status_code == 404


# ── project-map ────────────────────────────────────────────────────────────────

def test_project_map_returns_200_when_no_file(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    from fastapi.testclient import TestClient
    app, _ = _make_app(tmp_path)
    client = TestClient(app)
    r = client.get("/projects/my-project/project-map")
    assert r.status_code == 200


def test_project_map_activity_returns_200_when_no_file(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    from fastapi.testclient import TestClient
    app, _ = _make_app(tmp_path)
    client = TestClient(app)
    r = client.get("/projects/my-project/project-map/activity")
    assert r.status_code == 200


def test_project_map_refresh_returns_200(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    from fastapi.testclient import TestClient
    app, _ = _make_app(tmp_path)
    client = TestClient(app)
    r = client.post("/projects/my-project/project-map/refresh")
    assert r.status_code == 200
    assert r.json()["ok"] is True


# ── unknown project → 404 for project-map routes ──────────────────────────────

def test_project_map_unknown_project_returns_404(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    from fastapi.testclient import TestClient
    app, _ = _make_app(tmp_path)
    client = TestClient(app)
    r = client.get("/projects/no-such-id/project-map")
    assert r.status_code == 404


def test_project_map_activity_unknown_project_returns_404(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    from fastapi.testclient import TestClient
    app, _ = _make_app(tmp_path)
    client = TestClient(app)
    r = client.get("/projects/no-such-id/project-map/activity")
    assert r.status_code == 404


def test_project_map_refresh_unknown_project_returns_404(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    from fastapi.testclient import TestClient
    app, _ = _make_app(tmp_path)
    client = TestClient(app)
    r = client.post("/projects/no-such-id/project-map/refresh")
    assert r.status_code == 404


# ── global exception handler ──────────────────────────────────────────────────

def test_unhandled_exception_returns_500_with_detail(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    from services.control_api.services import project_map_service
    from fastapi.testclient import TestClient

    app, _ = _make_app(tmp_path)

    def _boom(project_root):
        raise RuntimeError("injected failure")

    monkeypatch.setattr(project_map_service, "get_project_map", _boom)
    client = TestClient(app, raise_server_exceptions=False)
    r = client.get("/project-map")
    assert r.status_code == 500
    body = r.json()
    assert "detail" in body
    assert body["detail"]
