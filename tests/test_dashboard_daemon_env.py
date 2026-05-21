"""Regression tests for the dashboard daemon execution environment.

Failure mode reproduced: when the API runs in an environment without ``gh``
or without ``.git`` access, the dashboard's "Start Daemon" still happily
spawned a degraded process and the dashboard reported it as "running".

These tests pin the new contract:

- ``check_environment`` reports each fact (project_root, cwd, gh path,
  git path, runtime root, runs/worktrees/logs dirs);
- missing ``gh`` is a hard error (not a degraded mode);
- missing ``.git`` is a hard error;
- non-writable ``runs_dir`` is a hard error;
- ``start`` refuses (and does NOT write a PID file) when preflight fails;
- ``start`` writes the environment banner to ``daemon.log`` even on failure
  so the dashboard's activity stream surfaces the diagnosis;
- ``AI_DEV_FACTORY_PROJECT_ROOT`` overrides ``Path.cwd()`` in ``create_app``.
"""

from __future__ import annotations

import importlib
import os
import sys
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


sys.path.insert(0, str(Path(__file__).parent.parent))


# ── helpers ──────────────────────────────────────────────────────────────────

def _init_repo(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.email", "x@y"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "x"], cwd=tmp_path, check=True)
    (tmp_path / "README.md").write_text("x")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "seed"], cwd=tmp_path, check=True)


# ── 1. check_environment: facts ──────────────────────────────────────────────

def test_check_environment_reports_all_facts(tmp_path: Path):
    _init_repo(tmp_path)
    from services.control_api.services import daemon_manager
    ok, errors, facts = daemon_manager.check_environment(tmp_path)

    # Every key the dashboard / logs should display
    for key in (
        "project_root", "cwd", "runtime_root",
        "runs_dir", "worktrees_dir", "logs_dir",
        "python", "git_path", "gh_path",
    ):
        assert key in facts, f"facts missing key {key!r}"

    assert facts["project_root"] == str(tmp_path)
    assert facts["cwd"] == str(tmp_path)
    # python and git should be discoverable on the test runner
    assert facts["python"] == sys.executable


def test_check_environment_passes_on_full_repo(tmp_path: Path, monkeypatch):
    _init_repo(tmp_path)
    # Pretend gh is available (the test env may not actually have it)
    monkeypatch.setenv("PATH", f"{tmp_path}:{os.environ.get('PATH', '')}")
    fake_gh = tmp_path / "gh"
    fake_gh.write_text("#!/bin/sh\necho ok\n")
    fake_gh.chmod(0o755)

    from services.control_api.services import daemon_manager
    ok, errors, facts = daemon_manager.check_environment(tmp_path)

    assert ok, f"expected ok but got errors: {errors}"
    assert errors == []
    assert facts["gh_path"].endswith("/gh")


# ── 2. missing dependencies are hard errors ──────────────────────────────────

def test_check_environment_fails_when_gh_missing(tmp_path: Path):
    _init_repo(tmp_path)
    from services.control_api.services import daemon_manager
    with patch("services.control_api.services.daemon_manager.shutil.which") as which:
        which.side_effect = lambda name: None if name == "gh" else f"/usr/bin/{name}"
        ok, errors, facts = daemon_manager.check_environment(tmp_path)
    assert not ok
    assert any("gh CLI not found" in e for e in errors)
    assert facts["gh_path"] == "<missing>"


def test_check_environment_fails_when_git_missing(tmp_path: Path):
    _init_repo(tmp_path)
    from services.control_api.services import daemon_manager
    with patch("services.control_api.services.daemon_manager.shutil.which") as which:
        which.side_effect = lambda name: None if name == "git" else f"/usr/bin/{name}"
        ok, errors, facts = daemon_manager.check_environment(tmp_path)
    assert not ok
    assert any("git not found" in e for e in errors)


