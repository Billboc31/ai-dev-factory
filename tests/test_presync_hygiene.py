"""Regression tests for pre-sync runtime hygiene.

Covers:
1. ``_clean_runtime_before_sync`` discards runtime garbage (``runtime.log``,
   ``*.pyc``, ``__pycache__/``, daemon lock, SQLite live DB, etc.) so the
   subsequent ``git pull --rebase`` is not blocked by it.
2. Real code dirty files are left untouched: the caller (or git itself)
   decides what to do with them.
3. ``PYTHONDONTWRITEBYTECODE=1`` is propagated to every Python subprocess
   the daemon spawns (run_ticket worker, issue intake, control-api spawned
   daemon, and step-level planner/coder/reviewer/tester invocations).
"""

from __future__ import annotations

import importlib.util
import os
import sys
import subprocess
import textwrap
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest


TOOLS_DIR = Path(__file__).parent.parent / "tools" / "agent_runner"
sys.path.insert(0, str(TOOLS_DIR))


def _load_run_daemon():
    spec = importlib.util.spec_from_file_location(
        "_test_run_daemon", TOOLS_DIR / "run_daemon.py"
    )
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def _init_git_repo(tmp_path: Path) -> None:
    """Create a minimal initialised git repo for sync hygiene tests."""
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@test"], cwd=tmp_path, check=True
    )
    subprocess.run(["git", "config", "user.name", "test"], cwd=tmp_path, check=True)


# ── 1. pre-sync hygiene ──────────────────────────────────────────────────────

def test_dirty_runtime_log_before_sync_is_cleaned(tmp_path: Path):
    """An untracked ``runs/<TID>/runtime.log`` must be removed by the
    pre-sync hygiene so ``git pull --rebase`` can proceed."""
    _init_git_repo(tmp_path)
    (tmp_path / "README.md").write_text("seed")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "seed"], cwd=tmp_path, check=True
    )

    # Create an untracked runtime.log — gitignored in real repo, but here it
    # appears as `??` to test the rm path.
    run_dir = tmp_path / "runs" / "T999"
    run_dir.mkdir(parents=True)
    log = run_dir / "runtime.log"
    log.write_text("noise from previous cycle")

    daemon = _load_run_daemon()
    cleaned, real = daemon._clean_runtime_before_sync("T999", cwd=str(tmp_path))

    assert any("runs/T999/runtime.log" in c for c in cleaned)
    assert not log.exists(), "untracked runtime.log must be removed"
    assert real == []


def test_dirty_pycache_files_before_sync_are_cleaned(tmp_path: Path):
    """``__pycache__/*.pyc`` files (untracked) must be physically removed."""
    _init_git_repo(tmp_path)
    (tmp_path / "README.md").write_text("seed")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "seed"], cwd=tmp_path, check=True
    )

    cache_dir = tmp_path / "services" / "__pycache__"
    cache_dir.mkdir(parents=True)
    pyc = cache_dir / "module.cpython-314.pyc"
    pyc.write_bytes(b"\x00")

    daemon = _load_run_daemon()
    cleaned, real = daemon._clean_runtime_before_sync("T999", cwd=str(tmp_path))

    assert any("__pycache__" in c for c in cleaned)
    assert not pyc.exists()
    assert real == []


def test_tracked_runtime_log_before_sync_is_reset_to_head(tmp_path: Path):
    """When ``runtime.log`` is *tracked* (legacy pre-gitignore commit) and
    dirty, the hygiene must reset it to HEAD so the rebase can proceed."""
    _init_git_repo(tmp_path)
    run_dir = tmp_path / "runs" / "T999"
    run_dir.mkdir(parents=True)
    log = run_dir / "runtime.log"
    log.write_text("baseline\n")
    subprocess.run(["git", "add", "-f", "."], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "tracked-runtime"], cwd=tmp_path, check=True
    )

    log.write_text("DIRTY runtime log content that should never block sync\n")
    daemon = _load_run_daemon()
    cleaned, real = daemon._clean_runtime_before_sync("T999", cwd=str(tmp_path))

    assert any("reset:runs/T999/runtime.log" == c or "runs/T999/runtime.log" in c for c in cleaned)
    assert log.read_text() == "baseline\n", "tracked runtime.log must be reset to HEAD"
    assert real == []


