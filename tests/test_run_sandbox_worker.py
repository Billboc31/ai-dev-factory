"""Tests for the host-side sandbox-validation worker.

This file used to drive the in-container ``sandbox_runner`` via the
control-api TestClient. The worker has since moved to
``tools/agent_runner/run_sandbox.py`` (executed host-side by the
supervisor), so tests now exercise the worker module directly. The
robustness invariants from PR #120 are preserved verbatim — none of
them depended on the HTTP layer.
"""

from __future__ import annotations

import json
import subprocess as _subprocess
import sys
from pathlib import Path

import pytest

# Import the worker as a flat module — same trick the supervisor uses.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "agent_runner"))

import run_sandbox  # noqa: E402


# ── Fixtures ──────────────────────────────────────────────────────────────────


def _make_git_project(tmp_path: Path) -> Path:
    proj = tmp_path / "myproject"
    proj.mkdir()
    _subprocess.run(["git", "init", str(proj)], check=True, capture_output=True)
    _subprocess.run(
        ["git", "-C", str(proj), "config", "user.email", "test@test.com"],
        check=True, capture_output=True,
    )
    _subprocess.run(
        ["git", "-C", str(proj), "config", "user.name", "Test"],
        check=True, capture_output=True,
    )
    (proj / "README.md").write_text("test")
    _subprocess.run(["git", "-C", str(proj), "add", "."], check=True, capture_output=True)
    _subprocess.run(
        ["git", "-C", str(proj), "commit", "-m", "init"],
        check=True, capture_output=True,
    )
    return proj


def _add_scripts(proj: Path, scripts: dict[str, str]) -> None:
    for name, content in scripts.items():
        script = proj / name
        script.write_text(f"#!/bin/bash\n{content}\n")
        script.chmod(0o755)
    _subprocess.run(["git", "-C", str(proj), "add", "."], check=True, capture_output=True)
    _subprocess.run(
        ["git", "-C", str(proj), "commit", "-m", "add scripts"],
        check=True, capture_output=True,
    )


@pytest.fixture(autouse=True)
def _runtime_root(tmp_path, monkeypatch):
    """Pin the host runtime root to a tmp dir so tests are hermetic."""
    monkeypatch.setenv("AI_DEV_FACTORY_RUNTIME_ROOT", str(tmp_path / "runtime"))
    return tmp_path / "runtime"


def _read_latest_state(tmp_path: Path, project_id: str = "myproject") -> dict:
    p = tmp_path / "runtime" / "state" / f"sandbox-{project_id}.json"
    return json.loads(p.read_text())


def _read_latest_log(tmp_path: Path, project_id: str = "myproject") -> str:
    # Per-run log: find the single sandbox directory under runtime/sandboxes/
    base = tmp_path / "runtime" / "sandboxes"
    dirs = [d for d in base.iterdir() if d.is_dir() and d.name.startswith(project_id)]
    assert dirs, f"no sandbox directory found under {base}"
    return (dirs[0] / "run.log").read_text()


def _assert_terminal_failed(state: dict) -> None:
    assert state["state"] == "failed", f"state stuck at {state['state']}"
    assert state["finished_at"] is not None, "finished_at must be set on failure"
    assert state["error"], "error must not be empty on failure"


# ── Happy paths ───────────────────────────────────────────────────────────────


def test_worker_creates_worktree(tmp_path):
    proj = _make_git_project(tmp_path)
    run_sandbox._do_sandbox("myproject", proj, "myproject-T1")

    state = _read_latest_state(tmp_path)
    assert state["state"] in ("success", "failed")  # depends on scripts presence
    wt = tmp_path / "runtime" / "sandboxes" / "myproject-T1" / "worktree"
    assert wt.exists(), "worktree directory must be created"


def test_worker_full_success(tmp_path):
    proj = _make_git_project(tmp_path)
    _add_scripts(proj, {
        "bootstrap.sh": "exit 0",
        "build.sh": "exit 0",
        "start.sh": "exit 0",
        "healthcheck.sh": "exit 0",
    })
    run_sandbox._do_sandbox("myproject", proj, "myproject-OK")

    state = _read_latest_state(tmp_path)
    assert state["state"] == "success"
    success_steps = [s for s in state["steps"] if s["status"] == "success"]
    assert len(success_steps) == 4


def test_worker_healthcheck_failure(tmp_path):
    proj = _make_git_project(tmp_path)
    _add_scripts(proj, {
        "bootstrap.sh": "exit 0",
        "healthcheck.sh": "exit 1",
    })
    run_sandbox._do_sandbox("myproject", proj, "myproject-HC")

    state = _read_latest_state(tmp_path)
    assert state["state"] == "failed"
    assert state["last_step"] == "healthcheck.sh"
    assert "healthcheck.sh" in (state.get("error") or "")
    failed = [s for s in state["steps"] if s["status"] == "failed"]
    assert len(failed) == 1


