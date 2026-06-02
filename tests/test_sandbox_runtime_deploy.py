"""Unit tests for the shared operational deploy pipeline."""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.control_api.models.sandbox import SandboxState, SandboxStatus
from services.control_api.services.sandbox_manager import SandboxManager
from services.control_api.models.sandbox import EnvironmentMode, LifecyclePhase
from services.control_api.services.sandbox_runtime_deploy import (
    OperationalDeployResult,
    apply_deploy_result_to_state,
    deploy_operational_runtime,
    format_environment_logs,
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

    def _scripts_ok(*_args, **kwargs):
        cb = kwargs.get("on_step_complete")
        if cb:
            cb("start.sh")
        return True, None, [{"name": "healthcheck.sh", "status": "pass"}]

    with (
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
    ):
        (routes_dir / f"{state.id}.yml").write_text("http:\n  routers: {}\n")
        result = deploy_operational_runtime(
            state, sandbox_dir=sandbox_dir, mode="environment"
        )

    assert result.success is True
    assert result.urls == registered
    assert result.supervisor_pid == 55555
    assert result.route_registered is True
    mock_infra.assert_called_once()

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
    mock_unreg.assert_called_once_with(
        state.id,
        remove_route_file=False,
    )


def test_format_environment_logs_includes_lifecycle_sections(tmp_path):
    mgr, state, sandbox_dir = _sample_state(tmp_path)
    (sandbox_dir / "run.log").write_text(
        "--- bootstrap.sh ---\nok\n", encoding="utf-8"
    )
    (sandbox_dir / "runtime").mkdir(exist_ok=True)
    (sandbox_dir / "runtime" / "supervisor.log").write_text(
        "supervisor listening\n", encoding="utf-8"
    )
    text = format_environment_logs(sandbox_dir, state)
    assert "Lifecycle" in text
    assert "bootstrap.sh" in text
    assert "Supervisor" in text
    assert "supervisor listening" in text


def test_deploy_runs_smoke_for_deploy_and_test_mode(tmp_path):
    mgr, state, sandbox_dir = _sample_state(tmp_path)
    state = mgr.create(
        "env-smoke",
        str(tmp_path / "project"),
        env_name="env-smoke",
        deployment_mode=EnvironmentMode.deploy_and_test,
    )
    sandbox_dir = mgr._storage_dir(state.id)
    smoke = tmp_path / "project" / ".ai-dev-factory" / "scripts" / "smoke.sh"
    smoke.write_text("#!/bin/bash\nexit 0\n", encoding="utf-8")
    smoke.chmod(0o755)

    fake_proc = MagicMock()
    fake_proc.pid = 99
    registered = {"web": "http://w", "api": "http://a"}
    routes_dir = tmp_path / "routes"
    phases: list[LifecyclePhase] = []

    def capture(s):
        if s.lifecycle_phase:
            phases.append(s.lifecycle_phase)

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
            return_value=(True, None, [{"name": "healthcheck.sh", "status": "success"}]),
        ),
        patch(
            "tools.agent_runner.run_sandbox._run_smoke_tests",
            return_value=("success", None),
        ) as mock_smoke,
        patch(
            "services.control_api.services.proxy_manager.ProxyManager.register",
            return_value=registered,
        ),
    ):
        (routes_dir / f"{state.id}.yml").write_text("x")
        result = deploy_operational_runtime(
            state,
            sandbox_dir=sandbox_dir,
            mode="environment",
            persist_state=capture,
        )

    assert result.success is True
    assert result.smoke_status == "success"
    mock_smoke.assert_called_once()
    assert LifecyclePhase.validating in phases