def test_real_code_dirty_files_before_sync_are_preserved(tmp_path: Path):
    """A real code change must NOT be touched by the pre-sync hygiene."""
    _init_git_repo(tmp_path)
    code_file = tmp_path / "tools" / "agent_runner" / "module.py"
    code_file.parent.mkdir(parents=True)
    code_file.write_text("original\n")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "seed"], cwd=tmp_path, check=True
    )
    code_file.write_text("LOCAL DEVELOPER WORK\n")

    daemon = _load_run_daemon()
    cleaned, real = daemon._clean_runtime_before_sync("T999", cwd=str(tmp_path))

    assert cleaned == [], "no runtime files to clean"
    assert "tools/agent_runner/module.py" in real
    assert code_file.read_text() == "LOCAL DEVELOPER WORK\n", (
        "real code dirty must not be modified by pre-sync hygiene"
    )


def test_egg_info_before_sync_is_cleaned(tmp_path: Path):
    """``pip install -e .`` metadata must not block pre-sync rebase."""
    _init_git_repo(tmp_path)
    (tmp_path / "README.md").write_text("seed")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "seed"], cwd=tmp_path, check=True
    )

    egg_dir = tmp_path / "backend" / "timizer_backend.egg-info"
    egg_dir.mkdir(parents=True)
    (egg_dir / "PKG-INFO").write_text("Metadata-Version: 2.1\n")
    (egg_dir / "SOURCES.txt").write_text("setup.py\n")

    daemon = _load_run_daemon()
    cleaned, real = daemon._clean_runtime_before_sync("T001", cwd=str(tmp_path))

    assert any("egg-info" in c for c in cleaned)
    assert not egg_dir.exists(), "egg-info directory must be removed before sync"
    assert real == []


def test_mixed_dirty_only_cleans_runtime_and_logs_real(tmp_path: Path):
    """Runtime + real code dirty: hygiene cleans runtime, preserves real."""
    _init_git_repo(tmp_path)
    code_file = tmp_path / "tools" / "module.py"
    code_file.parent.mkdir(parents=True)
    code_file.write_text("original\n")
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "commit", "-q", "-m", "seed"], cwd=tmp_path, check=True
    )
    # Real dirty
    code_file.write_text("LOCAL CHANGE\n")
    # Runtime garbage (untracked)
    (tmp_path / "runs" / "T999").mkdir(parents=True)
    (tmp_path / "runs" / "T999" / "runtime.log").write_text("noise")
    cache_dir = tmp_path / "tools" / "__pycache__"
    cache_dir.mkdir(parents=True)
    (cache_dir / "x.pyc").write_bytes(b"\x00")

    daemon = _load_run_daemon()
    cleaned, real = daemon._clean_runtime_before_sync("T999", cwd=str(tmp_path))

    assert any("runtime.log" in c for c in cleaned)
    assert any("__pycache__" in c for c in cleaned)
    assert "tools/module.py" in real
    assert code_file.read_text() == "LOCAL CHANGE\n"


# ── 2. _sync_ticket_branch wires the hygiene step ────────────────────────────

def test_sync_ticket_branch_calls_pre_sync_hygiene():
    """``_sync_ticket_branch`` must always run the hygiene step before pull."""
    daemon = _load_run_daemon()

    calls: list[tuple] = []

    def fake_clean(ticket_id, cwd=None):
        calls.append(("clean", ticket_id, cwd))
        return [], []

    def fake_subprocess_run(args, **kwargs):
        calls.append(("run", tuple(args)))
        result = MagicMock()
        result.returncode = 0
        result.stdout = ""
        result.stderr = ""
        return result

    with patch.object(daemon, "_clean_runtime_before_sync", side_effect=fake_clean), \
         patch.object(daemon, "subprocess") as sp_mod:
        sp_mod.run.side_effect = fake_subprocess_run
        daemon._sync_ticket_branch("T999", "ticket/T999-work", cwd="/tmp/x")

    # Hygiene must be called before the git pull --rebase
    assert calls[0] == ("clean", "T999", "/tmp/x")
    pull_call = next(c for c in calls if c[0] == "run" and "pull" in c[1])
    assert "--rebase" in pull_call[1]


# ── 3. PYTHONDONTWRITEBYTECODE propagation ───────────────────────────────────

def test_no_bytecode_env_forces_pythondontwritebytecode():
    daemon = _load_run_daemon()
    env = daemon._no_bytecode_env()
    assert env["PYTHONDONTWRITEBYTECODE"] == "1"
    # Make sure existing env is not lost
    assert "PATH" in env