def test_worker_mid_pipeline_failure_skips_later_scripts(tmp_path):
    proj = _make_git_project(tmp_path)
    _add_scripts(proj, {
        "bootstrap.sh": "exit 0",
        "build.sh": "exit 1",
        "start.sh": "exit 0",
        "healthcheck.sh": "exit 0",
    })
    run_sandbox._do_sandbox("myproject", proj, "myproject-MID")

    state = _read_latest_state(tmp_path)
    assert state["state"] == "failed"
    by_name = {s["name"]: s for s in state["steps"]}
    assert by_name["bootstrap.sh"]["status"] == "success"
    assert by_name["build.sh"]["status"] == "failed"
    assert "start.sh" not in by_name
    assert "healthcheck.sh" not in by_name


def test_worker_writes_step_output_to_log(tmp_path):
    proj = _make_git_project(tmp_path)
    _add_scripts(proj, {"bootstrap.sh": "echo hello_from_bootstrap"})
    run_sandbox._do_sandbox("myproject", proj, "myproject-LOG")

    log = _read_latest_log(tmp_path)
    assert "hello_from_bootstrap" in log
    assert "--- bootstrap.sh ---" in log


def test_worker_latest_state_mirrors_per_run_state(tmp_path):
    """The supervisor reads ``state/sandbox-{project_id}.json`` while the
    per-run history lives under ``sandboxes/{id}/state.json``. Both must
    carry the same content after the worker finishes."""
    proj = _make_git_project(tmp_path)
    run_sandbox._do_sandbox("myproject", proj, "myproject-MIRROR")

    latest = json.loads(
        (tmp_path / "runtime" / "state" / "sandbox-myproject.json").read_text()
    )
    per_run = json.loads(
        (tmp_path / "runtime" / "sandboxes" / "myproject-MIRROR" / "state.json").read_text()
    )
    assert latest == per_run


# ── Worktree robustness (preserved from PR #120) ──────────────────────────────


def test_worktree_log_header_contains_explicit_diagnostics(tmp_path):
    proj = _make_git_project(tmp_path)
    run_sandbox._do_sandbox("myproject", proj, "myproject-HDR")

    log = _read_latest_log(tmp_path)
    assert "--- creating git worktree ---" in log
    assert "worktree path: " in log
    assert "timeout: " in log
    assert "git worktree add " in log
    assert "exit=0" in log


def test_worktree_subprocess_timeout_marks_failed(tmp_path, monkeypatch):
    """If ``git worktree add`` hangs, the worker must kill it and mark
    the sandbox as failed — never leave state=running forever."""
    proj = _make_git_project(tmp_path)

    real_popen = run_sandbox.subprocess.Popen

    def fake_popen(cmd, *a, **kw):
        if isinstance(cmd, list) and cmd[:3] == ["git", "worktree", "add"]:
            class _Hanging:
                pid = 999999
                returncode = None

                def communicate(self, timeout=None):
                    raise run_sandbox.subprocess.TimeoutExpired(
                        cmd=cmd, timeout=timeout,
                    )
            return _Hanging()
        return real_popen(cmd, *a, **kw)

    monkeypatch.setattr(run_sandbox.subprocess, "Popen", fake_popen)
    monkeypatch.setattr(run_sandbox.os, "killpg", lambda *a, **kw: None)
    monkeypatch.setattr(run_sandbox, "_WORKTREE_TIMEOUT_SECONDS", 1)

    run_sandbox._do_sandbox("myproject", proj, "myproject-TO")

    state = _read_latest_state(tmp_path)
    _assert_terminal_failed(state)
    assert "timed out" in state["error"]
    assert state["last_step"] == "worktree"

    log = _read_latest_log(tmp_path)
    assert "git command timed out" in log
    assert "worktree creation failed" in log


def test_worktree_nonzero_exit_preserves_stderr(tmp_path, monkeypatch):
    proj = _make_git_project(tmp_path)
    real_popen = run_sandbox.subprocess.Popen

    def fake_popen(cmd, *a, **kw):
        if isinstance(cmd, list) and cmd[:3] == ["git", "worktree", "add"]:
            class _Failing:
                pid = 999998
                returncode = 128

                def communicate(self, timeout=None):
                    return ("", "fatal: HEAD is not a valid object name\n")
            return _Failing()
        return real_popen(cmd, *a, **kw)

    monkeypatch.setattr(run_sandbox.subprocess, "Popen", fake_popen)
    run_sandbox._do_sandbox("myproject", proj, "myproject-ERR")

    state = _read_latest_state(tmp_path)
    _assert_terminal_failed(state)
    assert "exited 128" in state["error"]
    assert "fatal: HEAD" in state["error"]

    log = _read_latest_log(tmp_path)
    assert "fatal: HEAD" in log
    assert "exit=128" in log


def test_preflight_git_binary_missing(tmp_path, monkeypatch):
    proj = _make_git_project(tmp_path)
    monkeypatch.setattr(run_sandbox.shutil, "which", lambda name: None)
    log = tmp_path / "preflight.log"

    err = run_sandbox._preflight_worktree(proj, proj / "wt", log)
    assert err is not None
    assert "git binary not found" in err


