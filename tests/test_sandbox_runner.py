"""Tests for sandbox runner: worktree creation, success, failure, logs, lock contention."""

from __future__ import annotations

import subprocess as _subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def _make_git_project(tmp_path: Path) -> Path:
    proj = tmp_path / "myproject"
    proj.mkdir()
    _subprocess.run(["git", "init", str(proj)], check=True, capture_output=True)
    _subprocess.run(["git", "-C", str(proj), "config", "user.email", "test@test.com"], check=True, capture_output=True)
    _subprocess.run(["git", "-C", str(proj), "config", "user.name", "Test"], check=True, capture_output=True)
    (proj / "README.md").write_text("test")
    _subprocess.run(["git", "-C", str(proj), "add", "."], check=True, capture_output=True)
    _subprocess.run(["git", "-C", str(proj), "commit", "-m", "init"], check=True, capture_output=True)
    return proj


def _add_scripts(proj: Path, scripts: dict[str, str]) -> None:
    for name, content in scripts.items():
        script = proj / name
        script.write_text(f"#!/bin/bash\n{content}\n")
        script.chmod(0o755)
    _subprocess.run(["git", "-C", str(proj), "add", "."], check=True, capture_output=True)
    _subprocess.run(["git", "-C", str(proj), "commit", "-m", "add scripts"], check=True, capture_output=True)


def _make_app(tmp_path: Path, proj: Path):
    from services.control_api.main import create_app
    return create_app(project_root=proj, projects_root=tmp_path)


def _wait_for_terminal(client, project_id: str, timeout: float = 15.0) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = client.get(f"/projects/{project_id}/sandbox/status")
        if r.json().get("state") in ("success", "failed"):
            return r.json()
        time.sleep(0.1)
    return client.get(f"/projects/{project_id}/sandbox/status").json()


