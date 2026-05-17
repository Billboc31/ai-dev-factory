"""Tests that dashboard actions resolve the correct cwd/worktree.

Reproduces: commit-checkpoint: refused — current branch 'main' does not match
state branch 'ticket/TXXX-...' when IHM actions ran from project_root on main.
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, call

sys.path.insert(0, str(Path(__file__).parent.parent / "services"))

from control_api.services.subprocess_runner import (
    _resolve_action_cwd,
    approve_plan,
    checkpoint_ticket,
    push_ticket,
    approve_implementation,
    request_plan_fix,
    request_implementation_fix,
)


def _make_project(tmp_path: Path, ticket_id: str = "T001", branch: str = "ticket/T001-feat") -> Path:
    project_root = tmp_path / "repo"
    run_dir = project_root / "runs" / ticket_id
    run_dir.mkdir(parents=True)
    state = {
        "ticket_id": ticket_id,
        "state": "PLAN_REVIEW_NEEDED",
        "branch": branch,
    }
    (run_dir / "state.json").write_text(json.dumps(state), encoding="utf-8")
    return project_root


def _make_worktree(tmp_path: Path, ticket_id: str = "T001", branch: str = "ticket/T001-feat") -> Path:
    worktrees_dir = tmp_path / "worktrees"
    wt_path = worktrees_dir / ticket_id
    run_dir = wt_path / "runs" / ticket_id
    run_dir.mkdir(parents=True)
    state = {
        "ticket_id": ticket_id,
        "state": "PLAN_REVIEW_NEEDED",
        "branch": branch,
    }
    (run_dir / "state.json").write_text(json.dumps(state), encoding="utf-8")
    return worktrees_dir


# ── _resolve_action_cwd ───────────────────────────────────────────────────────

def test_resolve_cwd_returns_worktree_when_present(tmp_path):
    project_root = _make_project(tmp_path)
    worktrees_dir = _make_worktree(tmp_path)

    cwd, error = _resolve_action_cwd("T001", project_root, worktrees_dir)

    assert error is None
    assert cwd == worktrees_dir / "T001"


def test_resolve_cwd_no_worktree_wrong_branch_returns_error(tmp_path):
    project_root = _make_project(tmp_path, branch="ticket/T001-feat")

    def fake_run(args, **kwargs):
        if "rev-parse" in args:
            return MagicMock(returncode=0, stdout="main\n")
        return MagicMock(returncode=0, stdout="")

    with patch("control_api.services.subprocess_runner.subprocess.run", side_effect=fake_run):
        cwd, error = _resolve_action_cwd("T001", project_root, None)

    assert error is not None
    assert "main" in error
    assert "ticket/T001-feat" in error
    assert "does not match" in error


def test_resolve_cwd_no_worktree_correct_branch_ok(tmp_path):
    project_root = _make_project(tmp_path, branch="ticket/T001-feat")

    def fake_run(args, **kwargs):
        if "rev-parse" in args:
            return MagicMock(returncode=0, stdout="ticket/T001-feat\n")
        return MagicMock(returncode=0, stdout="")

    with patch("control_api.services.subprocess_runner.subprocess.run", side_effect=fake_run):
        cwd, error = _resolve_action_cwd("T001", project_root, None)

    assert error is None
    assert cwd == project_root


def test_resolve_cwd_no_worktree_no_state_no_error(tmp_path):
    project_root = tmp_path / "repo"
    (project_root / "runs" / "T001").mkdir(parents=True)
    # state.json absent — no branch to check

    cwd, error = _resolve_action_cwd("T001", project_root, None)

    assert error is None
    assert cwd == project_root


# ── action functions use worktree cwd ─────────────────────────────────────────

def _fake_subprocess_ok(args, **kwargs):
    return MagicMock(returncode=0, stdout="ok", stderr="")


def test_approve_plan_uses_worktree_cwd(tmp_path):
    project_root = _make_project(tmp_path)
    worktrees_dir = _make_worktree(tmp_path)
    expected_cwd = worktrees_dir / "T001"

    captured = {}

    def fake_run(args, **kwargs):
        captured["cwd"] = kwargs.get("cwd")
        return MagicMock(returncode=0, stdout="ok", stderr="")

    with patch("control_api.services.subprocess_runner.subprocess.run", side_effect=fake_run):
        result = approve_plan("T001", project_root, worktrees_dir)

    assert result.ok is True
    assert captured.get("cwd") == expected_cwd


def test_checkpoint_ticket_uses_worktree_cwd(tmp_path):
    project_root = _make_project(tmp_path)
    worktrees_dir = _make_worktree(tmp_path)
    expected_cwd = worktrees_dir / "T001"

    captured = {}

    def fake_run(args, **kwargs):
        captured["cwd"] = kwargs.get("cwd")
        return MagicMock(returncode=0, stdout="ok", stderr="")

    with patch("control_api.services.subprocess_runner.subprocess.run", side_effect=fake_run):
        result = checkpoint_ticket("T001", project_root, worktrees_dir)

    assert result.ok is True
    assert captured.get("cwd") == expected_cwd


def test_push_ticket_uses_worktree_cwd(tmp_path):
    project_root = _make_project(tmp_path)
    worktrees_dir = _make_worktree(tmp_path)
    expected_cwd = worktrees_dir / "T001"

    captured = {}

    def fake_run(args, **kwargs):
        captured["cwd"] = kwargs.get("cwd")
        return MagicMock(returncode=0, stdout="ok", stderr="")

    with patch("control_api.services.subprocess_runner.subprocess.run", side_effect=fake_run):
        result = push_ticket("T001", project_root, worktrees_dir)

    assert result.ok is True
    assert captured.get("cwd") == expected_cwd


def test_action_refuses_when_on_wrong_branch_no_worktree(tmp_path):
    """Reproduces the bug: IHM on main while state.branch is ticket branch."""
    project_root = _make_project(tmp_path, branch="ticket/T001-feat")

    def fake_run(args, **kwargs):
        if "rev-parse" in args:
            return MagicMock(returncode=0, stdout="main\n")
        return MagicMock(returncode=0, stdout="ok", stderr="")

    with patch("control_api.services.subprocess_runner.subprocess.run", side_effect=fake_run):
        result = approve_plan("T001", project_root, None)

    assert result.ok is False
    assert "does not match" in result.message
    assert "main" in result.message
    assert "ticket/T001-feat" in result.message


def test_action_refuses_gives_actionable_message(tmp_path):
    project_root = _make_project(tmp_path, branch="ticket/T001-feat")

    def fake_run(args, **kwargs):
        if "rev-parse" in args:
            return MagicMock(returncode=0, stdout="main\n")
        return MagicMock(returncode=0, stdout="ok", stderr="")

    with patch("control_api.services.subprocess_runner.subprocess.run", side_effect=fake_run):
        result = request_plan_fix("T001", project_root, None)

    assert "worktree" in result.message.lower() or "checkout" in result.message.lower()


def test_all_action_functions_pass_worktrees_dir(tmp_path):
    """Ensure every action function correctly resolves to the worktree cwd."""
    project_root = _make_project(tmp_path)
    worktrees_dir = _make_worktree(tmp_path)
    expected_cwd = worktrees_dir / "T001"

    action_fns = [
        approve_plan,
        request_plan_fix,
        approve_implementation,
        request_implementation_fix,
        checkpoint_ticket,
        push_ticket,
    ]

    for fn in action_fns:
        captured = {}

        def fake_run(args, **kwargs):
            captured["cwd"] = kwargs.get("cwd")
            return MagicMock(returncode=0, stdout="ok", stderr="")

        with patch("control_api.services.subprocess_runner.subprocess.run", side_effect=fake_run):
            result = fn("T001", project_root, worktrees_dir)

        assert result.ok is True, f"{fn.__name__} failed: {result.message}"
        assert captured.get("cwd") == expected_cwd, (
            f"{fn.__name__}: expected cwd={expected_cwd!r}, got {captured.get('cwd')!r}"
        )
