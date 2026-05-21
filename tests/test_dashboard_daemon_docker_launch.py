"""Regression tests for dashboard Start Daemon host-vs-Docker architecture.

The dashboard's POST /daemon/start must NOT spawn the daemon inside Docker.
This module pins the three execution paths of ``daemon_manager.start``:

1. ``AI_DEV_FACTORY_HOST_DAEMON_COMMAND`` set → run that shell command
   verbatim (typically an ssh wrapper) and do NOT preflight-check the
   API container's environment.
2. API runs in Docker, no host launcher → refuse with a copy-paste
   ``host_command`` field in the ``ActionResult``. No PID file written.
3. API runs on host → existing preflight + Popen flow.

It also pins ``_is_running_in_docker`` against the trusted signals
(``AI_DEV_FACTORY_API_IN_DOCKER`` env var, ``/.dockerenv`` file,
``/proc/1/cgroup`` content).
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def daemon_manager(monkeypatch):
    """Provide ``daemon_manager`` with all Docker detection signals cleared."""
    monkeypatch.delenv("AI_DEV_FACTORY_API_IN_DOCKER", raising=False)
    monkeypatch.delenv("AI_DEV_FACTORY_HOST_DAEMON_COMMAND", raising=False)
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    monkeypatch.delenv("AI_DEV_FACTORY_PROJECT_ROOT", raising=False)
    monkeypatch.delenv("AI_DEV_FACTORY_ISSUE_REPO", raising=False)
    from services.control_api.services import daemon_manager as dm
    return dm


# ── 1. Docker detection ───────────────────────────────────────────────────────

def test_is_running_in_docker_respects_env_var(daemon_manager, monkeypatch):
    monkeypatch.setenv("AI_DEV_FACTORY_API_IN_DOCKER", "1")
    assert daemon_manager._is_running_in_docker() is True


def test_is_running_in_docker_accepts_true_string(daemon_manager, monkeypatch):
    monkeypatch.setenv("AI_DEV_FACTORY_API_IN_DOCKER", "true")
    assert daemon_manager._is_running_in_docker() is True


def test_is_running_in_docker_detects_dockerenv_file(daemon_manager, monkeypatch, tmp_path):
    """Simulate ``/.dockerenv`` existence — patch ``Path.exists`` only for that path."""
    from services.control_api.services import daemon_manager as dm
    real_exists = dm.Path.exists

    def fake_exists(self):
        if str(self) == "/.dockerenv":
            return True
        return real_exists(self)

    with patch.object(dm.Path, "exists", fake_exists):
        assert daemon_manager._is_running_in_docker() is True


def test_is_running_in_docker_false_on_clean_host(daemon_manager, monkeypatch):
    # No env var, no /.dockerenv on macOS CI host: must return False.
    # (If the test runner itself happens to be in Docker this still passes
    # because the env-var check above is exhaustive for our test matrix.)
    monkeypatch.delenv("AI_DEV_FACTORY_API_IN_DOCKER", raising=False)
    # On hosts where /.dockerenv exists, this test is skipped.
    if Path("/.dockerenv").exists():
        pytest.skip("test runner is itself in Docker — signal cannot be falsified")
    assert daemon_manager._is_running_in_docker() is False


# ── 2. Suggested host command ────────────────────────────────────────────────

def test_recommended_host_command_uses_runtime_root_env(daemon_manager, monkeypatch, tmp_path):
    monkeypatch.setenv("AI_DEV_FACTORY_RUNTIME_ROOT", "/srv/runtime")
    monkeypatch.setenv("AI_DEV_FACTORY_ISSUE_REPO", "Billboc31/ai-dev-factory")
    cmd = daemon_manager._recommended_host_command(
        tmp_path,
        "claude --dangerously-skip-permissions",
    )
    assert "cd /srv/runtime/clones/ai-dev-factory" in cmd
    assert "source .venv/bin/activate" in cmd
    assert "export AI_DEV_FACTORY_RUNTIME_ROOT=/srv/runtime" in cmd
    assert "tools/agent_runner/run_daemon.py" in cmd
    assert "--exec-cmd \"claude --dangerously-skip-permissions\"" in cmd
    assert "--poll-issues" in cmd
    assert "--auto-commit" in cmd
    assert "--auto-push" in cmd
    assert "--auto-include-code" in cmd
    assert "--issue-repo Billboc31/ai-dev-factory" in cmd


def test_recommended_host_command_default_runtime_root(daemon_manager, monkeypatch, tmp_path):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    cmd = daemon_manager._recommended_host_command(tmp_path, "claude")
    # Falls back to ~/runtime/ai-dev-factory and expands the leading ~.
    assert "runtime/ai-dev-factory" in cmd
    assert "<owner>/<repo>" in cmd  # placeholder for issue repo


# ── 3. start() in Docker without host launcher → refuse ──────────────────────

def test_start_in_docker_without_host_command_refuses_with_host_command(
    daemon_manager, monkeypatch, tmp_path,
):
    monkeypatch.setenv("AI_DEV_FACTORY_API_IN_DOCKER", "1")
    monkeypatch.setenv("AI_DEV_FACTORY_RUNTIME_ROOT", "/srv/runtime")
    monkeypatch.delenv("AI_DEV_FACTORY_HOST_DAEMON_COMMAND", raising=False)

    pid_path = daemon_manager._pid_path(tmp_path)

    with patch.object(daemon_manager, "get_status") as gs, \
         patch.object(daemon_manager.subprocess, "Popen") as popen:
        gs.return_value = MagicMock(running=False, pid=None)
        result = daemon_manager.start(tmp_path, "claude")

    assert result.ok is False
    assert "Daemon cannot start inside Docker" in result.message
    assert "AI_DEV_FACTORY_HOST_DAEMON_COMMAND" in result.message
    # host_command MUST be populated so the dashboard can show copy block.
    assert result.host_command is not None
    assert "tools/agent_runner/run_daemon.py" in result.host_command
    popen.assert_not_called()
    assert not pid_path.exists(), "PID file MUST NOT be created on refusal"


def test_start_in_docker_refusal_appends_to_daemon_log(
    daemon_manager, monkeypatch, tmp_path,
):
    monkeypatch.setenv("AI_DEV_FACTORY_API_IN_DOCKER", "1")
    monkeypatch.delenv("AI_DEV_FACTORY_HOST_DAEMON_COMMAND", raising=False)

    log_path = daemon_manager._log_path(tmp_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    with patch.object(daemon_manager, "get_status") as gs:
        gs.return_value = MagicMock(running=False, pid=None)
        daemon_manager.start(tmp_path, "claude")

    assert log_path.exists()
    text = log_path.read_text(encoding="utf-8")
    assert "startup refused" in text
    assert "in_docker=true" in text


# ── 4. start() with AI_DEV_FACTORY_HOST_DAEMON_COMMAND set ───────────────────

def test_start_uses_host_command_via_shell_when_configured(
    daemon_manager, monkeypatch, tmp_path,
):
    host_cmd = (
        "ssh host -- 'cd ~/runtime/ai-dev-factory/clones/ai-dev-factory && "
        "source .venv/bin/activate && "
        "python tools/agent_runner/run_daemon.py --poll-issues --auto-commit'"
    )
    monkeypatch.setenv("AI_DEV_FACTORY_API_IN_DOCKER", "1")
    monkeypatch.setenv("AI_DEV_FACTORY_HOST_DAEMON_COMMAND", host_cmd)

    captured_popen: dict = {}

    class FakeProc:
        pid = 99001

    def fake_popen(args, **kwargs):
        captured_popen["args"] = args
        captured_popen["shell"] = kwargs.get("shell")
        captured_popen["env"] = kwargs.get("env")
        return FakeProc()

    with patch.object(daemon_manager, "get_status") as gs, \
         patch.object(daemon_manager.subprocess, "Popen", side_effect=fake_popen):
        gs.return_value = MagicMock(running=False, pid=None)
        result = daemon_manager.start(tmp_path, "claude")

    assert result.ok is True
    assert "host daemon launcher started" in result.message
    assert captured_popen["args"] == host_cmd
    assert captured_popen["shell"] is True
    assert captured_popen["env"].get("PYTHONDONTWRITEBYTECODE") == "1"


def test_start_uses_host_command_even_when_not_in_docker(
    daemon_manager, monkeypatch, tmp_path,
):
    """If an operator explicitly wants the host launcher (even on the host
    side), the env var wins over the preflight. They have chosen the
    explicit path."""
    monkeypatch.delenv("AI_DEV_FACTORY_API_IN_DOCKER", raising=False)
    monkeypatch.setenv("AI_DEV_FACTORY_HOST_DAEMON_COMMAND", "echo ok")

    with patch.object(daemon_manager, "get_status") as gs, \
         patch.object(daemon_manager.subprocess, "Popen") as popen, \
         patch.object(daemon_manager, "check_environment") as ce:
        proc = MagicMock(); proc.pid = 4242
        popen.return_value = proc
        gs.return_value = MagicMock(running=False, pid=None)

        result = daemon_manager.start(tmp_path, "claude")

    assert result.ok is True
    # check_environment is skipped on the host-launcher path
    ce.assert_not_called()


# ── 5. Host mode (no Docker, no override) → existing preflight + Popen ───────

def test_start_on_host_still_uses_preflight_and_local_popen(
    daemon_manager, monkeypatch, tmp_path,
):
    monkeypatch.delenv("AI_DEV_FACTORY_API_IN_DOCKER", raising=False)
    monkeypatch.delenv("AI_DEV_FACTORY_HOST_DAEMON_COMMAND", raising=False)

    if Path("/.dockerenv").exists():
        pytest.skip("test runner is itself in Docker — host path cannot be exercised")

    facts = {
        "project_root": str(tmp_path),
        "cwd": str(tmp_path),
        "runs_dir": str(daemon_manager.resolve_runs_dir(tmp_path)),
        "worktrees_dir": "/wt",
        "logs_dir": str(daemon_manager.resolve_logs_dir(tmp_path)),
        "runtime_root": "<unset>",
        "python": "/usr/bin/python3",
        "git_path": "/usr/bin/git",
        "gh_path": "/usr/bin/gh",
    }
    with patch.object(daemon_manager, "get_status") as gs, \
         patch.object(daemon_manager, "check_environment", return_value=(True, [], facts)), \
         patch.object(daemon_manager.subprocess, "Popen") as popen, \
         patch.object(daemon_manager, "_write_pid_file") as wpid:
        proc = MagicMock(); proc.pid = 7777
        popen.return_value = proc
        gs.return_value = MagicMock(running=False, pid=None)

        result = daemon_manager.start(tmp_path, "claude")

    assert result.ok is True
    # No host_command leaks into the success ActionResult on the host path
    assert result.host_command is None
    popen.assert_called_once()
    wpid.assert_called_once()
    # Local Popen, NOT shell mode
    assert popen.call_args.kwargs.get("shell") in (None, False)
