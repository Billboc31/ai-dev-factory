"""Shared rules for when a ticket may start or retry conflict resolution."""

from __future__ import annotations

import subprocess
from pathlib import Path

_RESOLVABLE_STATES = frozenset({
    "CONFLICT_RESOLUTION_NEEDED",
    "CONFLICT_RESOLUTION_FAILED",
    "CONFLICT_RESOLVING",
})


def git_conflicted_files(worktree_cwd: Path) -> list[str]:
    """Return unmerged paths in the worktree, or [] when git is unavailable."""
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "--diff-filter=U"],
            cwd=str(worktree_cwd),
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return []
    if result.returncode != 0:
        return []
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def git_rebase_in_progress(worktree_cwd: Path) -> bool:
    """True when the worktree is in the middle of a rebase."""
    for subpath in ("rebase-merge", "rebase-apply"):
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--git-path", subpath],
                cwd=str(worktree_cwd),
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError:
            continue
        if result.returncode != 0:
            continue
        if Path(result.stdout.strip()).exists():
            return True
    return False


def git_has_active_conflicts(worktree_cwd: Path) -> bool:
    """True when git reports an in-progress rebase and/or unmerged paths."""
    return bool(git_conflicted_files(worktree_cwd)) or git_rebase_in_progress(worktree_cwd)


def conflict_resolution_eligible(
    state: dict,
    worktree_cwd: Path | None = None,
) -> bool:
    """Return True when conflict resolution may be started or retried."""
    current = state.get("state", "")
    if current in _RESOLVABLE_STATES:
        return True
    if worktree_cwd is not None and worktree_cwd.is_dir():
        return git_has_active_conflicts(worktree_cwd)
    return False
