#!/usr/bin/env python3
"""Git worktree lifecycle helpers for per-ticket isolated execution."""

from __future__ import annotations

import subprocess
from pathlib import Path


def get_ticket_worktree_path(ticket_id: str, worktrees_dir: Path) -> Path:
    return worktrees_dir / ticket_id


def create_ticket_worktree(ticket_id: str, branch: str, worktrees_dir: Path) -> tuple[bool, str]:
    """Create a git worktree for the ticket branch. Returns (success, message)."""
    worktree_path = get_ticket_worktree_path(ticket_id, worktrees_dir)
    if worktree_path.exists():
        return True, f"worktree already exists: {worktree_path}"
    worktrees_dir.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["git", "worktree", "add", str(worktree_path), branch],
        capture_output=True, text=True, check=False,
    )
    if result.returncode == 0:
        return True, f"worktree created: {worktree_path}"
    return False, f"worktree creation failed: {result.stderr.strip()}"


def ensure_intake_worktree(worktrees_dir: Path, repo_root: "Path | None" = None) -> "tuple[bool, Path]":
    """Create or verify the _intake worktree on main. Returns (success, path)."""
    intake_path = worktrees_dir / "_intake"
    if intake_path.exists():
        return True, intake_path
    worktrees_dir.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["git", "worktree", "add", str(intake_path), "main"],
        capture_output=True, text=True, check=False,
        cwd=str(repo_root) if repo_root else None,
    )
    if result.returncode == 0:
        return True, intake_path
    return False, intake_path


def remove_ticket_worktree(ticket_id: str, worktrees_dir: Path, force: bool = False) -> tuple[bool, str]:
    """Remove the git worktree for the ticket.

    Refuses to remove if uncommitted changes exist unless force=True.
    Returns (success, message).
    """
    worktree_path = get_ticket_worktree_path(ticket_id, worktrees_dir)
    if not worktree_path.exists():
        return True, f"worktree does not exist: {worktree_path}"
    if not force:
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(worktree_path),
            capture_output=True, text=True, check=False,
        )
        if status.returncode == 0 and status.stdout.strip():
            return False, f"worktree has uncommitted changes — will not auto-remove: {worktree_path}"
    result = subprocess.run(
        ["git", "worktree", "remove"] + (["--force"] if force else []) + [str(worktree_path)],
        capture_output=True, text=True, check=False,
    )
    if result.returncode == 0:
        return True, f"worktree removed: {worktree_path}"
    return False, f"worktree removal failed: {result.stderr.strip()}"
