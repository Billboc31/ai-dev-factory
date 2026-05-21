"""Integration tests for deployer execution, locking, logs, and healthchecks."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

_DEPLOY_YML_HOST = """\
version: 1
project: myproject
required_tools: []
components:
  - name: step1
    type: host
    command: '{cmd}'
"""

_DEPLOY_YML_DOCKER = """\
version: 1
project: myproject
required_tools: []
components:
  - name: api
    type: docker
    service: api
"""

_DEPLOY_YML_HEALTHCHECK = """\
version: 1
project: myproject
required_tools: []
components: []
healthcheck:
  command: '{cmd}'
  timeout: 10
  retries: 1
  delay: 0
"""


def _make_app(tmp_path: Path):
    from services.control_api.main import create_app

    proj = tmp_path / "myproject"
    proj.mkdir()
    (proj / ".git").mkdir()
    return create_app(project_root=proj, projects_root=tmp_path), proj


def _write_deploy_yml(proj: Path, content: str) -> None:
    ai_dir = proj / ".ai-dev-factory"
    ai_dir.mkdir(exist_ok=True)
    (ai_dir / "deploy.yml").write_text(content, encoding="utf-8")


def test_deploy_success(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    from fastapi.testclient import TestClient

    app, proj = _make_app(tmp_path)
    _write_deploy_yml(proj, _DEPLOY_YML_HOST.format(cmd="true"))

    client = TestClient(app)
    r = client.post("/projects/myproject/deployer/deploy")
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is True

    r2 = client.get("/projects/myproject/deployer/status")
    assert r2.status_code == 200
    assert r2.json()["state"] == "success"


def test_deploy_failure(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    from fastapi.testclient import TestClient

    app, proj = _make_app(tmp_path)
    _write_deploy_yml(proj, _DEPLOY_YML_HOST.format(cmd="false"))

    client = TestClient(app)
    r = client.post("/projects/myproject/deployer/deploy")
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is False
    assert data["error"] is not None

    r2 = client.get("/projects/myproject/deployer/status")
    assert r2.json()["state"] == "failed"
    assert r2.json()["error"] is not None


def test_deploy_logs(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    from fastapi.testclient import TestClient

    app, proj = _make_app(tmp_path)
    _write_deploy_yml(proj, _DEPLOY_YML_HOST.format(cmd="echo hello from deploy"))

    client = TestClient(app)
    client.post("/projects/myproject/deployer/deploy")

    r = client.get("/projects/myproject/deployer/logs")
    assert r.status_code == 200
    lines = r.json()["lines"]
    assert len(lines) > 0
    assert any("deploy" in line.lower() for line in lines)


def test_deploy_lock(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    from fastapi.testclient import TestClient

    app, proj = _make_app(tmp_path)
    _write_deploy_yml(proj, _DEPLOY_YML_HOST.format(cmd="true"))

    from services.control_api.services.deployer_runner import _get_lock

    lock = _get_lock("myproject")
    lock.acquire()
    try:
        client = TestClient(app)
        r = client.post("/projects/myproject/deployer/deploy")
        assert r.status_code == 409
    finally:
        lock.release()


def test_deploy_healthcheck_failure(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    from fastapi.testclient import TestClient

    app, proj = _make_app(tmp_path)
    _write_deploy_yml(proj, _DEPLOY_YML_HEALTHCHECK.format(cmd="false"))

    client = TestClient(app)
    r = client.post("/projects/myproject/deployer/deploy")
    assert r.status_code == 200
    data = r.json()
    assert data["ok"] is False
    assert "healthcheck" in data["error"].lower()

    r2 = client.get("/projects/myproject/deployer/status")
    assert r2.json()["state"] == "failed"


def test_restart_success(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    from fastapi.testclient import TestClient

    app, proj = _make_app(tmp_path)
    _write_deploy_yml(proj, _DEPLOY_YML_DOCKER)

    calls: list[str] = []

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(
        "services.control_api.services.deployer_runner.subprocess.run", fake_run
    )

    client = TestClient(app)
    r = client.post("/projects/myproject/deployer/restart")
    assert r.status_code == 200
    assert r.json()["ok"] is True
    assert any("docker compose restart api" in str(c) for c in calls)
