"""Resolve the main working tree root from any path inside a git repo or worktree."""

from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger("control-api")


def resolve_git_root(path: Path) -> Path:
    """Return the main working tree root for the git repo containing *path*.

    Handles three cases:
    - Normal clone: ``{path}/.git`` is a directory → returns *path*.
    - Git worktree: ``{path}/.git`` is a file containing ``gitdir: ...`` → follows
      the chain (gitdir → commondir → main worktree) and returns the main root.
    - Non-git path or any resolution error → returns *path* unchanged.
    """
    git_entry = path / ".git"

    if not git_entry.exists():
        return path

    if git_entry.is_dir():
        return path

    # .git is a file — this is a git worktree.
    try:
        git_file_content = git_entry.read_text(encoding="utf-8").strip()
        if not git_file_content.startswith("gitdir:"):
            return path

        gitdir = Path(git_file_content[len("gitdir:"):].strip())
        if not gitdir.is_absolute():
            gitdir = (path / gitdir).resolve()

        # commondir points to the .git dir of the main clone.
        commondir_file = gitdir / "commondir"
        if not commondir_file.exists():
            return path

        commondir_ref = commondir_file.read_text(encoding="utf-8").strip()
        commondir = Path(commondir_ref)
        if not commondir.is_absolute():
            commondir = (gitdir / commondir).resolve()

        # The main working tree root is the parent of the main .git dir.
        return commondir.parent
    except Exception as exc:  # noqa: BLE001
        logger.warning("git_root: resolution failed for %s: %s", path, exc)
        return path
