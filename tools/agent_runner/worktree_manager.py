#!/usr/bin/env python3
"""Git worktree lifecycle helpers for per-ticket isolated execution.

Intake is *ephemeral*: no persistent `_intake` worktree. Each new issue is
ingested by creating the ticket branch from `origin/main` and adding the ticket
worktree directly. See `create_ticket_branch_and_worktree` and the daemon's
`poll_github_issues` for the orchestration.
"""

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


def fetch_origin_main(repo_root: "Path | None" = None) -> tuple[bool, str]:
    """Fetch `origin/main` without touching any branch or working tree.

    Pure ref operation — safe to call regardless of which branch any worktree
    currently has checked out. Required before `create_ticket_branch_and_worktree`
    so the new ticket branch starts from the latest upstream main.
    """
    result = subprocess.run(
        ["git", "fetch", "origin", "main"],
        capture_output=True, text=True, check=False,
        cwd=str(repo_root) if repo_root else None,
    )
    if result.returncode == 0:
        return True, "fetched origin/main"
    return False, f"git fetch failed: {result.stderr.strip()}"


def _branch_exists(branch: str, repo_root: "Path | None" = None) -> bool:
    result = subprocess.run(
        ["git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"],
        capture_output=True, text=True, check=False,
        cwd=str(repo_root) if repo_root else None,
    )
    return result.returncode == 0


def _branch_used_by_any_worktree(branch: str, repo_root: "Path | None" = None) -> bool:
    """Return True if any existing git worktree currently has ``branch`` checked out."""
    result = subprocess.run(
        ["git", "worktree", "list", "--porcelain"],
        capture_output=True, text=True, check=False,
        cwd=str(repo_root) if repo_root else None,
    )
    if result.returncode != 0:
        return False
    target = f"refs/heads/{branch}"
    return any(
        line.strip() == f"branch {target}"
        for line in result.stdout.splitlines()
    )


def create_ticket_branch_and_worktree(
    ticket_id: str,
    branch: str,
    worktrees_dir: Path,
    repo_root: "Path | None" = None,
) -> tuple[bool, str]:
    """Provision the ticket worktree on ``branch``, creating the branch if needed.

    Behaviour:

    1. If ``worktrees/<ticket_id>`` already exists, refuse — the caller should
       reuse it or remove it explicitly.
    2. If the branch already exists locally and is **not** checked out in
       another worktree, adopt it: ``git worktree add <wt> <branch>`` without
       recreating the ref. This is the recovery path for tickets whose previous
       intake left an orphan branch behind.
    3. If the branch is currently checked out in another worktree, refuse —
       that is a real conflict needing human attention.
    4. Otherwise, create the branch from ``origin/main`` then add the worktree.
       The branch ref is rolled back if the worktree add fails so the next
       cycle can retry cleanly.

    Returns ``(success, message)``.
    """
    worktree_path = get_ticket_worktree_path(ticket_id, worktrees_dir)
    if worktree_path.exists():
        return False, f"worktree already exists: {worktree_path} — refusing"

    branch_already_exists = _branch_exists(branch, repo_root=repo_root)
    if branch_already_exists:
        if _branch_used_by_any_worktree(branch, repo_root=repo_root):
            return False, (
                f"branch {branch} is already checked out in another worktree — refusing"
            )
        worktrees_dir.mkdir(parents=True, exist_ok=True)
        wt_add = subprocess.run(
            ["git", "worktree", "add", str(worktree_path), branch],
            capture_output=True, text=True, check=False,
            cwd=str(repo_root) if repo_root else None,
        )
        if wt_add.returncode == 0:
            return True, (
                f"recovered orphan branch {branch} into worktree at {worktree_path}"
            )
        return False, f"worktree add (recovery) failed: {wt_add.stderr.strip()}"

    branch_create = subprocess.run(
        ["git", "branch", branch, "origin/main"],
        capture_output=True, text=True, check=False,
        cwd=str(repo_root) if repo_root else None,
    )
    if branch_create.returncode != 0:
        return False, f"git branch failed: {branch_create.stderr.strip()}"

    worktrees_dir.mkdir(parents=True, exist_ok=True)
    wt_add = subprocess.run(
        ["git", "worktree", "add", str(worktree_path), branch],
        capture_output=True, text=True, check=False,
        cwd=str(repo_root) if repo_root else None,
    )
    if wt_add.returncode == 0:
        return True, f"branch+worktree created at {worktree_path}"

    subprocess.run(
        ["git", "branch", "-D", branch],
        capture_output=True, text=True, check=False,
        cwd=str(repo_root) if repo_root else None,
    )
    return False, f"worktree add failed: {wt_add.stderr.strip()}"


def cleanup_failed_intake(
    ticket_id: str,
    branch: str,
    worktrees_dir: Path,
    repo_root: "Path | None" = None,
) -> list[str]:
    """Remove ticket worktree and delete branch after a failed intake.

    Idempotent and best-effort: each step is independent and errors are
    captured in the returned message list rather than raised. Use only when
    intake has failed and we want to leave no traces so the next cycle can
    retry from scratch.
    """
    messages: list[str] = []
    worktree_path = get_ticket_worktree_path(ticket_id, worktrees_dir)
    if worktree_path.exists():
        rm = subprocess.run(
            ["git", "worktree", "remove", "--force", str(worktree_path)],
            capture_output=True, text=True, check=False,
            cwd=str(repo_root) if repo_root else None,
        )
        if rm.returncode == 0:
            messages.append(f"removed worktree {worktree_path}")
        else:
            messages.append(f"worktree remove failed: {rm.stderr.strip()}")

    if _branch_exists(branch, repo_root=repo_root):
        br = subprocess.run(
            ["git", "branch", "-D", branch],
            capture_output=True, text=True, check=False,
            cwd=str(repo_root) if repo_root else None,
        )
        if br.returncode == 0:
            messages.append(f"deleted branch {branch}")
        else:
            messages.append(f"branch delete failed: {br.stderr.strip()}")

    return messages


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
