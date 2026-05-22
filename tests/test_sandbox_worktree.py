"""Tests for sandbox worktree lifecycle: create_with_worktree, mark_completed, destroy."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from services.control_api.models.sandbox import SandboxStatus
from services.control_api.services.sandbox_manager import SandboxManager, SandboxNotFoundError


def _ok_subprocess(*args, **kwargs):
    m = MagicMock()
    m.returncode = 0
    m.stdout = "ok"
    m.stderr = ""
    return m


def _fail_subprocess(*args, **kwargs):
    m = MagicMock()
    m.returncode = 1
    m.stdout = ""
    m.stderr = "fatal: worktree error"
    return m


@pytest.fixture()
def mgr(tmp_path):
    return SandboxManager(sandboxes_dir=tmp_path / "sandboxes")


# ── create_with_worktree ──────────────────────────────────────────────────────

def test_create_with_worktree_sets_worktree_path(mgr):
    with patch("services.control_api.services.sandbox_manager.subprocess.run", side_effect=_ok_subprocess):
        state = mgr.create_with_worktree("T001", "/project", branch=None, job_type="deploy")
    assert state.worktree_path is not None
    assert state.worktree_path.endswith("/worktree")


def test_create_with_worktree_sets_job_type(mgr):
    with patch("services.control_api.services.sandbox_manager.subprocess.run", side_effect=_ok_subprocess):
        state = mgr.create_with_worktree("T001", "/project", branch=None, job_type="analysis")
    assert state.job_type == "analysis"


def test_create_with_worktree_persists_state(mgr):
    with patch("services.control_api.services.sandbox_manager.subprocess.run", side_effect=_ok_subprocess):
        state = mgr.create_with_worktree("T001", "/project", branch=None, job_type="deploy")

    reloaded = mgr.status(state.id)
    assert reloaded.worktree_path == state.worktree_path
    assert reloaded.job_type == "deploy"


def test_create_with_worktree_uses_detach_when_no_branch(mgr):
    calls = []

    def capture(*args, **kwargs):
        calls.append(args[0])
        return _ok_subprocess()

    with patch("services.control_api.services.sandbox_manager.subprocess.run", side_effect=capture):
        mgr.create_with_worktree("T001", "/project", branch=None)

    worktree_calls = [c for c in calls if "worktree" in c]
    assert len(worktree_calls) == 1
    assert "--detach" in worktree_calls[0]


def test_create_with_worktree_uses_branch_when_given(mgr):
    calls = []

    def capture(*args, **kwargs):
        calls.append(args[0])
        return _ok_subprocess()

    with patch("services.control_api.services.sandbox_manager.subprocess.run", side_effect=capture):
        mgr.create_with_worktree("T001", "/project", branch="my-branch")

    worktree_calls = [c for c in calls if "worktree" in c]
    assert len(worktree_calls) == 1
    assert "my-branch" in worktree_calls[0]
    assert "--detach" not in worktree_calls[0]


def test_create_with_worktree_destroys_sandbox_on_git_failure(mgr):
    call_count = 0

    def side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if "worktree" in args[0]:
            return _fail_subprocess()
        return _ok_subprocess()

    with patch("services.control_api.services.sandbox_manager.subprocess.run", side_effect=side_effect):
        with pytest.raises(RuntimeError, match="git worktree add failed"):
            mgr.create_with_worktree("T001", "/project", branch=None)

    assert len(mgr.list()) == 0


# ── mark_completed ────────────────────────────────────────────────────────────

def test_mark_completed_sets_completed_at(mgr):
    s = mgr.create("T001", "/project")
    assert s.completed_at is None

    updated = mgr.mark_completed(s.id)
    assert updated.completed_at is not None


def test_mark_completed_sets_status_stopped(mgr):
    with patch("services.control_api.services.sandbox_manager.subprocess.run", side_effect=_ok_subprocess):
        s = mgr.start(mgr.create("T001", "/project").id)
    assert s.status == SandboxStatus.running

    updated = mgr.mark_completed(s.id)
    assert updated.status == SandboxStatus.stopped


def test_mark_completed_persists_to_disk(mgr):
    s = mgr.create("T001", "/project")
    mgr.mark_completed(s.id)

    reloaded = mgr.status(s.id)
    assert reloaded.completed_at is not None
    assert reloaded.status == SandboxStatus.stopped


# ── destroy removes worktree ──────────────────────────────────────────────────

def test_destroy_calls_git_worktree_remove_when_worktree_set(mgr):
    worktree_path = str(mgr.sandboxes_dir / "fakeid" / "worktree")
    calls = []

    def capture(*args, **kwargs):
        calls.append(args[0])
        return _ok_subprocess()

    with patch("services.control_api.services.sandbox_manager.subprocess.run", side_effect=capture):
        state = mgr.create_with_worktree("T001", "/project", branch=None, job_type="deploy")
        mgr.destroy(state.id)

    worktree_remove_calls = [c for c in calls if "worktree" in c and "remove" in c]
    assert len(worktree_remove_calls) == 1
    assert "--force" in worktree_remove_calls[0]
    assert state.worktree_path in worktree_remove_calls[0]


def test_destroy_without_worktree_does_not_call_git(mgr):
    calls = []

    def capture(*args, **kwargs):
        calls.append(args[0])
        return _ok_subprocess()

    with patch("services.control_api.services.sandbox_manager.subprocess.run", side_effect=capture):
        s = mgr.create("T001", "/project")
        mgr.destroy(s.id)

    worktree_calls = [c for c in calls if isinstance(c, list) and "worktree" in c]
    assert len(worktree_calls) == 0


def test_destroy_removes_sandbox_directory_including_worktree(mgr):
    with patch("services.control_api.services.sandbox_manager.subprocess.run", side_effect=_ok_subprocess):
        state = mgr.create_with_worktree("T001", "/project", branch=None, job_type="deploy")
        sandbox_dir = mgr.sandboxes_dir / state.id
        assert sandbox_dir.exists()
        mgr.destroy(state.id)
        assert not sandbox_dir.exists()