def test_no_bytecode_env_accepts_extra_keys():
    daemon = _load_run_daemon()
    env = daemon._no_bytecode_env({"FOO": "bar"})
    assert env["PYTHONDONTWRITEBYTECODE"] == "1"
    assert env["FOO"] == "bar"


def test_run_daemon_module_sets_dont_write_bytecode_at_import():
    """Importing run_daemon must immediately set the environment flag."""
    daemon = _load_run_daemon()
    assert os.environ.get("PYTHONDONTWRITEBYTECODE") == "1"
    # sys.dont_write_bytecode is set in the *spawned subprocess* context, not
    # necessarily here when re-loading via importlib in the same process. The
    # contract we care about is that the env var is set, which subprocesses
    # inherit.
    _ = daemon  # silence linter


def test_run_ticket_module_sets_dont_write_bytecode_at_import():
    spec = importlib.util.spec_from_file_location(
        "_test_run_ticket", TOOLS_DIR / "run_ticket.py"
    )
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    assert os.environ.get("PYTHONDONTWRITEBYTECODE") == "1"


def test_run_step_module_sets_dont_write_bytecode_at_import():
    spec = importlib.util.spec_from_file_location(
        "_test_run_step", TOOLS_DIR / "run_step.py"
    )
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    assert os.environ.get("PYTHONDONTWRITEBYTECODE") == "1"


def test_run_ticket_run_command_passes_env_with_no_bytecode():
    """``run_ticket.run_command`` must enrich the subprocess env."""
    spec = importlib.util.spec_from_file_location(
        "_test_run_ticket_env", TOOLS_DIR / "run_ticket.py"
    )
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]

    captured_env: dict = {}

    def fake_run(args, **kwargs):
        captured_env.update(kwargs.get("env") or {})
        r = MagicMock()
        r.stdout = ""
        r.stderr = ""
        r.returncode = 0
        return r

    with patch.object(mod.subprocess, "run", side_effect=fake_run):
        mod.run_command(["echo", "hi"])
    assert captured_env.get("PYTHONDONTWRITEBYTECODE") == "1"


def test_run_step_execute_external_command_passes_env_with_no_bytecode():
    spec = importlib.util.spec_from_file_location(
        "_test_run_step_env", TOOLS_DIR / "run_step.py"
    )
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]

    captured_env: dict = {}

    def fake_run(args, **kwargs):
        captured_env.update(kwargs.get("env") or {})
        r = MagicMock()
        r.stdout = ""
        r.stderr = ""
        r.returncode = 0
        return r

    with patch.object(mod.subprocess, "run", side_effect=fake_run):
        mod.execute_external_command("echo hi", "prompt")
    assert captured_env.get("PYTHONDONTWRITEBYTECODE") == "1"


def test_daemon_manager_spawn_propagates_no_bytecode_env(tmp_path: Path):
    """control-api's daemon spawn must include PYTHONDONTWRITEBYTECODE=1."""
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from services.control_api.services import daemon_manager  # type: ignore

    captured: dict = {}

    class FakeProc:
        pid = 12345

    def fake_popen(args, **kwargs):
        captured.update(kwargs)
        return FakeProc()

    # Stub the preflight to pass so this test only checks env propagation.
    facts = {
        "project_root": str(tmp_path),
        "cwd": str(tmp_path),
        "runs_dir": str(daemon_manager.resolve_runs_dir(tmp_path)),
        "worktrees_dir": "/wt",
        "logs_dir": str(daemon_manager.resolve_logs_dir(tmp_path)),
        "runtime_root": "<unset>",
        "python": sys.executable,
        "git_path": "/usr/bin/git",
        "gh_path": "/usr/bin/gh",
    }
    with patch.object(daemon_manager, "get_status") as gs, \
         patch.object(daemon_manager, "check_environment", return_value=(True, [], facts)), \
         patch.object(daemon_manager.subprocess, "Popen", side_effect=fake_popen), \
         patch.object(daemon_manager, "_write_pid_file"):
        status_mock = MagicMock()
        status_mock.running = False
        gs.return_value = status_mock
        daemon_manager.start(tmp_path, "claude")

    env = captured.get("env") or {}
    assert env.get("PYTHONDONTWRITEBYTECODE") == "1"