def test_sandbox_worktree_creation(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    from fastapi.testclient import TestClient

    proj = _make_git_project(tmp_path)
    app = _make_app(tmp_path, proj)
    client = TestClient(app)

    r = client.post("/projects/myproject/sandbox/start")
    assert r.status_code == 202
    assert r.json()["ok"] is True

    _wait_for_terminal(client, "myproject")

    sandbox_base = proj / ".ai-dev-factory" / "sandboxes"
    latest = (sandbox_base / "latest").read_text().strip()
    worktree_path = sandbox_base / latest / "worktree"
    assert worktree_path.exists()


def test_sandbox_full_success(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    from fastapi.testclient import TestClient

    proj = _make_git_project(tmp_path)
    _add_scripts(proj, {
        "bootstrap.sh": "exit 0",
        "build.sh": "exit 0",
        "start.sh": "exit 0",
        "healthcheck.sh": "exit 0",
    })
    app = _make_app(tmp_path, proj)
    client = TestClient(app)

    r = client.post("/projects/myproject/sandbox/start")
    assert r.status_code == 202

    status = _wait_for_terminal(client, "myproject")
    assert status["state"] == "success"
    success_steps = [s for s in status["steps"] if s["status"] == "success"]
    assert len(success_steps) == 4


def test_sandbox_healthcheck_failure(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    from fastapi.testclient import TestClient

    proj = _make_git_project(tmp_path)
    _add_scripts(proj, {
        "bootstrap.sh": "exit 0",
        "healthcheck.sh": "exit 1",
    })
    app = _make_app(tmp_path, proj)
    client = TestClient(app)

    client.post("/projects/myproject/sandbox/start")
    status = _wait_for_terminal(client, "myproject")

    assert status["state"] == "failed"
    assert status["last_step"] == "healthcheck.sh"
    assert "healthcheck.sh" in (status.get("error") or "")
    failed_steps = [s for s in status["steps"] if s["status"] == "failed"]
    assert len(failed_steps) == 1
    assert failed_steps[0]["name"] == "healthcheck.sh"


def test_sandbox_mid_pipeline_failure(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    from fastapi.testclient import TestClient

    proj = _make_git_project(tmp_path)
    _add_scripts(proj, {
        "bootstrap.sh": "exit 0",
        "build.sh": "exit 1",
        "start.sh": "exit 0",
        "healthcheck.sh": "exit 0",
    })
    app = _make_app(tmp_path, proj)
    client = TestClient(app)

    client.post("/projects/myproject/sandbox/start")
    status = _wait_for_terminal(client, "myproject")

    assert status["state"] == "failed"
    steps_by_name = {s["name"]: s for s in status["steps"]}
    assert steps_by_name["bootstrap.sh"]["status"] == "success"
    assert steps_by_name["build.sh"]["status"] == "failed"
    assert "start.sh" not in steps_by_name
    assert "healthcheck.sh" not in steps_by_name


def test_sandbox_log_capture(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    from fastapi.testclient import TestClient

    proj = _make_git_project(tmp_path)
    _add_scripts(proj, {"bootstrap.sh": "echo hello_from_bootstrap"})
    app = _make_app(tmp_path, proj)
    client = TestClient(app)

    client.post("/projects/myproject/sandbox/start")
    _wait_for_terminal(client, "myproject")

    r = client.get("/projects/myproject/sandbox/logs")
    assert r.status_code == 200
    lines = r.json()["lines"]
    assert len(lines) > 0
    assert any("hello_from_bootstrap" in line for line in lines)


def test_sandbox_lock_contention(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    from fastapi.testclient import TestClient
    from services.control_api.services.sandbox_runner import _get_lock

    proj = _make_git_project(tmp_path)
    app = _make_app(tmp_path, proj)
    client = TestClient(app)

    lock = _get_lock("myproject")
    lock.acquire()
    try:
        r = client.post("/projects/myproject/sandbox/start")
        assert r.status_code == 409
    finally:
        lock.release()


# ── Worktree robustness ───────────────────────────────────────────────────────
#
# Each test below pins one failure mode that previously left the runner stuck
# in ``state=running, last_step=worktree``. They all assert two invariants:
#   1. the runner transitions to ``state=failed`` (never stays "running");
#   2. ``state.json`` carries ``finished_at`` and a non-empty ``error``.


import json  # noqa: E402

import pytest  # noqa: E402

from services.control_api.services import sandbox_runner  # noqa: E402


def _read_state_file(proj: Path) -> dict:
    sandbox_base = proj / ".ai-dev-factory" / "sandboxes"
    latest = (sandbox_base / "latest").read_text().strip()
    return json.loads((sandbox_base / latest / "state.json").read_text())


def _read_log_file(proj: Path) -> str:
    sandbox_base = proj / ".ai-dev-factory" / "sandboxes"
    latest = (sandbox_base / "latest").read_text().strip()
    return (sandbox_base / latest / "run.log").read_text()


def _assert_terminal_failed(status: dict) -> None:
    assert status["state"] == "failed", f"state stuck at {status['state']}"
    assert status["finished_at"] is not None, "finished_at must be set on failure"
    assert status["error"], "error must not be empty on failure"


def test_worktree_creation_writes_explicit_log_header(tmp_path, monkeypatch):
    """The new log header makes debugging trivial: it always names the
    worktree path, the timeout, and the actual git invocation."""
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    from fastapi.testclient import TestClient

    proj = _make_git_project(tmp_path)
    app = _make_app(tmp_path, proj)
    client = TestClient(app)

    client.post("/projects/myproject/sandbox/start")
    _wait_for_terminal(client, "myproject")

    log_text = _read_log_file(proj)
    assert "--- creating git worktree ---" in log_text
    assert "worktree path: " in log_text
    assert "timeout: " in log_text
    assert "git worktree add " in log_text  # the actual command line
    assert "exit=0" in log_text


def test_worktree_subprocess_timeout_fails_cleanly(tmp_path, monkeypatch):
    """If ``git worktree add`` hangs, the runner must kill it and mark
    the sandbox as failed — never leave state=running forever."""
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    from fastapi.testclient import TestClient

    proj = _make_git_project(tmp_path)

    real_popen = sandbox_runner.subprocess.Popen

    def fake_popen(cmd, *a, **kw):
        # Only intercept the actual `worktree add`; let preflight git
        # commands (e.g. `worktree prune`) run for real so we exercise
        # the full code path.
        if isinstance(cmd, list) and cmd[:3] == ["git", "worktree", "add"]:
            class _HangingProc:
                pid = 999999
                returncode = None

                def communicate(self, timeout=None):
                    raise sandbox_runner.subprocess.TimeoutExpired(cmd=cmd, timeout=timeout)

            return _HangingProc()
        return real_popen(cmd, *a, **kw)

    monkeypatch.setattr(sandbox_runner.subprocess, "Popen", fake_popen)
    # The killpg call would fail on our fake PID; swallow it.
    monkeypatch.setattr(sandbox_runner.os, "killpg", lambda *a, **kw: None)
    # Tighten timeout so the test stays fast.
    monkeypatch.setattr(sandbox_runner, "_WORKTREE_TIMEOUT_SECONDS", 1)

    app = _make_app(tmp_path, proj)
    client = TestClient(app)

    client.post("/projects/myproject/sandbox/start")
    status = _wait_for_terminal(client, "myproject", timeout=10.0)

    _assert_terminal_failed(status)
    assert "timed out" in status["error"]
    assert status["last_step"] == "worktree"

    log_text = _read_log_file(proj)
    assert "git command timed out" in log_text
    assert "worktree creation failed" in log_text


def test_worktree_nonzero_exit_is_reported_with_stderr(tmp_path, monkeypatch):
    """When ``git worktree add`` exits non-zero (e.g. branch already
    checked out elsewhere), the error message must include the actual
    stderr — not the truncated 200-char snippet of the old code."""
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    from fastapi.testclient import TestClient

    proj = _make_git_project(tmp_path)

    real_popen = sandbox_runner.subprocess.Popen

    def fake_popen(cmd, *a, **kw):
        if isinstance(cmd, list) and cmd[:3] == ["git", "worktree", "add"]:
            class _FailingProc:
                pid = 999998
                returncode = 128

                def communicate(self, timeout=None):
                    return ("", "fatal: HEAD is not a valid object name\n")

            return _FailingProc()
        return real_popen(cmd, *a, **kw)

    monkeypatch.setattr(sandbox_runner.subprocess, "Popen", fake_popen)

    app = _make_app(tmp_path, proj)
    client = TestClient(app)

    client.post("/projects/myproject/sandbox/start")
    status = _wait_for_terminal(client, "myproject")

    _assert_terminal_failed(status)
    assert "exited 128" in status["error"]
    assert "fatal: HEAD" in status["error"]

    log_text = _read_log_file(proj)
    assert "fatal: HEAD" in log_text
    assert "exit=128" in log_text


def test_preflight_git_binary_missing(tmp_path, monkeypatch):
    """If git is not in PATH the preflight check must catch it before
    we ever spawn a subprocess that could hang."""
    proj = _make_git_project(tmp_path)
    monkeypatch.setattr(sandbox_runner.shutil, "which", lambda name: None)
    log = tmp_path / "preflight.log"

    err = sandbox_runner._preflight_worktree(proj, proj / "wt", log)
    assert err is not None
    assert "git binary not found" in err


def test_preflight_project_root_missing(tmp_path):
    """Docker may map ``project_root`` to a host path that doesn't exist."""
    log = tmp_path / "preflight.log"
    ghost = tmp_path / "does-not-exist"

    err = sandbox_runner._preflight_worktree(ghost, ghost / "wt", log)
    assert err is not None
    assert "does not exist" in err


def test_preflight_project_root_not_a_git_repo(tmp_path):
    proj = tmp_path / "myproject"
    proj.mkdir()  # no .git
    log = tmp_path / "preflight.log"

    err = sandbox_runner._preflight_worktree(proj, proj / "wt", log)
    assert err is not None
    assert "not a git repository" in err


def test_preflight_removes_stale_index_lock(tmp_path):
    """``.git/index.lock`` left over by a killed git process must be
    removed; otherwise the next ``git worktree add`` would block."""
    proj = _make_git_project(tmp_path)
    lock = proj / ".git" / "index.lock"
    lock.write_text("")
    log = tmp_path / "preflight.log"

    err = sandbox_runner._preflight_worktree(proj, proj / "wt-new", log)
    assert err is None
    assert not lock.exists()
    assert "removed stale lock" in log.read_text()


def test_create_worktree_e2e_success(tmp_path):
    """Direct unit test of ``_create_worktree`` against a real git repo."""
    proj = _make_git_project(tmp_path)
    log = tmp_path / "run.log"
    wt = tmp_path / "wt"

    ok, err = sandbox_runner._create_worktree(proj, wt, log)
    assert ok is True, f"unexpected error: {err}"
    assert wt.exists()
    log_text = log.read_text()
    assert "worktree path: " in log_text
    assert "worktree created" in log_text
    assert "exit=0" in log_text


def test_worktree_stale_path_is_cleaned_before_add(tmp_path, monkeypatch):
    """A directory left over from a previous failed run must be cleared
    up by preflight so the next ``worktree add`` doesn't refuse."""
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    from fastapi.testclient import TestClient

    proj = _make_git_project(tmp_path)
    # Pre-create the sandbox dir + a stale worktree leftover (untracked
    # by git, so `worktree remove` will fail and we hit the rmtree path).
    sandbox_base = proj / ".ai-dev-factory" / "sandboxes"
    sandbox_base.mkdir(parents=True, exist_ok=True)
    # Force a deterministic sandbox_id so we know where to seed the
    # stale leftover.
    monkeypatch.setattr(sandbox_runner, "_make_sandbox_id", lambda pid: f"{pid}-STALE")
    stale = sandbox_base / "myproject-STALE" / "worktree"
    stale.mkdir(parents=True)
    (stale / "leftover.txt").write_text("from a previous failed run")

    app = _make_app(tmp_path, proj)
    client = TestClient(app)

    client.post("/projects/myproject/sandbox/start")
    status = _wait_for_terminal(client, "myproject", timeout=20.0)

    # End state: the runner must have either cleaned + succeeded OR
    # cleaned + failed for a reportable reason. Either way it must
    # NOT stay in "running" with the stale dir still in place.
    assert status["state"] in ("success", "failed")
    assert status["finished_at"] is not None
    log_text = _read_log_file(proj)
    assert "already exists" in log_text or "removed stale" in log_text


def test_worktree_unhandled_exception_finalises_state(tmp_path, monkeypatch):
    """Even a wholly unexpected error inside the runner thread must end
    with ``state=failed`` so the dashboard can recover."""
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    from fastapi.testclient import TestClient

    proj = _make_git_project(tmp_path)

    def boom(*a, **kw):
        raise RuntimeError("simulated catastrophic failure")

    monkeypatch.setattr(sandbox_runner, "_create_worktree", boom)

    app = _make_app(tmp_path, proj)
    client = TestClient(app)

    client.post("/projects/myproject/sandbox/start")
    status = _wait_for_terminal(client, "myproject")

    _assert_terminal_failed(status)
    assert "unhandled exception" in status["error"]
    assert "simulated catastrophic failure" in status["error"]


def test_state_file_never_stuck_in_running_after_failure(tmp_path, monkeypatch):
    """Belt-and-suspenders regression: directly read state.json after a
    forced failure and verify it is NOT ``running``."""
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    from fastapi.testclient import TestClient

    proj = _make_git_project(tmp_path)
    monkeypatch.setattr(sandbox_runner.shutil, "which", lambda name: None)
    app = _make_app(tmp_path, proj)
    client = TestClient(app)

    client.post("/projects/myproject/sandbox/start")
    _wait_for_terminal(client, "myproject")

    state = _read_state_file(proj)
    assert state["state"] != "running"
    assert state["state"] == "failed"


def test_run_git_uses_safe_subprocess_flags(monkeypatch, tmp_path):
    """Smoke-test the safety flags on the Popen call: stdin must be
    DEVNULL (no credential prompt blocking) and start_new_session must
    be True (so killpg can take down the whole process tree)."""
    seen_kwargs = {}

    def fake_popen(cmd, *a, **kw):
        seen_kwargs.update(kw)

        class _Done:
            pid = 1
            returncode = 0

            def communicate(self, timeout=None):
                return ("", "")

        return _Done()

    monkeypatch.setattr(sandbox_runner.subprocess, "Popen", fake_popen)
    log = tmp_path / "log.txt"
    rc, out, err = sandbox_runner._run_git(["--version"], cwd=tmp_path, log_path=log, timeout=5)
    assert rc == 0
    assert seen_kwargs.get("stdin") is sandbox_runner.subprocess.DEVNULL
    assert seen_kwargs.get("start_new_session") is True
    log_text = log.read_text()
    assert "+ git --version" in log_text
    assert f"timeout=5s" in log_text
    assert "exit=0" in log_text