def test_preflight_project_root_missing(tmp_path):
    log = tmp_path / "preflight.log"
    ghost = tmp_path / "does-not-exist"

    err = run_sandbox._preflight_worktree(ghost, ghost / "wt", log)
    assert err is not None
    assert "does not exist" in err


def test_preflight_project_root_not_a_git_repo(tmp_path):
    proj = tmp_path / "not-a-repo"
    proj.mkdir()
    log = tmp_path / "preflight.log"

    err = run_sandbox._preflight_worktree(proj, proj / "wt", log)
    assert err is not None
    assert "not a git repository" in err


def test_preflight_removes_stale_index_lock(tmp_path):
    proj = _make_git_project(tmp_path)
    lock = proj / ".git" / "index.lock"
    lock.write_text("")
    log = tmp_path / "preflight.log"

    err = run_sandbox._preflight_worktree(proj, proj / "wt-new", log)
    assert err is None
    assert not lock.exists()
    assert "removed stale lock" in log.read_text()


def test_create_worktree_happy_path(tmp_path):
    proj = _make_git_project(tmp_path)
    log = tmp_path / "run.log"
    wt = tmp_path / "wt"

    ok, err = run_sandbox._create_worktree(proj, wt, log)
    assert ok is True, f"unexpected error: {err}"
    assert wt.exists()
    log_text = log.read_text()
    assert "worktree path: " in log_text
    assert "worktree created" in log_text
    assert "exit=0" in log_text


def test_unhandled_exception_inside_create_worktree_is_finalised(tmp_path, monkeypatch):
    proj = _make_git_project(tmp_path)

    def boom(*a, **kw):
        raise RuntimeError("simulated catastrophic failure")

    monkeypatch.setattr(run_sandbox, "_create_worktree", boom)
    run_sandbox._do_sandbox("myproject", proj, "myproject-BOOM")

    state = _read_latest_state(tmp_path)
    _assert_terminal_failed(state)
    assert "unhandled exception" in state["error"]
    assert "simulated catastrophic failure" in state["error"]


def test_state_never_stuck_in_running_after_failure(tmp_path, monkeypatch):
    """Belt-and-suspenders: state.json must never be left as 'running'."""
    proj = _make_git_project(tmp_path)
    monkeypatch.setattr(run_sandbox.shutil, "which", lambda name: None)

    run_sandbox._do_sandbox("myproject", proj, "myproject-NEVER-STUCK")

    state = _read_latest_state(tmp_path)
    assert state["state"] != "running"
    assert state["state"] == "failed"


def test_run_git_uses_safe_subprocess_flags(monkeypatch, tmp_path):
    """``stdin=DEVNULL`` + ``start_new_session=True`` are the two flags
    that make timeout-killing reliable. Regress against any future
    refactor that drops them."""
    seen_kwargs = {}

    def fake_popen(cmd, *a, **kw):
        seen_kwargs.update(kw)

        class _Done:
            pid = 1
            returncode = 0

            def communicate(self, timeout=None):
                return ("", "")

        return _Done()

    monkeypatch.setattr(run_sandbox.subprocess, "Popen", fake_popen)
    log = tmp_path / "log.txt"
    rc, _out, _err = run_sandbox._run_git(
        ["--version"], cwd=tmp_path, log_path=log, timeout=5
    )
    assert rc == 0
    assert seen_kwargs.get("stdin") is run_sandbox.subprocess.DEVNULL
    assert seen_kwargs.get("start_new_session") is True
    log_text = log.read_text()
    assert "+ git --version" in log_text
    assert "timeout=5s" in log_text
    assert "exit=0" in log_text


# ── CLI entry point (smoke) ───────────────────────────────────────────────────


def test_worker_cli_smoke(tmp_path):
    """``python tools/agent_runner/run_sandbox.py`` must succeed on a
    real git project — this is exactly how the supervisor invokes it."""
    proj = _make_git_project(tmp_path)
    runtime_root = tmp_path / "runtime"
    runtime_root.mkdir()
    env = {
        **__import__("os").environ,
        "AI_DEV_FACTORY_RUNTIME_ROOT": str(runtime_root),
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    script = Path(__file__).resolve().parents[1] / "tools" / "agent_runner" / "run_sandbox.py"
    result = _subprocess.run(
        [sys.executable, str(script),
         "--project-root", str(proj),
         "--project-id", "myproject"],
        capture_output=True,
        text=True,
        env=env,
        timeout=60,
    )
    # exit code may be 1 because the test project has no scripts to run —
    # the important invariant is that the state file is finalised.
    assert result.returncode in (0, 1), (
        f"unexpected rc {result.returncode}: stderr={result.stderr[:500]}"
    )
    state = json.loads(
        (runtime_root / "state" / "sandbox-myproject.json").read_text()
    )
    assert state["state"] in ("success", "failed")
    assert state["finished_at"] is not None
