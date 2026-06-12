"""Tests for services/control_api/services/git_root.py."""

from pathlib import Path

import pytest

from services.control_api.services.git_root import resolve_git_root


def test_normal_clone_returns_same_path(tmp_path):
    (tmp_path / ".git").mkdir()
    assert resolve_git_root(tmp_path) == tmp_path


def test_non_git_path_returns_same_path(tmp_path):
    assert resolve_git_root(tmp_path) == tmp_path


def test_worktree_returns_main_clone_root(tmp_path):
    # Build a minimal git worktree layout.
    main_clone = tmp_path / "main"
    main_clone.mkdir()
    main_git_dir = main_clone / ".git"
    main_git_dir.mkdir()

    # Simulate the worktrees/<name> gitdir inside the main .git.
    worktree_gitdir = main_git_dir / "worktrees" / "T186"
    worktree_gitdir.mkdir(parents=True)

    # commondir points back to the main .git dir (relative from the worktree gitdir).
    (worktree_gitdir / "commondir").write_text("../..\n", encoding="utf-8")

    # The actual worktree directory with a .git *file*.
    worktree_path = tmp_path / "worktrees" / "T186"
    worktree_path.mkdir(parents=True)
    (worktree_path / ".git").write_text(
        f"gitdir: {worktree_gitdir}\n", encoding="utf-8"
    )

    result = resolve_git_root(worktree_path)
    assert result == main_clone


def test_malformed_git_file_returns_same_path(tmp_path):
    (tmp_path / ".git").write_text("not a gitdir line\n", encoding="utf-8")
    assert resolve_git_root(tmp_path) == tmp_path


def test_missing_commondir_returns_same_path(tmp_path):
    main_clone = tmp_path / "main"
    main_clone.mkdir()
    (main_clone / ".git").mkdir()

    worktree_gitdir = main_clone / ".git" / "worktrees" / "T186"
    worktree_gitdir.mkdir(parents=True)
    # commondir file intentionally absent

    worktree_path = tmp_path / "worktrees" / "T186"
    worktree_path.mkdir(parents=True)
    (worktree_path / ".git").write_text(
        f"gitdir: {worktree_gitdir}\n", encoding="utf-8"
    )

    assert resolve_git_root(worktree_path) == worktree_path
