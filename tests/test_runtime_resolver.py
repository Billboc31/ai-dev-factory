"""Tests for the worktree-aware runtime resolver."""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "services"))

from control_api.services.runtime_resolver import resolve_ticket_run_dir, resolve_ticket_cwd


def _make_runs_dir(tmp_path: Path) -> Path:
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    return runs_dir


def _write_state(directory: Path, ticket_id: str, **extra) -> Path:
    run_dir = directory / ticket_id
    run_dir.mkdir(parents=True, exist_ok=True)
    state = {"ticket_id": ticket_id, "state": "PLAN_APPROVED", **extra}
    (run_dir / "state.json").write_text(json.dumps(state), encoding="utf-8")
    return run_dir


def _write_workers(runs_dir: Path, workers: dict) -> None:
    (runs_dir / "workers.json").write_text(json.dumps(workers), encoding="utf-8")


# ── resolve_ticket_run_dir ────────────────────────────────────────────────────

def test_resolve_run_dir_fallback_to_runs(tmp_path):
    runs_dir = _make_runs_dir(tmp_path)
    _write_state(runs_dir, "T001")
    result = resolve_ticket_run_dir("T001", runs_dir)
    assert result == runs_dir / "T001"


def test_resolve_run_dir_uses_active_worktree_from_workers(tmp_path):
    runs_dir = _make_runs_dir(tmp_path)
    _write_state(runs_dir, "T001")

    # Create a worktree with state
    wt_root = tmp_path / "worktrees" / "T001"
    _write_state(wt_root / "runs", "T001")

    _write_workers(runs_dir, {"T001": {"pid": 999, "worktree_path": str(wt_root)}})

    result = resolve_ticket_run_dir("T001", runs_dir)
    assert result == wt_root / "runs" / "T001"


def test_resolve_run_dir_uses_worktrees_dir_without_workers(tmp_path):
    runs_dir = _make_runs_dir(tmp_path)
    _write_state(runs_dir, "T001")

    worktrees_dir = tmp_path / "worktrees"
    wt_root = worktrees_dir / "T001"
    _write_state(wt_root / "runs", "T001")

    result = resolve_ticket_run_dir("T001", runs_dir, worktrees_dir=worktrees_dir)
    assert result == wt_root / "runs" / "T001"


def test_resolve_run_dir_workers_missing_worktree_falls_back(tmp_path):
    runs_dir = _make_runs_dir(tmp_path)
    _write_state(runs_dir, "T001")

    # workers.json points to a non-existent worktree path
    _write_workers(runs_dir, {"T001": {"pid": 999, "worktree_path": str(tmp_path / "ghost")}})

    result = resolve_ticket_run_dir("T001", runs_dir)
    assert result == runs_dir / "T001"


def test_resolve_run_dir_worktrees_dir_no_state_falls_back(tmp_path):
    runs_dir = _make_runs_dir(tmp_path)
    _write_state(runs_dir, "T001")

    # worktrees_dir exists but has no state.json for T001
    worktrees_dir = tmp_path / "worktrees"
    (worktrees_dir / "T001" / "runs" / "T001").mkdir(parents=True)

    result = resolve_ticket_run_dir("T001", runs_dir, worktrees_dir=worktrees_dir)
    assert result == runs_dir / "T001"


def test_resolve_run_dir_workers_takes_priority_over_worktrees_dir(tmp_path):
    runs_dir = _make_runs_dir(tmp_path)
    _write_state(runs_dir, "T001")

    worktrees_dir = tmp_path / "worktrees"
    wt_secondary = worktrees_dir / "T001"
    _write_state(wt_secondary / "runs", "T001", state="SECONDARY")

    wt_active = tmp_path / "active_wt"
    _write_state(wt_active / "runs", "T001", state="ACTIVE")
    _write_workers(runs_dir, {"T001": {"pid": 999, "worktree_path": str(wt_active)}})

    result = resolve_ticket_run_dir("T001", runs_dir, worktrees_dir=worktrees_dir)
    assert result == wt_active / "runs" / "T001"


# ── resolve_ticket_cwd ────────────────────────────────────────────────────────

def test_resolve_cwd_fallback_to_project_root(tmp_path):
    project_root = tmp_path / "repo"
    project_root.mkdir()
    (project_root / "runs").mkdir()
    result = resolve_ticket_cwd("T001", project_root)
    assert result == project_root


def test_resolve_cwd_uses_active_worktree_from_workers(tmp_path):
    project_root = tmp_path / "repo"
    runs_dir = project_root / "runs"
    runs_dir.mkdir(parents=True)

    wt_path = tmp_path / "worktrees" / "T001"
    wt_path.mkdir(parents=True)

    _write_workers(runs_dir, {"T001": {"pid": 999, "worktree_path": str(wt_path)}})

    result = resolve_ticket_cwd("T001", project_root)
    assert result == wt_path


def test_resolve_cwd_uses_worktrees_dir_without_workers(tmp_path):
    project_root = tmp_path / "repo"
    runs_dir = project_root / "runs"
    runs_dir.mkdir(parents=True)

    worktrees_dir = tmp_path / "worktrees"
    wt_path = worktrees_dir / "T001"
    wt_path.mkdir(parents=True)

    result = resolve_ticket_cwd("T001", project_root, worktrees_dir=worktrees_dir)
    assert result == wt_path


def test_resolve_cwd_workers_gone_worktree_still_exists(tmp_path):
    project_root = tmp_path / "repo"
    runs_dir = project_root / "runs"
    runs_dir.mkdir(parents=True)

    # workers.json points to a non-existent path
    _write_workers(runs_dir, {"T001": {"pid": 999, "worktree_path": str(tmp_path / "ghost")}})

    worktrees_dir = tmp_path / "worktrees"
    wt_path = worktrees_dir / "T001"
    wt_path.mkdir(parents=True)

    result = resolve_ticket_cwd("T001", project_root, worktrees_dir=worktrees_dir)
    # workers entry exists but path is gone — falls through to worktrees_dir scan
    assert result == wt_path
