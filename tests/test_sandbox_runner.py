"""Tests for sandbox runner: worktree creation, success, failure, logs, lock contention."""

from __future__ import annotations

import subprocess as _subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _make_git_project(tmp_path: Path) -> Path:
    proj = tmp_path / "myproject"
    proj.mkdir()
    _subprocess.run(["git", "init", str(proj)], check=True, capture_output=True)
    _subprocess.run(["git", "-C", str(proj), "config", "user.email", "test@test.com"], check=True, capture_output=True)
    _subprocess.run(["git", "-C", str(proj), "config", "user.name", "Test"], check=True, capture_output=True)
    (proj / "README.md").write_text("test")
    _subprocess.run(["git", "-C", str(proj), "add", "."], check=True, capture_output=True)
    _subprocess.run(["git", "-C", str(proj), "commit", "-m", "init"], check=True, capture_output=True)
    return proj


def _add_scripts(proj: Path, scripts: dict[str, str]) -> None:
    for name, content in scripts.items():
        script = proj / name
        script.write_text(f"#!/bin/bash\n{content}\n")
        script.chmod(0o755)
    _subprocess.run(["git", "-C", str(proj), "add", "."], check=True, capture_output=True)
    _subprocess.run(["git", "-C", str(proj), "commit", "-m", "add scripts"], check=True, capture_output=True)


def _make_app(tmp_path: Path, proj: Path):
    from services.control_api.main import create_app
    return create_app(project_root=proj, projects_root=tmp_path)


def _wait_for_terminal(client, project_id: str, timeout: float = 15.0) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = client.get(f"/projects/{project_id}/sandbox/status")
        if r.json().get("state") in ("success", "failed"):
            return r.json()
        time.sleep(0.1)
    return client.get(f"/projects/{project_id}/sandbox/status").json()


def test_sandbox_worktree_creation(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    from fastapi.testclient import TestClient

    proj = _make_git_project(tmp_path)
    app = _make_app(tmp_path, proj)
    client = TestClient(app)

    r = client.post("/projects/myproject/sandbox/start")
    assert r.status_code == 202
    assert r.json()["ok"] is True

    _wait_for_terminal(client, "myproject")

    sandbox_base = proj / ".ai-dev-factory" / "sandboxes"
    latest = (sandbox_base / "latest").read_text().strip()
    worktree_path = sandbox_base / latest / "worktree"
    assert worktree_path.exists()


def test_sandbox_full_success(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    from fastapi.testclient import TestClient

    proj = _make_git_project(tmp_path)
    _add_scripts(proj, {
        "bootstrap.sh": "exit 0",
        "build.sh": "exit 0",
        "start.sh": "exit 0",
        "healthcheck.sh": "exit 0",
    })
    app = _make_app(tmp_path, proj)
    client = TestClient(app)

    r = client.post("/projects/myproject/sandbox/start")
    assert r.status_code == 202

    status = _wait_for_terminal(client, "myproject")
    assert status["state"] == "success"
    success_steps = [s for s in status["steps"] if s["status"] == "success"]
    assert len(success_steps) == 4


def test_sandbox_healthcheck_failure(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    from fastapi.testclient import TestClient

    proj = _make_git_project(tmp_path)
    _add_scripts(proj, {
        "bootstrap.sh": "exit 0",
        "healthcheck.sh": "exit 1",
    })
    app = _make_app(tmp_path, proj)
    client = TestClient(app)

    client.post("/projects/myproject/sandbox/start")
    status = _wait_for_terminal(client, "myproject")

    assert status["state"] == "failed"
    assert status["last_step"] == "healthcheck.sh"
    assert "healthcheck.sh" in (status.get("error") or "")
    failed_steps = [s for s in status["steps"] if s["status"] == "failed"]
    assert len(failed_steps) == 1
    assert failed_steps[0]["name"] == "healthcheck.sh"


def test_sandbox_mid_pipeline_failure(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    from fastapi.testclient import TestClient

    proj = _make_git_project(tmp_path)
    _add_scripts(proj, {
        "bootstrap.sh": "exit 0",
        "build.sh": "exit 1",
        "start.sh": "exit 0",
        "healthcheck.sh": "exit 0",
    })
    app = _make_app(tmp_path, proj)
    client = TestClient(app)

    client.post("/projects/myproject/sandbox/start")
    status = _wait_for_terminal(client, "myproject")

    assert status["state"] == "failed"
    steps_by_name = {s["name"]: s for s in status["steps"]}
    assert steps_by_name["bootstrap.sh"]["status"] == "success"
    assert steps_by_name["build.sh"]["status"] == "failed"
    assert "start.sh" not in steps_by_name
    assert "healthcheck.sh" not in steps_by_name


def test_sandbox_log_capture(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    from fastapi.testclient import TestClient

    proj = _make_git_project(tmp_path)
    _add_scripts(proj, {"bootstrap.sh": "echo hello_from_bootstrap"})
    app = _make_app(tmp_path, proj)
    client = TestClient(app)

    client.post("/projects/myproject/sandbox/start")
    _wait_for_terminal(client, "myproject")

    r = client.get("/projects/myproject/sandbox/logs")
    assert r.status_code == 200
    lines = r.json()["lines"]
    assert len(lines) > 0
    assert any("hello_from_bootstrap" in line for line in lines)


def test_sandbox_lock_contention(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    from fastapi.testclient import TestClient
    from services.control_api.services.sandbox_runner import _get_lock

    proj = _make_git_project(tmp_path)
    app = _make_app(tmp_path, proj)
    client = TestClient(app)

    lock = _get_lock("myproject")
    lock.acquire()
    try:
        r = client.post("/projects/myproject/sandbox/start")
        assert r.status_code == 409
    finally:
        lock.release()
