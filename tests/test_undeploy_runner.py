"""Tests for the generic undeploy and cleanup lifecycle (T148)."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.control_api.models.schemas import DeployComponent, DeployProfile
from services.control_api.services.undeploy_runner import run_cleanup, run_undeploy


def _profile(undeploy=None, cleanup=None) -> DeployProfile:
    return DeployProfile(
        version=1,
        project="test",
        components=[],
        undeploy=undeploy or [],
        cleanup=cleanup or [],
    )


def _ok_run(*args, **kwargs):
    m = MagicMock()
    m.returncode = 0
    m.stdout = ""
    m.stderr = ""
    return m


def _fail_run(*args, **kwargs):
    m = MagicMock()
    m.returncode = 1
    m.stdout = ""
    m.stderr = "error"
    return m


# ── run_undeploy tests ────────────────────────────────────────────────────────

def test_undeploy_steps_executed_in_reverse_order(tmp_path):
    """Undeploy steps must run in reverse order relative to the undeploy list."""
    calls: list[str] = []

    def capture_run(cmd, **kwargs):
        calls.append(cmd)
        return _ok_run()

    profile = _profile(undeploy=[
        DeployComponent(name="web", type="host", command="echo stop-web"),
        DeployComponent(name="api", type="host", command="echo stop-api"),
        DeployComponent(name="db", type="host", command="echo stop-db"),
    ])

    with patch(
        "services.control_api.services.undeploy_runner.subprocess.run",
        side_effect=capture_run,
    ):
        run_undeploy(profile, "proj", "/tmp/env", tmp_path, "s1")

    assert calls == ["echo stop-db", "echo stop-api", "echo stop-web"]


def test_cleanup_without_deploy_yml(tmp_path):
    """When profile is None, run_undeploy falls back to docker compose down without error."""
    with patch(
        "services.control_api.services.undeploy_runner.subprocess.run",
        side_effect=_ok_run,
    ) as mock_run:
        run_undeploy(None, "myproject", "/tmp/env", tmp_path, "s1")

    assert mock_run.called
    cmd = mock_run.call_args[0][0]
    assert "docker compose" in cmd
    assert "myproject" in cmd
    assert "down" in cmd


def test_undeploy_no_undeploy_section_falls_back(tmp_path):
    """A profile with an empty undeploy list also triggers the fallback."""
    with patch(
        "services.control_api.services.undeploy_runner.subprocess.run",
        side_effect=_ok_run,
    ) as mock_run:
        run_undeploy(_profile(), "proj", "/tmp/env", tmp_path, "s1")

    assert mock_run.called
    cmd = mock_run.call_args[0][0]
    assert "down" in cmd


def test_undeploy_docker_type_uses_compose_down(tmp_path):
    """A docker-type undeploy step issues docker compose down with project isolation."""
    profile = _profile(undeploy=[
        DeployComponent(name="app", type="docker", service="api"),
    ])

    with patch(
        "services.control_api.services.undeploy_runner.subprocess.run",
        side_effect=_ok_run,
    ) as mock_run:
        run_undeploy(profile, "myproj", "/tmp/env", tmp_path, "s1")

    cmd = mock_run.call_args[0][0]
    assert "docker compose" in cmd
    assert "-p myproj" in cmd
    assert "--env-file /tmp/env" in cmd
    assert "down" in cmd
    assert "--remove-orphans" in cmd


def test_undeploy_step_failure_does_not_abort(tmp_path):
    """A failing undeploy step logs a warning; remaining steps still execute."""
    calls: list[str] = []

    def side_effect(cmd, **kwargs):
        calls.append(cmd)
        m = MagicMock()
        m.returncode = 1 if len(calls) == 1 else 0
        m.stdout = ""
        m.stderr = "fail"
        return m

    profile = _profile(undeploy=[
        DeployComponent(name="a", type="host", command="echo a"),
        DeployComponent(name="b", type="host", command="echo b"),
    ])

    with patch(
        "services.control_api.services.undeploy_runner.subprocess.run",
        side_effect=side_effect,
    ):
        run_undeploy(profile, "proj", "/tmp/env", tmp_path, "s1")

    assert len(calls) == 2


# ── run_cleanup tests ─────────────────────────────────────────────────────────

def test_stale_pid_removed(tmp_path):
    """run_cleanup removes *.pid files from sandbox_dir and runtime_root."""
    runtime_root = tmp_path / "runtime"
    runtime_root.mkdir()
    sandbox_dir = tmp_path / "sandbox"
    sandbox_dir.mkdir()

    (runtime_root / "worker.pid").write_text('{"pid": 99999}')
    (sandbox_dir / "run.pid").write_text('{"pid": 99999}')

    run_cleanup(None, sandbox_dir, runtime_root, "s1")

    assert not (runtime_root / "worker.pid").exists()
    assert not (sandbox_dir / "run.pid").exists()


def test_stale_lock_removed(tmp_path):
    """run_cleanup removes *.lock files from sandbox_dir and runtime_root."""
    runtime_root = tmp_path / "runtime"
    runtime_root.mkdir()
    sandbox_dir = tmp_path / "sandbox"
    sandbox_dir.mkdir()

    (runtime_root / "deploy.lock").write_text('locked')
    (sandbox_dir / "run.lock").write_text('locked')

    run_cleanup(None, sandbox_dir, runtime_root, "s1")

    assert not (runtime_root / "deploy.lock").exists()
    assert not (sandbox_dir / "run.lock").exists()


def test_cleanup_hooks_executed(tmp_path):
    """run_cleanup executes host-type cleanup hook steps from the profile."""
    sandbox_dir = tmp_path / "sandbox"
    sandbox_dir.mkdir()

    profile = _profile(cleanup=[
        DeployComponent(name="prune", type="host", command="echo cleanup"),
    ])

    with patch(
        "services.control_api.services.undeploy_runner.subprocess.run",
        side_effect=_ok_run,
    ) as mock_run:
        run_cleanup(profile, sandbox_dir, None, "s1")

    assert mock_run.called
    assert mock_run.call_args[0][0] == "echo cleanup"


def test_cleanup_hook_failure_does_not_abort_stale_removal(tmp_path):
    """A failing cleanup hook does not prevent stale file removal."""
    sandbox_dir = tmp_path / "sandbox"
    sandbox_dir.mkdir()
    (sandbox_dir / "stale.pid").write_text("1234")

    profile = _profile(cleanup=[
        DeployComponent(name="failing", type="host", command="false"),
    ])

    with patch(
        "services.control_api.services.undeploy_runner.subprocess.run",
        side_effect=_fail_run,
    ):
        run_cleanup(profile, sandbox_dir, None, "s1")

    assert not (sandbox_dir / "stale.pid").exists()


def test_cleanup_missing_runtime_root_is_safe(tmp_path):
    """run_cleanup does not raise when runtime_root is None."""
    sandbox_dir = tmp_path / "sandbox"
    sandbox_dir.mkdir()
    (sandbox_dir / "run.pid").write_text("1234")

    run_cleanup(None, sandbox_dir, None, "s1")

    assert not (sandbox_dir / "run.pid").exists()


# ── stop.sh tests (run_sandbox.py integration) ───────────────────────────────

def test_stop_script_executed_on_sandbox_cleanup(tmp_path):
    """_run_stop_script calls stop.sh and tolerates a non-zero exit code."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "agent_runner"))
    from run_sandbox import _run_stop_script  # noqa: PLC0415

    worktree = tmp_path / "worktree"
    scripts_dir = worktree / ".ai-dev-factory" / "scripts"
    scripts_dir.mkdir(parents=True)
    stop_sh = scripts_dir / "stop.sh"
    stop_sh.write_text("#!/usr/bin/env bash\nexit 1\n")
    log_path = tmp_path / "run.log"

    calls: list[str] = []

    def capture(cmd, **kwargs):
        calls.append(str(cmd))
        m = MagicMock()
        m.returncode = 1
        m.stdout = ""
        m.stderr = ""
        return m

    with patch("subprocess.run", side_effect=capture):
        _run_stop_script(worktree, log_path)

    assert len(calls) == 1
    log_content = log_path.read_text()
    assert "continuing cleanup" in log_content


def test_stop_script_skipped_when_missing(tmp_path):
    """_run_stop_script logs a message and does not raise when stop.sh is absent."""
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "agent_runner"))
    from run_sandbox import _run_stop_script  # noqa: PLC0415

    worktree = tmp_path / "worktree"
    worktree.mkdir()
    log_path = tmp_path / "run.log"

    with patch("subprocess.run") as mock_run:
        _run_stop_script(worktree, log_path)

    mock_run.assert_not_called()
    assert "not found" in log_path.read_text()
