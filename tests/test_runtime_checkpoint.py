"""Tests for T109 — runtime_checkpoint atomic primitive."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, call, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "tools" / "agent_runner"))

from runtime_checkpoint import (
    CheckpointError,
    DirtyTreeError,
    checkpoint_transition,
    collect_runtime_artifacts,
    resolve_ticket_cwd,
    verify_clean_tree,
)


def _git_ok(stdout: str = "") -> MagicMock:
    return MagicMock(returncode=0, stdout=stdout, stderr="")


def _git_fail(stderr: str = "error") -> MagicMock:
    return MagicMock(returncode=1, stdout="", stderr=stderr)


# ── test 1: checkpoint success ────────────────────────────────────────────────

def test_checkpoint_transition_success(tmp_path):
    """Happy path: add → commit → push → verify all succeed."""
    run_dir = tmp_path / "runs" / "T042"
    run_dir.mkdir(parents=True)
    (run_dir / "state.json").write_text("{}", encoding="utf-8")

    calls: list[list[str]] = []

    def fake_git(args, **kwargs):
        calls.append(args)
        cmd = args[1] if len(args) > 1 else ""
        if cmd == "rev-parse" and "--abbrev-ref" in args:
            return _git_ok("ticket/T042-work")
        if cmd == "add":
            return _git_ok()
        if cmd == "diff":
            return _git_ok("runs/T042/state.json")  # something staged
        if cmd == "commit":
            return _git_ok()
        if cmd == "push":
            return _git_ok()
        if cmd == "status":
            return _git_ok("")  # clean after commit
        return _git_ok()

    with patch("runtime_checkpoint.subprocess.run", side_effect=fake_git):
        checkpoint_transition("T042", "T042: checkpoint", push=True, cwd=str(tmp_path))

    git_cmds = [a[1] for a in calls if len(a) > 1]
    assert "add" in git_cmds
    assert "commit" in git_cmds
    assert "push" in git_cmds
    assert "status" in git_cmds  # verify_clean_tree called


# ── test 2: push failure raises CheckpointError ───────────────────────────────

def test_checkpoint_transition_push_failure(tmp_path):
    """Push failure must raise CheckpointError, not be silently swallowed."""
    run_dir = tmp_path / "runs" / "T042"
    run_dir.mkdir(parents=True)
    (run_dir / "state.json").write_text("{}", encoding="utf-8")

    def fake_git(args, **kwargs):
        cmd = args[1] if len(args) > 1 else ""
        if cmd == "rev-parse":
            return _git_ok("ticket/T042-work")
        if cmd == "add":
            return _git_ok()
        if cmd == "diff":
            return _git_ok("runs/T042/state.json")
        if cmd == "commit":
            return _git_ok()
        if cmd == "push":
            return _git_fail("remote: rejected")
        return _git_ok()

    import pytest
    with patch("runtime_checkpoint.subprocess.run", side_effect=fake_git):
        with pytest.raises(CheckpointError, match="git push failed"):
            checkpoint_transition("T042", "T042: checkpoint", push=True, cwd=str(tmp_path))


# ── test 3: dirty tree after commit raises DirtyTreeError ────────────────────

def test_checkpoint_transition_dirty_tree_remaining(tmp_path):
    """If the tree is still dirty after commit+push, DirtyTreeError must be raised."""
    run_dir = tmp_path / "runs" / "T042"
    run_dir.mkdir(parents=True)
    (run_dir / "state.json").write_text("{}", encoding="utf-8")

    def fake_git(args, **kwargs):
        cmd = args[1] if len(args) > 1 else ""
        if cmd == "rev-parse":
            return _git_ok("ticket/T042-work")
        if cmd == "add":
            return _git_ok()
        if cmd == "diff":
            return _git_ok("runs/T042/state.json")
        if cmd == "commit":
            return _git_ok()
        if cmd == "push":
            return _git_ok()
        if cmd == "status":
            return _git_ok(" M runs/T042/runtime.log")  # still dirty
        return _git_ok()

    import pytest
    with patch("runtime_checkpoint.subprocess.run", side_effect=fake_git):
        with pytest.raises(DirtyTreeError, match="DIRTY_RUNTIME_CHECKPOINT"):
            checkpoint_transition("T042", "T042: checkpoint", push=True, cwd=str(tmp_path))


# ── test 4: resolve_ticket_cwd reads workers.json ────────────────────────────

def test_resolve_ticket_cwd_from_workers_json(tmp_path):
    """resolve_ticket_cwd returns the worktree path registered in workers.json."""
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    wt_path = tmp_path / "worktrees" / "T042"
    wt_path.mkdir(parents=True)
    workers = {
        "T042": {"pid": 12345, "worktree_path": str(wt_path), "branch": "ticket/T042-work"}
    }
    (runs_dir / "workers.json").write_text(json.dumps(workers), encoding="utf-8")

    result = resolve_ticket_cwd("T042", runs_dir=runs_dir)
    assert result == str(wt_path)


# ── test 5: resolve_ticket_cwd fallback when no workers.json ─────────────────

def test_resolve_ticket_cwd_fallback_when_no_workers(tmp_path):
    """resolve_ticket_cwd returns None when workers.json does not exist."""
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()

    result = resolve_ticket_cwd("T042", runs_dir=runs_dir)
    assert result is None


# ── test 6: git add -f handles gitignored files ───────────────────────────────

def test_checkpoint_transition_gitadd_force_for_ignored_files(tmp_path):
    """checkpoint_transition uses git add -f so gitignored runtime artifacts are staged."""
    run_dir = tmp_path / "runs" / "T042"
    run_dir.mkdir(parents=True)
    (run_dir / "state.json").write_text("{}", encoding="utf-8")

    add_calls: list[list[str]] = []

    def fake_git(args, **kwargs):
        cmd = args[1] if len(args) > 1 else ""
        if cmd == "rev-parse":
            return _git_ok("ticket/T042-work")
        if cmd == "add":
            add_calls.append(args)
            return _git_ok()
        if cmd == "diff":
            return _git_ok("runs/T042/state.json")
        if cmd == "commit":
            return _git_ok()
        if cmd == "push":
            return _git_ok()
        if cmd == "status":
            return _git_ok("")
        return _git_ok()

    with patch("runtime_checkpoint.subprocess.run", side_effect=fake_git):
        checkpoint_transition("T042", "T042: checkpoint", push=True, cwd=str(tmp_path))

    assert add_calls, "git add must be called"
    for add_call in add_calls:
        assert "-f" in add_call, f"git add must use -f flag, got: {add_call}"


# ── test 7: concurrent ticket isolation ───────────────────────────────────────

def test_checkpoint_transition_concurrent_isolation(tmp_path):
    """Two concurrent tickets must not interfere — each stages only its own run_dir."""
    for tid in ("T001", "T002"):
        run_dir = tmp_path / "runs" / tid
        run_dir.mkdir(parents=True)
        (run_dir / "state.json").write_text("{}", encoding="utf-8")

    staged_paths: dict[str, list[str]] = {"T001": [], "T002": []}

    def make_fake_git(ticket_id: str):
        def fake_git(args, **kwargs):
            cmd = args[1] if len(args) > 1 else ""
            if cmd == "rev-parse":
                return _git_ok(f"ticket/{ticket_id}-work")
            if cmd == "add":
                staged_paths[ticket_id].extend(a for a in args[2:] if not a.startswith("-"))
                return _git_ok()
            if cmd == "diff":
                return _git_ok(f"runs/{ticket_id}/state.json")
            if cmd == "commit":
                return _git_ok()
            if cmd == "push":
                return _git_ok()
            if cmd == "status":
                return _git_ok("")
            return _git_ok()
        return fake_git

    with patch("runtime_checkpoint.subprocess.run", side_effect=make_fake_git("T001")):
        checkpoint_transition("T001", "T001: checkpoint", push=False, cwd=str(tmp_path))

    with patch("runtime_checkpoint.subprocess.run", side_effect=make_fake_git("T002")):
        checkpoint_transition("T002", "T002: checkpoint", push=False, cwd=str(tmp_path))

    # T001 must only have staged paths containing T001
    for path in staged_paths["T001"]:
        assert "T002" not in path, f"T001 staged T002 path: {path}"

    # T002 must only have staged paths containing T002
    for path in staged_paths["T002"]:
        assert "T001" not in path, f"T002 staged T001 path: {path}"
