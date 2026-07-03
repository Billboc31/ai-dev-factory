"""Shared rules for when a ticket may start or retry conflict resolution."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

RETRY_STATE_FILENAME = "retry-state.json"

# Max daemon auto-launches of run_conflict_resolver before requiring a human.
MAX_CONFLICT_RESOLVER_AUTO_RUNS = int(
    os.environ.get("CONFLICT_RESOLVER_MAX_AUTO_RUNS", "3"),
)

_CONFLICT_RETRY_RUNS_KEY = "conflict_resolution_runs"
_CONFLICT_RETRY_STOPPED_KEY = "conflict_resolution_auto_stopped"
_CONFLICT_RETRY_STOP_REASON_KEY = "conflict_resolution_stop_reason"

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


def conflict_resolution_auto_runs(retry_state: dict) -> int:
    """Number of daemon auto-launches already recorded for this conflict episode."""
    try:
        return max(0, int(retry_state.get(_CONFLICT_RETRY_RUNS_KEY) or 0))
    except (TypeError, ValueError):
        return 0


def conflict_resolution_auto_retries_exhausted(retry_state: dict) -> bool:
    """True when auto-launch budget is spent or explicitly stopped."""
    if retry_state.get(_CONFLICT_RETRY_STOPPED_KEY):
        return True
    return conflict_resolution_auto_runs(retry_state) >= MAX_CONFLICT_RESOLVER_AUTO_RUNS


def clear_conflict_resolution_retry(retry_state: dict) -> dict:
    """Drop conflict auto-retry counters while preserving other retry-state keys."""
    updated = dict(retry_state)
    for key in (
        _CONFLICT_RETRY_RUNS_KEY,
        _CONFLICT_RETRY_STOPPED_KEY,
        _CONFLICT_RETRY_STOP_REASON_KEY,
    ):
        updated.pop(key, None)
    return updated


def mark_conflict_resolution_auto_exhausted(retry_state: dict, reason: str) -> dict:
    """Mark the conflict episode as requiring human intervention."""
    updated = dict(retry_state)
    updated[_CONFLICT_RETRY_STOPPED_KEY] = True
    updated[_CONFLICT_RETRY_STOP_REASON_KEY] = reason
    return updated


def record_conflict_resolution_auto_run(retry_state: dict) -> tuple[dict, int]:
    """Increment auto-run counter; return (updated_state, run_number)."""
    runs = conflict_resolution_auto_runs(retry_state) + 1
    updated = clear_conflict_resolution_retry(retry_state)
    updated[_CONFLICT_RETRY_RUNS_KEY] = runs
    return updated, runs


def _load_retry_state_file(run_dir: Path) -> dict:
    path = run_dir / RETRY_STATE_FILENAME
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_retry_state_file(run_dir: Path, state: dict) -> None:
    path = run_dir / RETRY_STATE_FILENAME
    if not state:
        try:
            path.unlink()
        except OSError:
            pass
        return
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, indent=2), encoding="utf-8")
    tmp.replace(path)


def reset_conflict_resolution_auto_retry(run_dir: Path) -> None:
    """Clear conflict auto-retry counters (new episode or human-triggered retry)."""
    state = _load_retry_state_file(run_dir)
    if not state:
        return
    updated = clear_conflict_resolution_retry(state)
    _save_retry_state_file(run_dir, updated)
