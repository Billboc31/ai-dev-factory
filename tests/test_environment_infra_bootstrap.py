"""Tests verifying Environment flows trigger the canonical infra bootstrap."""
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


def _scripts_ok(*_args, **kwargs):
    cb = kwargs.get("on_step_complete")
    if cb:
        cb("start.sh")
    return True, None, [{"name": "healthcheck.sh", "status": "pass"}]


class TestInfraBootstrappedOnProvision:
    """_ensure_required_infra is called before route registration during provisioning."""

    def test_infra_bootstrap_called_during_provision(self, tmp_path):
        _, state, sandbox_dir = _sample_state(tmp_path)
        fake_proc = MagicMock()
        fake_proc.pid = 55555
        registered = {"web": "http://w.test", "api": "http://a.test"}
        routes_dir = tmp_path / "routes"

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
            patch(
                "tools.agent_runner.run_sandbox._ensure_required_infra",
            ) as mock_infra,
            patch("tools.agent_runner.run_sandbox._wait_for_proxy_url", return_value=True),
            patch("tools.agent_runner.run_sandbox._run_scripts", side_effect=_scripts_ok),
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
        mock_infra.assert_called_once()
        call_args, _ = mock_infra.call_args
        assert isinstance(call_args[0], Path)


class TestTraefikInitiallyStopped:
    """Full infra bootstrap runs and succeeds even when Traefik starts from stopped state."""

    def test_traefik_started_automatically(self, tmp_path):
        _, state, sandbox_dir = _sample_state(tmp_path)
        fake_proc = MagicMock()
        fake_proc.pid = 55555
        registered = {"web": "http://w.test", "api": "http://a.test"}
        routes_dir = tmp_path / "routes"

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
            patch(
                "services.control_api.services.infra_service_manager.ensure_runtime_network",
            ),
            patch(
                "services.control_api.services.infra_service_manager.TraefikManager.ensure_running",
                return_value=True,
            ) as mock_ensure_running,
            patch("tools.agent_runner.run_sandbox._wait_for_proxy_url", return_value=True),
            patch("tools.agent_runner.run_sandbox._run_scripts", side_effect=_scripts_ok),
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
        assert result.route_registered is True
        mock_ensure_running.assert_called_once()


class TestNoDuplicateBootstrap:
    """_ensure_required_infra is called exactly once per deploy_operational_runtime invocation."""

    def test_no_duplicate_infra_calls_per_deploy(self, tmp_path):
        _, state, sandbox_dir = _sample_state(tmp_path)
        fake_proc = MagicMock()
        fake_proc.pid = 55555
        registered = {"web": "http://w.test", "api": "http://a.test"}
        routes_dir = tmp_path / "routes"

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
            patch(
                "tools.agent_runner.run_sandbox._ensure_required_infra",
            ) as mock_infra,
            patch("tools.agent_runner.run_sandbox._wait_for_proxy_url", return_value=True),
            patch("tools.agent_runner.run_sandbox._run_scripts", side_effect=_scripts_ok),
            patch(
                "services.control_api.services.proxy_manager.ProxyManager.register",
                return_value=registered,
            ),
        ):
            (routes_dir / f"{state.id}.yml").write_text("http:\n  routers: {}\n")
            deploy_operational_runtime(state, sandbox_dir=sandbox_dir, mode="environment")
            assert mock_infra.call_count == 1, "first deploy must call infra bootstrap exactly once"

            mock_infra.reset_mock()
            (routes_dir / f"{state.id}.yml").write_text("http:\n  routers: {}\n")
            deploy_operational_runtime(state, sandbox_dir=sandbox_dir, mode="environment")
            assert mock_infra.call_count == 1, "second deploy must call infra bootstrap exactly once"