def test_check_environment_fails_without_dot_git(tmp_path: Path):
    """A directory that is not a git working tree must be rejected."""
    # No _init_repo — tmp_path is a plain directory.
    from services.control_api.services import daemon_manager
    with patch("services.control_api.services.daemon_manager.shutil.which") as which:
        which.side_effect = lambda name: f"/usr/bin/{name}"  # all CLIs present
        ok, errors, facts = daemon_manager.check_environment(tmp_path)
    assert not ok
    assert any("no .git" in e or "not a git working tree" in e for e in errors), errors


def test_check_environment_fails_when_runs_dir_unwritable(tmp_path: Path):
    _init_repo(tmp_path)
    from services.control_api.services import daemon_manager
    with patch("services.control_api.services.daemon_manager.shutil.which") as which, \
         patch("services.control_api.services.daemon_manager.resolve_runs_dir") as runs:
        which.side_effect = lambda name: f"/usr/bin/{name}"
        # Point runs_dir at a path whose parent does not exist and cannot be created
        runs.return_value = Path("/nonexistent/forbidden/runs")
        ok, errors, facts = daemon_manager.check_environment(tmp_path)
    assert not ok
    assert any("runs_dir not writable" in e for e in errors), errors


# ── 3. start() refuses when preflight fails, no PID file written ─────────────

def test_start_refuses_and_does_not_write_pid_on_preflight_failure(tmp_path: Path):
    from services.control_api.services import daemon_manager

    pid_path = daemon_manager._pid_path(tmp_path)

    with patch.object(
        daemon_manager, "check_environment",
        return_value=(False, ["gh CLI not found in PATH — synthetic"], {
            "project_root": str(tmp_path),
            "cwd": str(tmp_path),
            "runs_dir": str(daemon_manager.resolve_runs_dir(tmp_path)),
            "worktrees_dir": "/x",
            "logs_dir": str(daemon_manager.resolve_logs_dir(tmp_path)),
            "runtime_root": "<unset>",
            "python": sys.executable,
            "git_path": "/usr/bin/git",
            "gh_path": "<missing>",
        }),
    ), patch.object(daemon_manager, "get_status") as gs, \
         patch.object(daemon_manager.subprocess, "Popen") as popen:
        gs.return_value = MagicMock(running=False, pid=None)
        result = daemon_manager.start(tmp_path, "claude")

        popen.assert_not_called()  # MUST not spawn
        assert not result.ok
        assert "gh CLI not found" in result.message
        assert not pid_path.exists(), "PID file must NOT be created on preflight failure"


def test_start_writes_environment_banner_to_log_on_refusal(tmp_path: Path):
    from services.control_api.services import daemon_manager

    log_path = daemon_manager._log_path(tmp_path)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    with patch.object(
        daemon_manager, "check_environment",
        return_value=(False, ["gh CLI not found in PATH — synthetic"], {
            "project_root": str(tmp_path),
            "cwd": str(tmp_path),
            "runs_dir": str(daemon_manager.resolve_runs_dir(tmp_path)),
            "worktrees_dir": "/wt",
            "logs_dir": str(daemon_manager.resolve_logs_dir(tmp_path)),
            "runtime_root": "<unset>",
            "python": sys.executable,
            "git_path": "/usr/bin/git",
            "gh_path": "<missing>",
        }),
    ), patch.object(daemon_manager, "get_status") as gs:
        gs.return_value = MagicMock(running=False, pid=None)
        daemon_manager.start(tmp_path, "claude")

    assert log_path.exists()
    text = log_path.read_text(encoding="utf-8")
    assert "startup refused" in text
    assert "project_root=" in text
    assert "ERROR" in text
    assert "gh CLI not found" in text


