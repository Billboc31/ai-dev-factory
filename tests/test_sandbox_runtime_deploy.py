"""Unit tests for the shared operational deploy pipeline."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.control_api.models.sandbox import SandboxState, SandboxStatus
from services.control_api.services.sandbox_manager import SandboxManager
from services.control_api.services.sandbox_runtime_deploy import (
    OperationalDeployResult,
    apply_deploy_result_to_state,
    deploy_operational_runtime,
)


def _sample_state(tmp_path: Path) -> tuple[SandboxManager, SandboxState, Path]:
    proj = tmp_path / "project"
    proj.mkdir()
    (proj / ".git").mkdir()
    scripts = proj / ".ai-dev-factory" / "scripts"
    scripts.mkdir(parents=True)
    for name in ("bootstrap.sh", "build.sh", "start.sh", "healthcheck.sh"):
        script = scripts / name
        script.write_text("#!/bin/bash\nexit 0\n", encoding="utf-8")
        script.chmod(0o755)

    mgr = SandboxManager(
        sandboxes_dir=tmp_path / "sandboxes",
        proxy_routes_dir=tmp_path / "routes",
    )
    state = mgr.create("env-1", str(proj), env_name="env-1")
    sandbox_dir = mgr._storage_dir(state.id)
    return mgr, state, sandbox_dir


def test_deploy_operational_runtime_success(tmp_path):
    mgr, state, sandbox_dir = _sample_state(tmp_path)
    fake_proc = MagicMock()
    fake_proc.pid = 55555
    registered = {"web": "http://w.test", "api": "http://a.test"}

    routes_dir = tmp_path / "routes"
    with (
        patch(
            "services.control_api.services.sandbox_runtime_deploy.resolve_proxy_routes_dir",
            return_value=routes_dir,
        ),
        patch(
            "tools.agent_runner.run_sandbox._start_sandbox_supervisor",
            return_value=fake_proc,
        ),
        patch("tools.agent_runner.run_sandbox._ensure_required_infra"),
        patch("tools.agent_runner.run_sandbox._wait_for_proxy_url", return_value=True),
        patch(
            "tools.agent_runner.run_sandbox._run_scripts",
            return_value=(True, None, [{"name": "healthcheck.sh", "status": "pass"}]),
        ),
        patch(
            "services.control_api.services.proxy_manager.ProxyManager.register",
            return_value=registered,
        ),
    ):
        (routes_dir / f"{state.id}.yml").write_text("http:\n  routers: {}\n")
        result = deploy_operational_runtime(
            state, sandbox_dir=sandbox_dir, mode="environment"
        )

    assert result.success is True
    assert result.urls == registered
    assert result.supervisor_pid == 55555
    assert result.route_registered is True

    updated = apply_deploy_result_to_state(state, result)
    assert updated.status == SandboxStatus.running
    assert updated.urls == registered
    assert updated.supervisor_pid == 55555


def test_deploy_operational_runtime_supervisor_failure(tmp_path):
    _, state, sandbox_dir = _sample_state(tmp_path)

    with patch(
        "tools.agent_runner.run_sandbox._start_sandbox_supervisor",
        return_value=None,
    ):
        result = deploy_operational_runtime(
            state, sandbox_dir=sandbox_dir, mode="environment"
        )

    assert result.success is False
    assert "supervisor" in (result.error or "").lower()


def test_deploy_operational_runtime_script_failure_cleans_up(tmp_path):
    _, state, sandbox_dir = _sample_state(tmp_path)
    fake_proc = MagicMock()
    fake_proc.pid = 1
    registered = {"web": "http://w", "api": "http://a"}

    routes_dir = tmp_path / "routes"
    with (
        patch(
            "services.control_api.services.sandbox_runtime_deploy.resolve_proxy_routes_dir",
            return_value=routes_dir,
        ),
        patch(
            "tools.agent_runner.run_sandbox._start_sandbox_supervisor",
            return_value=fake_proc,
        ),
        patch("tools.agent_runner.run_sandbox._ensure_required_infra"),
        patch("tools.agent_runner.run_sandbox._wait_for_proxy_url", return_value=True),
        patch(
            "tools.agent_runner.run_sandbox._run_scripts",
            return_value=(False, "bootstrap failed", []),
        ),
        patch("tools.agent_runner.run_sandbox._run_stop_script"),
        patch("tools.agent_runner.run_sandbox._stop_sandbox_supervisor"),
        patch(
            "services.control_api.services.proxy_manager.ProxyManager.register",
            return_value=registered,
        ),
        patch(
            "services.control_api.services.proxy_manager.ProxyManager.unregister"
        ) as mock_unreg,
    ):
        (routes_dir / f"{state.id}.yml").write_text("x")
        result = deploy_operational_runtime(
            state, sandbox_dir=sandbox_dir, mode="environment"
        )

    assert result.success is False
    mock_unreg.assert_called_once_with(state.id)
