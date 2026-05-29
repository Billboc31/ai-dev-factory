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
    app.state._sandbox_manager = SandboxManager(
        sandboxes_dir=tmp_path / "sandboxes",
        proxy_routes_dir=tmp_path / "proxy_routes",
    )
    return app


def test_deploy_branch_environment(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    from fastapi.testclient import TestClient

    app = _make_app(tmp_path)
    client = TestClient(app)

    with patch("services.control_api.services.sandbox_manager.subprocess.run", side_effect=_ok_compose):
        r = client.post("/environments", json={
            "env_name": "feature/my-branch",
            "project_root": str(tmp_path / "myproject"),
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
            "project_root": str(tmp_path / "myproject"),
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
        client.post("/environments", json={"env_name": "env-a", "project_root": str(tmp_path / "myproject")})
        client.post("/environments", json={"env_name": "env-b", "project_root": str(tmp_path / "myproject")})

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
        r = client.post("/environments", json={"env_name": "to-delete", "project_root": str(tmp_path / "myproject")})
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
            "project_root": str(tmp_path / "myproject"),
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
        r = client.post("/environments", json={"env_name": "staging", "project_root": str(tmp_path / "myproject")})
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
        r = client.post("/environments", json={"env_name": "idem", "project_root": str(tmp_path / "myproject")})
        env_id = r.json()["id"]
        client.post(f"/environments/{env_id}/stop")
        # Stop an already-stopped environment — must not 5xx
        r2 = client.post(f"/environments/{env_id}/stop")

    assert r2.status_code < 500, f"expected 2xx but got {r2.status_code}"


# ── T158: custom host validation ─────────────────────────────────────────────


def test_create_environment_with_custom_hosts(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    monkeypatch.setenv("HOST_RUNTIME_ROOT", str(tmp_path / "host-runtime"))
    from fastapi.testclient import TestClient

    app = _make_app(tmp_path)
    client = TestClient(app)

    with patch("services.control_api.services.sandbox_manager.subprocess.run", side_effect=_ok_compose):
        r = client.post("/environments", json={
            "env_name": "demo",
            "project_root": str(tmp_path / "myproject"),
            "web_host": "demo.ai-dev-factory.localhost",
            "api_host": "api.demo.ai-dev-factory.localhost",
        })

    assert r.status_code == 201, r.text
    data = r.json()
    assert data["web_host"] == "demo.ai-dev-factory.localhost"
    assert data["api_host"] == "api.demo.ai-dev-factory.localhost"
    assert data["urls"]["web"] == "http://demo.ai-dev-factory.localhost"
    assert data["urls"]["api"] == "http://api.demo.ai-dev-factory.localhost"


def test_create_environment_invalid_host_format(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    from fastapi.testclient import TestClient

    app = _make_app(tmp_path)
    client = TestClient(app)

    r = client.post("/environments", json={
        "env_name": "bad",
        "project_root": str(tmp_path / "myproject"),
        "web_host": "my host!.localhost",
    })
    assert r.status_code == 422
    assert "web_host" in r.json()["detail"]


def test_create_environment_reserved_host(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    from fastapi.testclient import TestClient

    app = _make_app(tmp_path)
    client = TestClient(app)

    r = client.post("/environments", json={
        "env_name": "bad",
        "project_root": str(tmp_path / "myproject"),
        "web_host": "traefik.ai-dev-factory.localhost",
    })
    assert r.status_code == 422
    assert "web_host" in r.json()["detail"]


def test_create_environment_host_collision(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    monkeypatch.setenv("HOST_RUNTIME_ROOT", str(tmp_path / "host-runtime"))
    from fastapi.testclient import TestClient

    app = _make_app(tmp_path)
    client = TestClient(app)

    with patch("services.control_api.services.sandbox_manager.subprocess.run", side_effect=_ok_compose):
        r1 = client.post("/environments", json={
            "env_name": "first",
            "project_root": str(tmp_path / "myproject"),
            "web_host": "shared.ai-dev-factory.localhost",
        })
        assert r1.status_code == 201, r1.text

        # Second environment trying to claim the same host must be rejected.
        r2 = client.post("/environments", json={
        "env_name": "second",
        "project_root": str(tmp_path / "myproject"),
            "web_host": "shared.ai-dev-factory.localhost",
        })
        assert r2.status_code == 422
        assert "web_host" in r2.json()["detail"]


def test_create_environment_localhost_reserved(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    from fastapi.testclient import TestClient

    app = _make_app(tmp_path)
    client = TestClient(app)

    r = client.post("/environments", json={
        "env_name": "bad",
        "project_root": str(tmp_path / "myproject"),
        "api_host": "localhost",
    })
    assert r.status_code == 422
    assert "api_host" in r.json()["detail"]


# ── T160: path resolution and error handling ──────────────────────────────────


def test_custom_sandbox_root_resolves_correctly(tmp_path, monkeypatch):
    """Environment actions use a configurable sandbox root, not hardcoded paths."""
    custom_root = tmp_path / "custom-sandbox-root"
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    from fastapi.testclient import TestClient
    from services.control_api.services.sandbox_manager import SandboxManager

    app = _make_app(tmp_path)
    app.state._sandbox_manager = SandboxManager(
        sandboxes_dir=custom_root / "myproject",
        proxy_routes_dir=tmp_path / "proxy_routes",
    )
    client = TestClient(app)

    with patch("services.control_api.services.sandbox_manager.subprocess.run", side_effect=_ok_compose):
        r = client.post("/environments", json={"env_name": "custom-env", "project_root": str(tmp_path / "myproject")})
    assert r.status_code == 201, r.text
    env_id = r.json()["id"]

    with patch("services.control_api.services.sandbox_manager.subprocess.run", side_effect=_ok_compose):
        stop_r = client.post(f"/environments/{env_id}/stop")
    assert stop_r.status_code == 200

    with patch("services.control_api.services.sandbox_manager.subprocess.run", side_effect=_ok_compose):
        del_r = client.delete(f"/environments/{env_id}")
    assert del_r.status_code == 204


def test_missing_sandbox_returns_readable_404(tmp_path, monkeypatch):
    """Requesting an action on a non-existent sandbox returns 404 with a human-readable message."""
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    from fastapi.testclient import TestClient

    app = _make_app(tmp_path)
    client = TestClient(app)

    nonexistent = "deadbeef0000"
    r = client.get(f"/environments/{nonexistent}")
    assert r.status_code == 404
    assert "environment not found" in r.json()["detail"]

    r2 = client.post(f"/environments/{nonexistent}/stop")
    assert r2.status_code == 404
    assert "environment not found" in r2.json()["detail"]


def test_no_hardcoded_sandboxes_path_in_sandbox_manager():
    """sandbox_manager.py must not contain hardcoded /sandboxes/... path construction."""
    src = Path(__file__).resolve().parents[1] / "services" / "control_api" / "services" / "sandbox_manager.py"
    content = src.read_text(encoding="utf-8")
    assert 'Path("/sandboxes")' not in content, 'found hardcoded Path("/sandboxes")'
    assert '"/sandboxes/"' not in content, 'found hardcoded "/sandboxes/" string'


# ── T161: real sandbox provisioning on create ─────────────────────────────────


def _fail_compose_up(*args, **kwargs):
    """Return rc=1 for compose up commands, rc=0 for everything else."""
    m = MagicMock()
    cmd_list = args[0] if args else kwargs.get("args", [])
    if isinstance(cmd_list, list) and "up" in cmd_list:
        m.returncode = 1
        m.stdout = ""
        m.stderr = "container start failed"
    else:
        m.returncode = 0
        m.stdout = "done"
        m.stderr = ""
    return m


def test_create_environment_creates_real_sandbox_dir(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    from fastapi.testclient import TestClient

    app = _make_app(tmp_path)
    client = TestClient(app)

    with patch("services.control_api.services.sandbox_manager.subprocess.run", side_effect=_ok_compose):
        r = client.post("/environments", json={"env_name": "demo-ai-dev-factory", "project_root": str(tmp_path / "myproject")})
    assert r.status_code == 201, r.text
    env_id = r.json()["id"]
    assert (tmp_path / "sandboxes" / env_id).exists()


def test_create_environment_creates_state_json(tmp_path, monkeypatch):
    import json as _json

    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    from fastapi.testclient import TestClient

    app = _make_app(tmp_path)
    client = TestClient(app)

    with patch("services.control_api.services.sandbox_manager.subprocess.run", side_effect=_ok_compose):
        r = client.post("/environments", json={"env_name": "demo-ai-dev-factory", "project_root": str(tmp_path / "myproject")})
    assert r.status_code == 201, r.text
    env_id = r.json()["id"]
    state_file = tmp_path / "sandboxes" / env_id / "state.json"
    assert state_file.exists(), "state.json not created"
    data = _json.loads(state_file.read_text())
    assert data["id"] == env_id


def test_create_environment_creates_env_file(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    from fastapi.testclient import TestClient

    app = _make_app(tmp_path)
    client = TestClient(app)

    with patch("services.control_api.services.sandbox_manager.subprocess.run", side_effect=_ok_compose):
        r = client.post("/environments", json={"env_name": "demo-ai-dev-factory", "project_root": str(tmp_path / "myproject")})
    assert r.status_code == 201, r.text
    env_id = r.json()["id"]
    assert (tmp_path / "sandboxes" / env_id / ".env").exists()


def test_failed_provisioning_returns_500(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    from fastapi.testclient import TestClient

    app = _make_app(tmp_path)
    client = TestClient(app)

    with patch("services.control_api.services.sandbox_manager.subprocess.run", side_effect=_fail_compose_up):
        r = client.post("/environments", json={"env_name": "demo-ai-dev-factory", "project_root": str(tmp_path / "myproject")})
    assert r.status_code >= 500, f"expected 5xx but got {r.status_code}: {r.text}"


def test_failed_provisioning_no_environment_card(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    from fastapi.testclient import TestClient

    app = _make_app(tmp_path)
    client = TestClient(app)

    with patch("services.control_api.services.sandbox_manager.subprocess.run", side_effect=_fail_compose_up):
        client.post("/environments", json={"env_name": "demo-ai-dev-factory", "project_root": str(tmp_path / "myproject")})

    r = client.get("/environments")
    assert r.status_code == 200
    assert r.json() == [], f"expected empty list but got: {r.json()}"


def test_failed_provisioning_sandbox_dir_removed(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    from fastapi.testclient import TestClient

    app = _make_app(tmp_path)
    client = TestClient(app)

    with patch("services.control_api.services.sandbox_manager.subprocess.run", side_effect=_fail_compose_up):
        client.post("/environments", json={"env_name": "demo-ai-dev-factory", "project_root": str(tmp_path / "myproject")})

    sandboxes_dir = tmp_path / "sandboxes"
    subdirs = [d for d in sandboxes_dir.iterdir() if d.is_dir()] if sandboxes_dir.exists() else []
    assert subdirs == [], f"expected no sandbox dirs but found: {subdirs}"


def test_create_environment_sandbox_id_from_manager(tmp_path, monkeypatch):
    import re

    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    from fastapi.testclient import TestClient

    app = _make_app(tmp_path)
    client = TestClient(app)

    with patch("services.control_api.services.sandbox_manager.subprocess.run", side_effect=_ok_compose):
        r = client.post("/environments", json={"env_name": "demo", "project_root": str(tmp_path / "myproject")})
    assert r.status_code == 201, r.text
    env_id = r.json()["id"]
    assert re.fullmatch(r"[0-9a-f]{12}", env_id), f"id is not a 12-char hex string: {env_id!r}"


def test_environment_actions_work_after_create(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    from fastapi.testclient import TestClient

    app = _make_app(tmp_path)
    client = TestClient(app)

    with patch("services.control_api.services.sandbox_manager.subprocess.run", side_effect=_ok_compose):
        r = client.post("/environments", json={"env_name": "demo", "project_root": str(tmp_path / "myproject")})
        assert r.status_code == 201, r.text
        env_id = r.json()["id"]

        refresh_r = client.post(f"/environments/{env_id}/refresh")
        assert refresh_r.status_code < 500, f"refresh returned {refresh_r.status_code}"

        stop_r = client.post(f"/environments/{env_id}/stop")
        assert stop_r.status_code < 500, f"stop returned {stop_r.status_code}"

        redeploy_r = client.post(f"/environments/{env_id}/redeploy")
        assert redeploy_r.status_code < 500, f"redeploy returned {redeploy_r.status_code}"

        del_r = client.delete(f"/environments/{env_id}")
        assert del_r.status_code < 500, f"delete returned {del_r.status_code}"


# ── Custom sandbox directory auto-creation ────────────────────────────────────


def test_create_environment_auto_creates_custom_sandbox_path(tmp_path, monkeypatch):
    """sandbox_path is the runtime location; parent dirs are created automatically."""
    import json as _json

    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    from fastapi.testclient import TestClient

    custom = tmp_path / "sandboxes" / "demo"
    assert not custom.exists()

    app = _make_app(tmp_path)
    client = TestClient(app)

    with patch("services.control_api.services.sandbox_manager.subprocess.run", side_effect=_ok_compose):
        r = client.post(
            "/environments",
            json={
                "env_name": "demo",
                "project_root": str(tmp_path / "myproject"),
                "sandbox_path": str(custom),
            },
        )
    assert r.status_code == 201, r.text
    data = r.json()
    assert custom.exists()
    assert (custom / ".env").exists()
    assert (custom / "state.json").exists()
    state = _json.loads((custom / "state.json").read_text(encoding="utf-8"))
    assert state["id"] == data["id"]
    assert state["sandbox_dir"] == str(custom.resolve())
    assert data["sandbox_dir"] == str(custom.resolve())


def test_create_environment_auto_creates_nested_custom_sandbox_path(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    from fastapi.testclient import TestClient

    nested = tmp_path / "custom" / "envs" / "demo" / "runtime"
    assert not nested.parent.exists()

    app = _make_app(tmp_path)
    client = TestClient(app)

    with patch("services.control_api.services.sandbox_manager.subprocess.run", side_effect=_ok_compose):
        r = client.post(
            "/environments",
            json={
                "env_name": "nested",
                "project_root": str(tmp_path / "myproject"),
                "sandbox_path": str(nested),
            },
        )
    assert r.status_code == 201, r.text
    assert nested.exists()
    assert (nested / ".env").exists()
    assert (nested / "state.json").exists()


def test_failed_provisioning_cleans_custom_sandbox_path(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    from fastapi.testclient import TestClient

    custom = tmp_path / "sandboxes" / "demo"
    app = _make_app(tmp_path)
    client = TestClient(app)

    with patch("services.control_api.services.sandbox_manager.subprocess.run", side_effect=_fail_compose_up):
        r = client.post(
            "/environments",
            json={
                "env_name": "demo",
                "project_root": str(tmp_path / "myproject"),
                "sandbox_path": str(custom),
            },
        )
    assert r.status_code >= 500, r.text

    list_r = client.get("/environments")
    assert list_r.status_code == 200
    assert list_r.json() == []

    assert not custom.exists(), f"expected custom sandbox dir removed, found: {list(custom.rglob('*'))}"
