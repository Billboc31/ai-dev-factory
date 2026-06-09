"""Resolve the correct run_dir and cwd for a ticket — worktree-aware."""

from __future__ import annotations

import json
import os
from pathlib import Path

_WORKERS_JSON = "workers.json"


def resolve_runs_dir(project_root: Path, project_id: str | None = None) -> Path:
    """Return the runs/ directory.

    When *project_id* is given, returns the project-specific path under
    ``{RUNTIME_ROOT}/projects/{project_id}/runs``.  Otherwise falls back to the
    global ``{RUNTIME_ROOT}/runs`` or ``project_root/runs``.
    """
    runtime_root = os.environ.get("AI_DEV_FACTORY_RUNTIME_ROOT")
    if project_id and runtime_root:
        return Path(runtime_root) / "projects" / project_id / "runs"
    if runtime_root:
        return Path(runtime_root) / "runs"
    return project_root / "runs"


def resolve_worktrees_dir(project_root: Path, project_id: str | None = None) -> Path:
    """Return the worktrees/ directory.

    When *project_id* is given, returns the project-specific path under
    ``{RUNTIME_ROOT}/projects/{project_id}/worktrees``.
    """
    runtime_root = os.environ.get("AI_DEV_FACTORY_RUNTIME_ROOT")
    if project_id and runtime_root:
        return Path(runtime_root) / "projects" / project_id / "worktrees"
    if runtime_root:
        return Path(runtime_root) / "worktrees"
    return project_root.parent / (project_root.name + "-worktrees")


def resolve_state_dir(project_root: Path, project_id: str | None = None) -> Path:
    """Return the state/ directory.

    When *project_id* is given, returns the project-specific path under
    ``{RUNTIME_ROOT}/projects/{project_id}/state``.
    """
    runtime_root = os.environ.get("AI_DEV_FACTORY_RUNTIME_ROOT")
    if project_id and runtime_root:
        return Path(runtime_root) / "projects" / project_id / "state"
    if runtime_root:
        return Path(runtime_root) / "state"
    return project_root / "runs"


def resolve_logs_dir(project_root: Path, project_id: str | None = None) -> Path:
    """Return the logs/ directory.

    When *project_id* is given, returns the project-specific path under
    ``{RUNTIME_ROOT}/projects/{project_id}/logs``.
    """
    runtime_root = os.environ.get("AI_DEV_FACTORY_RUNTIME_ROOT")
    if project_id and runtime_root:
        return Path(runtime_root) / "projects" / project_id / "logs"
    if runtime_root:
        return Path(runtime_root) / "logs"
    return project_root / "logs"


def resolve_project_runtime_root(project_id: str, runtime_root: Path) -> Path:
    """Return the per-project runtime root, validated for path containment.

    Delegates to ``assert_contained`` so callers get the same safety guarantee as
    the bootstrap service.
    """
    from .project_id import assert_contained
    return assert_contained(runtime_root, project_id)


def get_sandbox_root() -> Path:
    """Return the top-level sandbox root from SANDBOX_ROOT, expanding ~. Falls back to ~/sandboxes."""
    raw = os.environ.get("SANDBOX_ROOT", "")
    if raw:
        return Path(raw).expanduser().resolve()
    return Path.home() / "sandboxes"


def get_project_name() -> str:
    """Return the project name from PROJECT_NAME, falling back to basename of AI_DEV_FACTORY_PROJECT_ROOT."""
    name = os.environ.get("PROJECT_NAME", "").strip()
    if name:
        return name
    project_root = os.environ.get("AI_DEV_FACTORY_PROJECT_ROOT", "").strip()
    if project_root:
        return Path(project_root).name
    return "default"


def get_project_sandbox_dir() -> Path:
    """Return {get_sandbox_root()}/{get_project_name()} — the per-project sandbox directory."""
    return get_sandbox_root() / get_project_name()


def _load_workers(runs_dir: Path) -> dict:
    path = runs_dir / _WORKERS_JSON
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def resolve_ticket_run_dir(
    ticket_id: str,
    runs_dir: Path,
    worktrees_dir: Path | None = None,
) -> Path:
    """Return the Path holding the ticket's state files.

    Priority:
    1. Active worktree from workers.json (most authoritative — ticket is running)
    2. worktrees_dir/TXXX/runs/TXXX if that state.json exists (ticket ran in worktree)
    3. runs_dir/TXXX (legacy fallback)
    """
    workers = _load_workers(runs_dir)
    worker = workers.get(ticket_id, {})
    wt_path = worker.get("worktree_path")
    if wt_path:
        candidate = Path(wt_path) / "runs" / ticket_id
        if candidate.exists():
            return candidate

    if worktrees_dir:
        candidate = worktrees_dir / ticket_id / "runs" / ticket_id
        if (candidate / "state.json").exists():
            return candidate

    return runs_dir / ticket_id


def resolve_ticket_cwd(
    ticket_id: str,
    project_root: Path,
    worktrees_dir: Path | None = None,
) -> Path:
    """Return the cwd to use when running run_ticket.py for a ticket.

    Priority:
    1. Active worktree from workers.json
    2. worktrees_dir/TXXX if it exists
    3. project_root (legacy fallback)
    """
    runs_dir = project_root / "runs"
    workers = _load_workers(runs_dir)
    worker = workers.get(ticket_id, {})
    wt_path = worker.get("worktree_path")
    if wt_path:
        wt = Path(wt_path)
        if wt.exists():
            return wt

    if worktrees_dir:
        candidate = worktrees_dir / ticket_id
        if candidate.exists():
            return candidate

    return project_root
