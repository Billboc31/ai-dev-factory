"""Tests for control API agent-layout proxy routes (start + status/logs/files).

Focus: the proxy must forward to the supervisor and *propagate* its status codes
instead of swallowing non-2xx responses into an empty 200 (the old bug).
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _make_git_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    (path / ".git").mkdir()
    return path


@pytest.fixture()
def client(tmp_path):
    from services.control_api.main import create_app
    pr = tmp_path / "projects"
    _make_git_repo(pr / "alpha")
    app = create_app(project_root=tmp_path, projects_root=pr)
    return TestClient(app)


class _FakeResponse:
    def __init__(self, status_code: int, payload: dict, text: str = ""):
        self.status_code = status_code
        self._payload = payload
        self.text = text or ""

    def json(self):
        if self._payload is None:
            raise ValueError("no json")
        return self._payload


class _FakeClient:
    """Minimal stand-in for httpx.Client used by the proxy routes."""

    def __init__(self, handler):
        self._handler = handler

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def post(self, url, json=None, **kwargs):
        return self._handler("POST", url, json=json, **kwargs)

    def get(self, url, params=None, **kwargs):
        return self._handler("GET", url, params=params, **kwargs)


def _patch_supervisor(monkeypatch, handler):
    from services.control_api.routes import projects as projects_routes
    monkeypatch.setattr(
        projects_routes.httpx, "Client", lambda *a, **k: _FakeClient(handler)
    )


def test_start_returns_job_id(client, monkeypatch):
    def handler(method, url, **kwargs):
        assert method == "POST"
        assert url.endswith("/projects/alpha/install-agent-layout")
        return _FakeResponse(200, {"ok": True, "job_id": "deadbeef"})

    _patch_supervisor(monkeypatch, handler)
    r = client.post("/projects/alpha/install-agent-layout")
    assert r.status_code == 200
    assert r.json()["job_id"] == "deadbeef"


def test_start_propagates_supervisor_error(client, monkeypatch):
    def handler(method, url, **kwargs):
        return _FakeResponse(422, {"error": "git_not_found", "detail": "/x"})

    _patch_supervisor(monkeypatch, handler)
    r = client.post("/projects/alpha/install-agent-layout")
    # The old behaviour returned an empty 200; now the error is surfaced.
    assert r.status_code == 422
    assert "/x" in r.json()["detail"]


def test_start_unknown_project_is_404(client, monkeypatch):
    _patch_supervisor(monkeypatch, lambda *a, **k: _FakeResponse(200, {"job_id": "x"}))
    r = client.post("/projects/ghost/install-agent-layout")
    assert r.status_code == 404


def test_latest_proxies_body_and_status(client, monkeypatch):
    job = {
        "job_id": "j1", "project_id": "alpha", "status": "done",
        "branch": "docs/install", "result": None, "error": None,
    }

    def handler(method, url, **kwargs):
        assert url.endswith("/projects/alpha/install-agent-layout/latest")
        return _FakeResponse(200, job)

    _patch_supervisor(monkeypatch, handler)
    r = client.get("/projects/alpha/install-agent-layout/latest")
    assert r.status_code == 200
    assert r.json()["job_id"] == "j1"


def test_latest_404_propagated(client, monkeypatch):
    _patch_supervisor(monkeypatch, lambda *a, **k: _FakeResponse(404, {"error": "no job"}))
    r = client.get("/projects/alpha/install-agent-layout/latest")
    assert r.status_code == 404


def test_logs_proxy_forwards_offset(client, monkeypatch):
    seen = {}

    def handler(method, url, params=None, **kwargs):
        seen["url"] = url
        seen["params"] = params
        return _FakeResponse(200, {"text": "hello", "offset": 5, "status": "running"})

    _patch_supervisor(monkeypatch, handler)
    r = client.get("/projects/alpha/install-agent-layout/j1/logs", params={"offset": 5})
    assert r.status_code == 200
    assert r.json()["offset"] == 5
    assert seen["params"]["offset"] == 5
    assert seen["url"].endswith("/projects/alpha/install-agent-layout/j1/logs")


def test_files_proxy(client, monkeypatch):
    payload = {
        "files": [{"status": "A", "path": "docs/X.md"}],
        "docs_paths": ["docs/X.md"], "warnings": [], "branch": "docs/install",
    }
    _patch_supervisor(monkeypatch, lambda *a, **k: _FakeResponse(200, payload))
    r = client.get("/projects/alpha/install-agent-layout/j1/files")
    assert r.status_code == 200
    assert r.json()["files"][0]["path"] == "docs/X.md"


def test_status_proxy_forwards_project_root(client, monkeypatch):
    seen = {}

    def handler(method, url, params=None, **kwargs):
        seen["url"] = url
        seen["params"] = params
        return _FakeResponse(200, {
            "layout_exists": True,
            "ai_counts": {"roles": 2, "skills": 1, "templates": 3},
            "docs_present": ["docs/overview.md"],
            "base_docs_present": 5,
            "base_docs_total": 10,
            "memory_files": {"docs/ai/global-context.md": True},
        })

    _patch_supervisor(monkeypatch, handler)
    r = client.get("/projects/alpha/install-agent-layout/status")
    assert r.status_code == 200
    assert r.json()["layout_exists"] is True
    assert seen["url"].endswith("/projects/alpha/install-agent-layout/status")
    assert "project_root" in seen["params"]


def test_file_proxy_forwards_path(client, monkeypatch):
    seen = {}

    def handler(method, url, params=None, **kwargs):
        seen["params"] = params
        return _FakeResponse(200, {"path": "docs/X.md", "content": "# x", "diff": "++"})

    _patch_supervisor(monkeypatch, handler)
    r = client.get(
        "/projects/alpha/install-agent-layout/j1/file", params={"path": "docs/X.md"}
    )
    assert r.status_code == 200
    assert seen["params"]["path"] == "docs/X.md"
    assert r.json()["content"] == "# x"
