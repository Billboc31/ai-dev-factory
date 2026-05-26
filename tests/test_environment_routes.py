"""Integration tests for the /environments API routes (T151)."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

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
    app.state._sandbox_manager = SandboxManager(sandboxes_dir=tmp_path / "sandboxes")
    return app


def test_deploy_branch_environment(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    from fastapi.testclient import TestClient

    app = _make_app(tmp_path)
    client = TestClient(app)

    with patch("services.control_api.services.sandbox_manager.subprocess.run", side_effect=_ok_compose):
        r = client.post("/environments", json={
            "env_name": "feature/my-branch",
            "project_root": "/project",
            "ref": "feature/my-branch",
            "ref_type": "branch",
            "env_type": "feature",
            "deployment_mode": "deploy_and_test",
        })

    assert r.status_code == 201, r.text
    data = r.json()
    assert data["env_name"] == "feature/my-branch"
    assert data["ref"] == "feature/my-branch"
    assert data["deployed_at"] is not None


def test_deploy_persistent_environment(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    from fastapi.testclient import TestClient

    app = _make_app(tmp_path)
    client = TestClient(app)

    with patch("services.control_api.services.sandbox_manager.subprocess.run", side_effect=_ok_compose):
        r = client.post("/environments", json={
            "env_name": "develop",
            "project_root": "/project",
            "deployment_mode": "persistent",
        })

    assert r.status_code == 201, r.text
    assert r.json()["deployment_mode"] == "persistent"


def test_concurrent_environment_deployments(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    from fastapi.testclient import TestClient

    app = _make_app(tmp_path)
    client = TestClient(app)

    with patch("services.control_api.services.sandbox_manager.subprocess.run", side_effect=_ok_compose):
        client.post("/environments", json={"env_name": "env-a", "project_root": "/project"})
        client.post("/environments", json={"env_name": "env-b", "project_root": "/project"})

    r = client.get("/environments")
    assert r.status_code == 200
    names = {e["env_name"] for e in r.json()}
    assert "env-a" in names
    assert "env-b" in names


def test_environment_deletion_cleanup(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    from fastapi.testclient import TestClient

    app = _make_app(tmp_path)
    client = TestClient(app)

    with patch("services.control_api.services.sandbox_manager.subprocess.run", side_effect=_ok_compose):
        r = client.post("/environments", json={"env_name": "to-delete", "project_root": "/project"})
        env_id = r.json()["id"]
        del_r = client.delete(f"/environments/{env_id}")

    assert del_r.status_code == 204
    get_r = client.get(f"/environments/{env_id}")
    assert get_r.status_code == 404


def test_branch_ref_display_correctness(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    from fastapi.testclient import TestClient

    app = _make_app(tmp_path)
    client = TestClient(app)

    with patch("services.control_api.services.sandbox_manager.subprocess.run", side_effect=_ok_compose):
        r = client.post("/environments", json={
            "env_name": "preview-1",
            "project_root": "/project",
            "ref": "refs/pull/42/merge",
            "ref_type": "pr_ref",
        })
    env_id = r.json()["id"]

    get_r = client.get(f"/environments/{env_id}")
    assert get_r.status_code == 200
    data = get_r.json()
    assert data["ref"] == "refs/pull/42/merge"
    assert data["ref_type"] == "pr_ref"


def test_environment_lifecycle_transitions(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    from fastapi.testclient import TestClient

    app = _make_app(tmp_path)
    client = TestClient(app)

    with patch("services.control_api.services.sandbox_manager.subprocess.run", side_effect=_ok_compose):
        r = client.post("/environments", json={"env_name": "staging", "project_root": "/project"})
        env_id = r.json()["id"]
        assert r.json()["deployed_at"] is not None

        stop_r = client.post(f"/environments/{env_id}/stop")
        assert stop_r.status_code == 200
        assert stop_r.json()["stopped_at"] is not None
        assert stop_r.json()["status"] == "stopped"


def test_dashboard_action_idempotency(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    from fastapi.testclient import TestClient

    app = _make_app(tmp_path)
    client = TestClient(app)

    with patch("services.control_api.services.sandbox_manager.subprocess.run", side_effect=_ok_compose):
        r = client.post("/environments", json={"env_name": "idem", "project_root": "/project"})
        env_id = r.json()["id"]
        client.post(f"/environments/{env_id}/stop")
        # Stop an already-stopped environment — must not 5xx
        r2 = client.post(f"/environments/{env_id}/stop")

    assert r2.status_code < 500, f"expected 2xx but got {r2.status_code}"