def test_start_succeeds_when_environment_is_valid(tmp_path: Path):
    from services.control_api.services import daemon_manager

    with patch.object(
        daemon_manager, "check_environment",
        return_value=(True, [], {
            "project_root": str(tmp_path),
            "cwd": str(tmp_path),
            "runs_dir": str(daemon_manager.resolve_runs_dir(tmp_path)),
            "worktrees_dir": "/wt",
            "logs_dir": str(daemon_manager.resolve_logs_dir(tmp_path)),
            "runtime_root": "<unset>",
            "python": sys.executable,
            "git_path": "/usr/bin/git",
            "gh_path": "/usr/bin/gh",
        }),
    ), patch.object(daemon_manager, "get_status") as gs, \
         patch.object(daemon_manager, "_write_pid_file") as wpid, \
         patch.object(daemon_manager.subprocess, "Popen") as popen:
        gs.return_value = MagicMock(running=False, pid=None)
        proc = MagicMock()
        proc.pid = 4242
        popen.return_value = proc
        result = daemon_manager.start(tmp_path, "claude")

    assert result.ok, result.message
    popen.assert_called_once()
    wpid.assert_called_once()
    args = popen.call_args
    # Banner facts must drive the actual command — worktrees_dir must come
    # from the facts dict, not be silently recomputed elsewhere.
    cmd = args.args[0]
    assert "--worktrees-dir" in cmd
    assert "/wt" in cmd


# ── 4. AI_DEV_FACTORY_PROJECT_ROOT override ─────────────────────────────────

def test_create_app_respects_project_root_env_var(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("AI_DEV_FACTORY_PROJECT_ROOT", str(tmp_path))
    # Re-import main so the env var is read at create_app() call time
    from services.control_api import main as control_main
    importlib.reload(control_main)
    app = control_main.create_app()
    assert app.state.project_root == tmp_path.resolve()


def test_create_app_falls_back_to_cwd_when_env_var_unset(tmp_path: Path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_PROJECT_ROOT", raising=False)
    monkeypatch.chdir(tmp_path)
    from services.control_api import main as control_main
    importlib.reload(control_main)
    app = control_main.create_app()
    assert app.state.project_root == tmp_path


# ── 5. log de-duplication (run_daemon) ───────────────────────────────────────

def test_run_daemon_log_does_not_double_write_when_stdout_is_redirected(tmp_path: Path, monkeypatch):
    """Spawning via Popen redirects stdout to ``daemon.log``; ``_log`` must NOT
    mirror to ``_LOG_FILE`` in that case (it would duplicate every line)."""
    sys.path.insert(0, str(Path(__file__).parent.parent / "tools" / "agent_runner"))
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "_t124_run_daemon",
        Path(__file__).parent.parent / "tools" / "agent_runner" / "run_daemon.py",
    )
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]

    log_file = tmp_path / "daemon.log"
    mod._LOG_FILE = log_file

    captured: list[str] = []

    class FakeStdout:
        def write(self, s):
            captured.append(s)

        def flush(self):
            pass

        def isatty(self):
            return False  # simulate Popen redirection

    with patch.object(mod.sys, "stdout", FakeStdout()):
        mod._log("hello world")

    assert any("hello world" in s for s in captured), "print must still happen"
    assert not log_file.exists(), (
        "_LOG_FILE must not be written when stdout is redirected (it would duplicate)"
    )


def test_run_daemon_log_mirrors_to_file_in_interactive_mode(tmp_path: Path):
    sys.path.insert(0, str(Path(__file__).parent.parent / "tools" / "agent_runner"))
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "_t124b_run_daemon",
        Path(__file__).parent.parent / "tools" / "agent_runner" / "run_daemon.py",
    )
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]

    log_file = tmp_path / "daemon.log"
    mod._LOG_FILE = log_file

    class FakeTty:
        def write(self, s):
            pass

        def flush(self):
            pass

        def isatty(self):
            return True

    with patch.object(mod.sys, "stdout", FakeTty()):
        mod._log("interactive line")

    assert log_file.exists()
    assert "interactive line" in log_file.read_text(encoding="utf-8")
