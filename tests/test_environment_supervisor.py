"""Tests for host-side environment provisioning via the supervisor."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _ok_compose(*args, **kwargs):
    m = MagicMock()
    m.returncode = 0
    m.stdout = "done"
    m.stderr = ""
    return m


@pytest.fixture
def supervisor_app(tmp_path, monkeypatch):
    runtime = tmp_path / "runtime"
    runtime.mkdir()
    monkeypatch.setenv("AI_DEV_FACTORY_RUNTIME_ROOT", str(runtime))
    for mod in [m for m in list(sys.modules) if m.startswith("path_mapper") or m == "main"]:
        sys.modules.pop(mod, None)

    from services.supervisor import main as sup_main

    sup_main._sandbox_locks.clear()
    if sup_main._sandbox_manager is not None:
        sup_main._sandbox_manager._proxy._auto_ensure_infra = False
    return sup_main, runtime


def test_supervisor_provision_maps_and_validates_host_project_root(
    supervisor_app, tmp_path, monkeypatch
):
    """Container path is mapped; existence is checked on the host."""
    sup_main, _runtime = supervisor_app
    host_project = tmp_path / "host-clone"
    host_project.mkdir()
    custom_sandbox = tmp_path / "sandboxes" / "demo"

    monkeypatch.setattr(
        sup_main.mapper,
        "map",
        lambda p: str(host_project) if p == "/app/clone" else p,
    )

    client = TestClient(sup_main.app)
    with patch(
        "services.control_api.services.environment_provision.deploy_operational_runtime",
    ) as mock_deploy:
        from services.control_api.services.sandbox_runtime_deploy import (
            OperationalDeployResult,
        )
        from services.control_api.services.proxy_manager import build_sandbox_urls

        def _ok(state, **kw):
            return OperationalDeployResult(
                success=True,
                urls=build_sandbox_urls(state.id),
                supervisor_pid=424242,
                route_registered=True,
            )

        mock_deploy.side_effect = _ok
        r = client.post(
            "/environments/provision",
            json={
                "env_name": "demo",
                "project_root": "/app/clone",
                "sandbox_path": str(custom_sandbox),
            },
        )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["ok"] is True
    state = data["state"]
    assert custom_sandbox.exists()
    assert (custom_sandbox / ".env").exists()
    assert (custom_sandbox / "state.json").exists()
    assert state["project_root"] == str(host_project.resolve())
    assert state["sandbox_dir"] == str(custom_sandbox.resolve())


def test_supervisor_provision_missing_host_project_root(supervisor_app, monkeypatch):
    sup_main, _runtime = supervisor_app
    missing = "/no/such/host/project"

    monkeypatch.setattr(sup_main.mapper, "map", lambda p: missing)

    client = TestClient(sup_main.app)
    r = client.post(
        "/environments/provision",
        json={"env_name": "demo", "project_root": "/app/missing"},
    )
    assert r.status_code == 422, r.text
    assert "does not exist on host runtime" in r.json()["error"]


def test_provision_endpoint_triggers_infra_bootstrap(
    supervisor_app, tmp_path, monkeypatch
):
    """HTTP provision endpoint → deploy_operational_runtime → _ensure_required_infra."""
    sup_main, _runtime = supervisor_app
    host_project = tmp_path / "host-clone"
    host_project.mkdir()
    (host_project / ".git").mkdir()
    scripts = host_project / ".ai-dev-factory" / "scripts"
    scripts.mkdir(parents=True)
    for name in ("bootstrap.sh", "build.sh", "start.sh", "healthcheck.sh"):
        s = scripts / name
        s.write_text("#!/bin/bash\nexit 0\n", encoding="utf-8")
        s.chmod(0o755)

    monkeypatch.setattr(
        sup_main.mapper,
        "map",
        lambda p: str(host_project) if p == "/app/clone" else p,
    )

    routes_dir = tmp_path / "routes"
    routes_dir.mkdir(exist_ok=True)
    fake_proc = MagicMock()
    fake_proc.pid = 77777
    registered = {"web": "http://w.test", "api": "http://a.test"}

    def _scripts_ok(*_args, **kwargs):
        cb = kwargs.get("on_step_complete")
        if cb:
            cb("start.sh")
        return True, None, [{"name": "healthcheck.sh", "status": "pass"}]

    client = TestClient(sup_main.app)
    with (
        patch(
            "services.control_api.services.sandbox_runtime_deploy._clone_fresh_source",
            return_value=(True, None, "abc1234"),
        ),
        patch(
            "services.control_api.services.sandbox_runtime_deploy.resolve_proxy_routes_dir",
            return_value=routes_dir,
        ),
        patch(
            "tools.agent_runner.run_sandbox._start_sandbox_supervisor",
            return_value=fake_proc,
        ),
        patch("tools.agent_runner.run_sandbox._ensure_required_infra") as mock_infra,
        patch("tools.agent_runner.run_sandbox._wait_for_proxy_url", return_value=True),
        patch("tools.agent_runner.run_sandbox._run_scripts", side_effect=_scripts_ok),
        patch(
            "services.control_api.services.proxy_manager.ProxyManager.register",
            return_value=registered,
        ),
        patch(
            "services.control_api.services.sandbox_runtime_deploy.validate_route_file",
            return_value=None,
        ),
    ):
        r = client.post(
            "/environments/provision",
            json={"env_name": "demo", "project_root": "/app/clone"},
        )

    assert r.status_code == 200, r.text
    assert r.json()["ok"] is True
    mock_infra.assert_called_once()


def test_api_routes_via_supervisor_when_host_path_invisible(
    tmp_path, monkeypatch
):
    """Control API must not require local visibility of the project root."""
    from services.control_api.main import create_app
    from services.control_api.models.sandbox import SandboxState, SandboxStatus

    proj = tmp_path / "myproject"
    proj.mkdir()

    app = create_app(project_root=proj, projects_root=tmp_path)
    monkeypatch.setenv(
        "AI_DEV_FACTORY_SUPERVISOR_URL",
        "http://host.docker.internal:8090",
    )

    fake_state = SandboxState(
        id="abc123def456",
        ticket_id="demo",
        project_root="/Users/host/clone",
        compose_project="sandbox-abc123def456",
        ports={"web": 3100, "api": 8100},
        status=SandboxStatus.running,
        created_at="2026-01-01T00:00:00+00:00",
        slot=1,
        env_name="demo",
        sandbox_dir=str(tmp_path / "sandboxes" / "demo"),
    )

    container_path = "/app/invisible-clone"
    captured: dict = {}

    def fake_provision(body, supervisor_url):
        captured["body"] = body
        captured["url"] = supervisor_url
        assert body["project_root"] == container_path
        return fake_state

    monkeypatch.setattr(
        "services.control_api.routes.environments.environment_runner.provision_environment",
        fake_provision,
    )

    client = TestClient(app)
    r = client.post(
        "/environments",
        json={
            "env_name": "demo",
            "project_root": container_path,
            "sandbox_path": str(tmp_path / "sandboxes" / "demo"),
        },
    )
    assert r.status_code == 201, r.text
    assert r.json()["id"] == fake_state.id
    assert captured["url"] == "http://host.docker.internal:8090"
    assert not Path(container_path).exists()
