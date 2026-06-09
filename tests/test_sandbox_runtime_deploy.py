"""Unit tests for the shared operational deploy pipeline."""
from __future__ import annotations

import shutil
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

    # Pre-create source scripts to reflect the cloned layout used at runtime.
    source_scripts = sandbox_dir / "source" / ".ai-dev-factory" / "scripts"
    source_scripts.mkdir(parents=True)
    for name in ("bootstrap.sh", "build.sh", "start.sh", "healthcheck.sh"):
        script = source_scripts / name
        script.write_text("#!/bin/bash\nexit 0\n", encoding="utf-8")
        script.chmod(0o755)

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
        return True, None, [{"name": "healthcheck.sh", "status": "pass"}], None

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


def test_deploy_operational_runtime_runtime_root_override(tmp_path):
    """runtime_root override relocates sandbox dir and logs runtime_root_source=override."""
    mgr, state, sandbox_dir = _sample_state(tmp_path)
    custom_rt = tmp_path / "custom-runtime"
    state = state.model_copy(update={"runtime_root": str(custom_rt)})
    fake_proc = MagicMock()
    fake_proc.pid = 55555
    registered = {"web": "http://w.test", "api": "http://a.test"}
    routes_dir = tmp_path / "routes"
    captured_runtime: dict = {}

    def _capture_supervisor(_port, runtime_root, _log_path):
        captured_runtime["path"] = Path(runtime_root)
        return fake_proc

    def _scripts_ok(*_args, **kwargs):
        cb = kwargs.get("on_step_complete")
        if cb:
            cb("start.sh")
        return True, None, [{"name": "healthcheck.sh", "status": "pass"}], None

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
            side_effect=_capture_supervisor,
        ),
        patch("tools.agent_runner.run_sandbox._ensure_required_infra"),
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

    expected_sandbox = (custom_rt / state.id).resolve()
    assert result.success is True
    assert captured_runtime["path"] == expected_sandbox / "runtime"
    log_text = (expected_sandbox / "run.log").read_text(encoding="utf-8")
    assert "runtime_root_source=override" in log_text
    assert f"sandbox_root={expected_sandbox}" in log_text


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
        patch("tools.agent_runner.run_sandbox._ensure_required_infra"),
        patch("tools.agent_runner.run_sandbox._wait_for_proxy_url", return_value=True),
        patch(
            "tools.agent_runner.run_sandbox._run_scripts",
            return_value=(False, "bootstrap failed", [], None),
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


# ── T169: deployer_runner compose env-file ordering and early-failure ────────


def test_deploy_inject_flags_includes_deploy_env(tmp_path):
    """_inject_compose_flags prepends --env-file deploy/.env before sandbox env when present."""
    from services.control_api.services.deployer_runner import _inject_compose_flags

    cwd = tmp_path / "project"
    cwd.mkdir()
    (cwd / "deploy").mkdir()
    (cwd / "deploy" / ".env").write_text("")

    sandbox_env = str(tmp_path / "sandbox" / ".env")
    cmd = _inject_compose_flags("docker compose up -d api", "myproject", sandbox_env, cwd=cwd)

    deploy_env_path = str(cwd / "deploy" / ".env")
    assert deploy_env_path in cmd, f"deploy/.env must appear in command: {cmd}"
    assert sandbox_env in cmd, f"sandbox env must appear in command: {cmd}"
    assert cmd.index(deploy_env_path) < cmd.index(sandbox_env), (
        f"deploy/.env must precede sandbox env: {cmd}"
    )


def test_deploy_fails_early_on_wrong_compose_alias(tmp_path):
    """_do_deploy returns ok=False before any compose up when config shows wrong alias."""
    from services.control_api.services.deployer_runner import _do_deploy

    cwd = tmp_path / "project"
    cwd.mkdir()
    (cwd / "deploy").mkdir()
    (cwd / "deploy" / ".env").write_text("")

    deploy_yml = cwd / ".ai-dev-factory" / "deploy.yml"
    deploy_yml.parent.mkdir(parents=True)
    deploy_yml.write_text(
        "version: '1'\nproject: test\ncomponents:\n  - name: api\n    type: docker\n    service: api\n"
    )

    mgr = SandboxManager(sandboxes_dir=tmp_path / "sandboxes", proxy_routes_dir=tmp_path / "routes")
    mgr._proxy._auto_ensure_infra = False
    sandbox = mgr.create("T001", str(cwd))
    sandbox = sandbox.model_copy(update={"worktree_path": str(cwd)})

    up_called = False

    def mock_run(cmd, **kwargs):
        nonlocal up_called
        m = MagicMock()
        m.returncode = 0
        m.stderr = ""
        if isinstance(cmd, list) and "config" in cmd:
            m.stdout = "sandbox-default-api\nsandbox-default-web\n"
        else:
            if isinstance(cmd, str) and " up " in cmd:
                up_called = True
            m.stdout = ""
        return m

    with patch("services.control_api.services.deployer_runner.subprocess.run", side_effect=mock_run):
        result = _do_deploy("T001", cwd, sandbox=sandbox)

    assert not result.ok, "deploy must fail when compose config alias is wrong"
    assert not up_called, "docker compose up must NOT be called after config validation failure"


def test_deploy_operational_runtime_clones_fresh_source_on_ref(tmp_path):
    """When state.ref is set, deploy_operational_runtime clones a fresh source checkout."""
    mgr, state, sandbox_dir = _sample_state(tmp_path)
    state = state.model_copy(update={"ref": "T171"})

    fake_proc = MagicMock()
    fake_proc.pid = 42
    registered = {"web": "http://w.test", "api": "http://a.test"}
    routes_dir = tmp_path / "routes"

    clone_calls: list[list[str]] = []

    def mock_clone(cmd, *args, **kwargs):
        if isinstance(cmd, list) and "clone" in cmd:
            clone_calls.append(cmd)
            # Create the source directory so the rest of the deploy works.
            target = Path(cmd[-1])
            target.mkdir(parents=True, exist_ok=True)
        m = MagicMock()
        m.returncode = 0
        m.stdout = "T171\n" if (isinstance(cmd, list) and "branch" in cmd) else "abc1234\n"
        m.stderr = ""
        return m

    def _scripts_ok(*_args, **kwargs):
        cb = kwargs.get("on_step_complete")
        if cb:
            cb("start.sh")
        return True, None, [{"name": "healthcheck.sh", "status": "pass"}], None

    with (
        patch(
            "services.control_api.services.sandbox_runtime_deploy.subprocess.run",
            side_effect=mock_clone,
        ),
        patch(
            "services.control_api.services.sandbox_runtime_deploy.resolve_proxy_routes_dir",
            return_value=routes_dir,
        ),
        patch("tools.agent_runner.run_sandbox._start_sandbox_supervisor", return_value=fake_proc),
        patch("tools.agent_runner.run_sandbox._ensure_required_infra"),
        patch("tools.agent_runner.run_sandbox._wait_for_proxy_url", return_value=True),
        patch("tools.agent_runner.run_sandbox._run_scripts", side_effect=_scripts_ok),
        patch(
            "services.control_api.services.proxy_manager.ProxyManager.register",
            return_value=registered,
        ),
    ):
        (routes_dir / f"{state.id}.yml").write_text("http:\n  routers: {}\n")
        result = deploy_operational_runtime(state, sandbox_dir=sandbox_dir, mode="environment")

    assert result.success is True
    assert clone_calls, "git clone must be called when state.ref is set"
    assert any("T171" in str(c) for c in clone_calls), "clone must include the ref branch"


def test_deploy_operational_runtime_aborts_on_clone_failure(tmp_path):
    """When git clone fails, deploy_operational_runtime returns failure before running scripts."""
    mgr, state, sandbox_dir = _sample_state(tmp_path)
    state = state.model_copy(update={"ref": "T171"})

    fake_proc = MagicMock()
    fake_proc.pid = 1

    scripts_called = False

    def fail_clone(cmd, *args, **kwargs):
        m = MagicMock()
        m.returncode = 1 if (isinstance(cmd, list) and "clone" in cmd) else 0
        m.stdout = ""
        m.stderr = "fatal: repository not found"
        return m

    def _scripts_side_effect(*_a, **_kw):
        nonlocal scripts_called
        scripts_called = True
        return True, None, [], None

    with (
        patch(
            "services.control_api.services.sandbox_runtime_deploy.subprocess.run",
            side_effect=fail_clone,
        ),
        patch("tools.agent_runner.run_sandbox._start_sandbox_supervisor", return_value=fake_proc),
        patch("tools.agent_runner.run_sandbox._ensure_required_infra"),
        patch("tools.agent_runner.run_sandbox._run_scripts", side_effect=_scripts_side_effect),
        patch("tools.agent_runner.run_sandbox._stop_sandbox_supervisor"),
    ):
        result = deploy_operational_runtime(state, sandbox_dir=sandbox_dir, mode="environment")

    assert result.success is False
    assert "clone" in (result.error or "").lower()
    assert not scripts_called, "scripts must NOT run when clone fails"


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
        patch("tools.agent_runner.run_sandbox._ensure_required_infra"),
        patch("tools.agent_runner.run_sandbox._wait_for_proxy_url", return_value=True),
        patch(
            "tools.agent_runner.run_sandbox._run_scripts",
            return_value=(True, None, [{"name": "healthcheck.sh", "status": "success"}], None),
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


def test_deploy_operational_runtime_clones_even_without_ref(tmp_path):
    """When state.ref is None, deploy still clones into sandbox_dir/source/."""
    mgr, state, sandbox_dir = _sample_state(tmp_path)
    assert state.ref is None

    fake_proc = MagicMock()
    fake_proc.pid = 42
    registered = {"web": "http://w.test", "api": "http://a.test"}
    routes_dir = tmp_path / "routes"

    clone_args: list[tuple] = []
    scripts_source: list[Path] = []

    def _fake_clone(project_root, source_path, ref, log):
        clone_args.append((project_root, source_path, ref))
        return True, None, "abc1234"

    def _scripts_ok(source, *_args, **kwargs):
        scripts_source.append(source)
        cb = kwargs.get("on_step_complete")
        if cb:
            cb("start.sh")
        return True, None, [{"name": "healthcheck.sh", "status": "pass"}], None

    with (
        patch(
            "services.control_api.services.sandbox_runtime_deploy._clone_fresh_source",
            side_effect=_fake_clone,
        ),
        patch(
            "services.control_api.services.sandbox_runtime_deploy.resolve_proxy_routes_dir",
            return_value=routes_dir,
        ),
        patch("tools.agent_runner.run_sandbox._start_sandbox_supervisor", return_value=fake_proc),
        patch("tools.agent_runner.run_sandbox._ensure_required_infra"),
        patch("tools.agent_runner.run_sandbox._wait_for_proxy_url", return_value=True),
        patch("tools.agent_runner.run_sandbox._run_scripts", side_effect=_scripts_ok),
        patch(
            "services.control_api.services.proxy_manager.ProxyManager.register",
            return_value=registered,
        ),
    ):
        (routes_dir / f"{state.id}.yml").write_text("http:\n  routers: {}\n")
        result = deploy_operational_runtime(state, sandbox_dir=sandbox_dir, mode="environment")

    assert result.success is True
    assert len(clone_args) == 1, "clone must be called even when state.ref is None"
    assert clone_args[0][2] is None, "clone must receive ref=None when state.ref is None"
    assert scripts_source[0] == sandbox_dir / "source", (
        f"_run_scripts must receive sandbox_dir/source, got {scripts_source[0]}"
    )


def test_deploy_operational_runtime_path_validation_fails(tmp_path):
    """Path validation guard returns failure if resolved source escapes sandbox_dir."""
    mgr, state, sandbox_dir = _sample_state(tmp_path)
    fake_proc = MagicMock()
    fake_proc.pid = 1

    # Replace source dir with a symlink pointing outside sandbox_dir.
    source_link = sandbox_dir / "source"
    shutil.rmtree(source_link)
    external_dir = tmp_path / "external"
    external_dir.mkdir()
    source_link.symlink_to(external_dir)

    scripts_called = False

    def _scripts_side(*_a, **_kw):
        nonlocal scripts_called
        scripts_called = True
        return True, None, [], None

    with (
        patch(
            "services.control_api.services.sandbox_runtime_deploy._clone_fresh_source",
            return_value=(True, None, "abc1234"),
        ),
        patch("tools.agent_runner.run_sandbox._start_sandbox_supervisor", return_value=fake_proc),
        patch("tools.agent_runner.run_sandbox._ensure_required_infra"),
        patch("tools.agent_runner.run_sandbox._run_scripts", side_effect=_scripts_side),
        patch("tools.agent_runner.run_sandbox._stop_sandbox_supervisor"),
    ):
        result = deploy_operational_runtime(state, sandbox_dir=sandbox_dir, mode="environment")

    assert result.success is False
    assert "path validation" in (result.error or "").lower()
    assert not scripts_called, "scripts must NOT run after path validation failure"
