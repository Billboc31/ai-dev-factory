#!/usr/bin/env python3
"""Atomic runtime checkpoint primitive for ai-dev-factory.

All runtime transitions (planner, coder, reviewer, tester, etc.) must go through
checkpoint_transition() to guarantee:
  1. resolve cwd / worktree
  2. git add runtime artifacts
  3. commit checkpoint
  4. push ticket branch
  5. verify clean tree
  6. fail loudly if persistence failed
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path


WORKERS_REGISTRY_FILENAME = "workers.json"

# Paths eligible for staging with include_code=True — mirrors COMMIT_SCOPE in run_ticket.py
COMMIT_SCOPE: tuple[str, ...] = (
    "tools/",
    "tests/",
    "prompts/",
    "tickets/",
    "docs/",
    "ai/",
    "services/",
    "runs/",
    "apps/",
    "README.md",
    ".gitignore",
    "package.json",
    "package-lock.json",
)


class CheckpointError(Exception):
    """Raised when commit or push fails during checkpoint_transition."""


class DirtyTreeError(Exception):
    """Raised when the working tree is not clean after a checkpoint_transition.

    The message always contains 'DIRTY_RUNTIME_CHECKPOINT' so callers and logs
    can grep for this sentinel to detect persistence failures.
    """


def resolve_ticket_cwd(ticket_id: str, runs_dir: Path | None = None) -> str | None:
    """Return the cwd for git operations for this ticket, or None for current dir.

    Reads workers.json to find a registered worktree path for the ticket.
    Falls back to None when no worktree is registered or the path does not exist.
    """
    if runs_dir is None:
        runs_dir = Path("runs")
    registry_path = runs_dir / WORKERS_REGISTRY_FILENAME
    if not registry_path.exists():
        return None
    try:
        workers = json.loads(registry_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None
    worker = workers.get(ticket_id)
    if not worker:
        return None
    wt = worker.get("worktree_path")
    if wt and Path(wt).exists():
        return str(wt)
    return None


def collect_runtime_artifacts(ticket_id: str, cwd: str | None = None) -> list[str]:
    """Return relative paths of all files under runs/{ticket_id}/.

    Paths are relative to cwd (or current directory when cwd is None).
    """
    base = Path(cwd) if cwd else Path(".")
    run_dir = base / "runs" / ticket_id
    if not run_dir.exists():
        return []
    return sorted(
        str(p.relative_to(base))
        for p in run_dir.rglob("*")
        if p.is_file()
    )


def _run_git(args: list[str], cwd: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        text=True,
        capture_output=True,
        check=False,
        cwd=cwd,
    )


def verify_clean_tree(ticket_id: str, cwd: str | None = None) -> None:
    """Assert the working tree is clean. Raises DirtyTreeError if dirty.

    The error message embeds DIRTY_RUNTIME_CHECKPOINT so upstream code and
    grep-based monitoring can identify persistence failures.
    """
    result = _run_git(["status", "--porcelain"], cwd=cwd)
    if result.returncode != 0:
        raise DirtyTreeError(
            f"{ticket_id}: DIRTY_RUNTIME_CHECKPOINT — git status failed, cannot verify clean tree"
        )
    dirty = result.stdout.strip()
    if dirty:
        files = [line[3:] for line in dirty.splitlines() if len(line) >= 4]
        raise DirtyTreeError(
            f"{ticket_id}: DIRTY_RUNTIME_CHECKPOINT — working tree not clean after checkpoint: "
            + ", ".join(files)
        )


def checkpoint_transition(
    ticket_id: str,
    message: str,
    push: bool = True,
    include_code: bool = False,
    cwd: str | None = None,
    run_dir: str | None = None,
) -> None:
    """Atomic checkpoint: add runtime artifacts → commit → (push) → verify clean tree.

    Arguments:
        ticket_id:    Ticket identifier (e.g. "T042").
        message:      Git commit message.
        push:         Whether to push after committing (default True).
        include_code: Also stage COMMIT_SCOPE paths alongside runs/ artifacts.
        cwd:          Working directory for git commands. None = current directory.
        run_dir:      Base staging path. Defaults to "runs/{ticket_id}/".
                      Pass "runs/" to stage the whole runs directory (e.g. for intake).

    Raises:
        CheckpointError: if git add, commit, or push fails.
        DirtyTreeError:  if the tree is not clean after the operation.
    """
    # Safety: never commit on main
    branch_result = _run_git(["rev-parse", "--abbrev-ref", "HEAD"], cwd=cwd)
    if branch_result.returncode == 0 and branch_result.stdout.strip() == "main":
        raise CheckpointError(
            f"{ticket_id}: refused — cannot checkpoint on branch 'main'"
        )

    # Determine staging paths
    base_run_dir = run_dir if run_dir is not None else f"runs/{ticket_id}/"
    if include_code:
        requested = [base_run_dir] + list(COMMIT_SCOPE)
    else:
        requested = [base_run_dir]

    # Filter to paths that actually exist
    if cwd:
        stage_paths = [p for p in requested if (Path(cwd) / p).exists()]
    else:
        stage_paths = [p for p in requested if Path(p).exists()]

    if not stage_paths:
        verify_clean_tree(ticket_id, cwd=cwd)
        return

    # git add -f (handles gitignored runtime artifacts)
    for path in stage_paths:
        add_result = _run_git(["add", "-f", path], cwd=cwd)
        if add_result.returncode != 0:
            raise CheckpointError(
                f"{ticket_id}: git add failed for {path!r}: {add_result.stderr.strip()}"
            )

    # Check whether anything was actually staged
    staged_result = _run_git(["diff", "--cached", "--name-only"], cwd=cwd)
    if staged_result.returncode == 0 and not staged_result.stdout.strip():
        # Nothing new to commit — tree is already clean at this point
        verify_clean_tree(ticket_id, cwd=cwd)
        return

    # Commit
    commit_result = _run_git(["commit", "-m", message], cwd=cwd)
    if commit_result.returncode != 0:
        raise CheckpointError(
            f"{ticket_id}: git commit failed: "
            + (commit_result.stderr.strip() or commit_result.stdout.strip())
        )

    # Push
    if push:
        push_result = _run_git(["push", "-u", "origin", "HEAD"], cwd=cwd)
        if push_result.returncode != 0:
            raise CheckpointError(
                f"{ticket_id}: git push failed: {push_result.stderr.strip()}"
            )

    # Verify clean tree after all operations
    verify_clean_tree(ticket_id, cwd=cwd)
