"""Tests for T113 — intake worktree isolation."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "tools" / "agent_runner"))

from run_daemon import (
    _get_run_dir,
    _load_project_map,
    call_issue_intake,
    poll_github_issues,
    poll_project_map,
    scan_tickets,
)
from worktree_manager import ensure_intake_worktree


# ── helpers ───────────────────────────────────────────────────────────────────

def _write_state_in_runs(runs_dir: Path, ticket_id: str, state: str) -> None:
    """Write state.json directly under runs_dir/ticket_id/ (main runs directory layout)."""
    run_dir = runs_dir / ticket_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "state.json").write_text(
        json.dumps({"ticket_id": ticket_id, "state": state, "updated_at": "2026-01-01T00:00:00Z"}),
        encoding="utf-8",
    )


def _write_state_in_worktree(worktree: Path, ticket_id: str, state: str) -> None:
    """Write state.json under worktree/runs/ticket_id/ (worktree layout)."""
    run_dir = worktree / "runs" / ticket_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "state.json").write_text(
        json.dumps({"ticket_id": ticket_id, "state": state, "updated_at": "2026-01-01T00:00:00Z"}),
        encoding="utf-8",
    )


def _make_intake_worktree(worktrees_dir: Path) -> Path:
    intake_path = worktrees_dir / "_intake"
    intake_path.mkdir(parents=True, exist_ok=True)
    return intake_path


# ── ensure_intake_worktree ────────────────────────────────────────────────────

def test_ensure_intake_worktree_returns_true_when_already_exists(tmp_path):
    worktrees_dir = tmp_path / "worktrees"
    intake_path = worktrees_dir / "_intake"
    intake_path.mkdir(parents=True)
    ok, path = ensure_intake_worktree(worktrees_dir)
    assert ok is True
    assert path == intake_path


def test_ensure_intake_worktree_creates_when_absent(tmp_path):
    worktrees_dir = tmp_path / "worktrees"
    mock_result = MagicMock(returncode=0)
    with patch("worktree_manager.subprocess.run", return_value=mock_result) as mock_sub:
        ok, path = ensure_intake_worktree(worktrees_dir, repo_root=tmp_path)
    assert ok is True
    assert path == worktrees_dir / "_intake"
    cmd = mock_sub.call_args[0][0]
    assert "worktree" in cmd
    assert "add" in cmd
    assert str(worktrees_dir / "_intake") in cmd
    assert "main" in cmd


def test_ensure_intake_worktree_returns_false_on_git_failure(tmp_path):
    worktrees_dir = tmp_path / "worktrees"
    mock_result = MagicMock(returncode=1, stderr="error")
    with patch("worktree_manager.subprocess.run", return_value=mock_result):
        ok, path = ensure_intake_worktree(worktrees_dir)
    assert ok is False


def test_ensure_intake_worktree_passes_repo_root_as_cwd(tmp_path):
    worktrees_dir = tmp_path / "worktrees"
    repo_root = tmp_path / "repo"
    mock_result = MagicMock(returncode=0)
    with patch("worktree_manager.subprocess.run", return_value=mock_result) as mock_sub:
        ensure_intake_worktree(worktrees_dir, repo_root=repo_root)
    kwargs = mock_sub.call_args[1]
    assert kwargs.get("cwd") == str(repo_root)


# ── call_issue_intake with cwd ────────────────────────────────────────────────

def test_call_issue_intake_passes_cwd_to_subprocess(tmp_path):
    mock_result = MagicMock(returncode=0, stdout="", stderr="")
    with patch("run_daemon.subprocess.run", return_value=mock_result) as mock_sub:
        call_issue_intake(42, "T001", "feat", None, cwd="/some/intake/path")
    kwargs = mock_sub.call_args[1]
    assert kwargs.get("cwd") == "/some/intake/path"


def test_call_issue_intake_cwd_none_by_default(tmp_path):
    mock_result = MagicMock(returncode=0, stdout="", stderr="")
    with patch("run_daemon.subprocess.run", return_value=mock_result) as mock_sub:
        call_issue_intake(42, "T001", "feat", None)
    kwargs = mock_sub.call_args[1]
    assert kwargs.get("cwd") is None


# ── scan_tickets tier 3 (_intake) ─────────────────────────────────────────────

def test_scan_tickets_finds_ticket_in_intake_worktree(tmp_path):
    runs = tmp_path / "runs"
    runs.mkdir()
    worktrees_dir = tmp_path / "worktrees"
    intake = _make_intake_worktree(worktrees_dir)
    _write_state_in_worktree(intake, "T001", "INIT")

    result = scan_tickets(runs, worktrees_dir=worktrees_dir)
    assert ("T001", "INIT") in result


def test_scan_tickets_intake_does_not_override_txxx_worktree(tmp_path):
    runs = tmp_path / "runs"
    runs.mkdir()
    worktrees_dir = tmp_path / "worktrees"
    intake = _make_intake_worktree(worktrees_dir)

    # T001 in TXXX worktree with state PLAN_APPROVED
    txxx = worktrees_dir / "T001"
    _write_state_in_worktree(txxx, "T001", "PLAN_APPROVED")
    # T001 in _intake with older state INIT — should not override
    _write_state_in_worktree(intake, "T001", "INIT")

    result = scan_tickets(runs, worktrees_dir=worktrees_dir)
    states = dict(result)
    assert states["T001"] == "PLAN_APPROVED"


def test_scan_tickets_intake_does_not_override_main_runs(tmp_path):
    runs = tmp_path / "runs"
    worktrees_dir = tmp_path / "worktrees"
    intake = _make_intake_worktree(worktrees_dir)

    # T001 in main runs/ with PLAN_APPROVED
    _write_state_in_runs(runs, "T001", "PLAN_APPROVED")
    # T001 in _intake with INIT — main runs takes priority (tier 2 > tier 3)
    _write_state_in_worktree(intake, "T001", "INIT")

    result = scan_tickets(runs, worktrees_dir=worktrees_dir)
    states = dict(result)
    assert states["T001"] == "PLAN_APPROVED"


def test_scan_tickets_intake_skips_non_ticket_dirs(tmp_path):
    runs = tmp_path / "runs"
    runs.mkdir()
    worktrees_dir = tmp_path / "worktrees"
    intake = _make_intake_worktree(worktrees_dir)

    # non-ticket dir in _intake/runs/
    non_ticket = intake / "runs" / "some-dir"
    non_ticket.mkdir(parents=True)
    (non_ticket / "state.json").write_text(
        json.dumps({"state": "INIT"}), encoding="utf-8"
    )

    result = scan_tickets(runs, worktrees_dir=worktrees_dir)
    assert result == []


def test_scan_tickets_intake_skips_daemon_archived(tmp_path):
    runs = tmp_path / "runs"
    runs.mkdir()
    worktrees_dir = tmp_path / "worktrees"
    intake = _make_intake_worktree(worktrees_dir)

    run_dir = intake / "runs" / "T001"
    run_dir.mkdir(parents=True)
    (run_dir / "state.json").write_text(
        json.dumps({"ticket_id": "T001", "state": "INIT", "daemon_archived": True}),
        encoding="utf-8",
    )

    result = scan_tickets(runs, worktrees_dir=worktrees_dir)
    assert result == []


# ── _get_run_dir with _intake fallback ───────────────────────────────────────

def test_get_run_dir_uses_intake_when_no_txxx_worktree(tmp_path):
    runs = tmp_path / "runs"
    runs.mkdir()
    worktrees_dir = tmp_path / "worktrees"
    intake = _make_intake_worktree(worktrees_dir)
    intake_run_dir = intake / "runs" / "T001"
    intake_run_dir.mkdir(parents=True)

    result = _get_run_dir("T001", runs, worktrees_dir=worktrees_dir)
    assert result == intake_run_dir


def test_get_run_dir_prefers_txxx_worktree_over_intake(tmp_path):
    runs = tmp_path / "runs"
    runs.mkdir()
    worktrees_dir = tmp_path / "worktrees"
    intake = _make_intake_worktree(worktrees_dir)

    txxx_run_dir = worktrees_dir / "T001" / "runs" / "T001"
    txxx_run_dir.mkdir(parents=True)
    intake_run_dir = intake / "runs" / "T001"
    intake_run_dir.mkdir(parents=True)

    result = _get_run_dir("T001", runs, worktrees_dir=worktrees_dir)
    assert result == txxx_run_dir


def test_get_run_dir_falls_back_to_main_runs(tmp_path):
    runs = tmp_path / "runs"
    runs.mkdir()
    worktrees_dir = tmp_path / "worktrees"
    _make_intake_worktree(worktrees_dir)  # _intake exists but no T001 inside

    result = _get_run_dir("T001", runs, worktrees_dir=worktrees_dir)
    assert result == runs / "T001"


# ── poll_github_issues with intake worktree ───────────────────────────────────

def test_poll_github_issues_uses_intake_pull_when_worktrees_dir_set(tmp_path):
    runs = tmp_path / "runs"
    runs.mkdir()
    worktrees_dir = tmp_path / "worktrees"
    intake = _make_intake_worktree(worktrees_dir)

    issues = [{"number": 42, "title": "New feature"}]
    pull_result = MagicMock(returncode=0, stdout="", stderr="")

    with patch("run_daemon.fetch_ready_issues", return_value=issues), \
         patch("run_daemon.call_issue_intake", return_value=True), \
         patch("run_daemon.ensure_intake_worktree", return_value=(True, intake)) as mock_ensure, \
         patch("run_daemon.subprocess.run", return_value=pull_result) as mock_sub, \
         patch("run_daemon.create_ticket_worktree", return_value=(True, "ok")):
        poll_github_issues(runs, "ai-ready", None, worktrees_dir=worktrees_dir)

    mock_ensure.assert_called_once()
    # subprocess.run should be called for git pull in _intake, not git checkout main
    for c in mock_sub.call_args_list:
        cmd = c[0][0]
        assert "checkout" not in cmd, f"unexpected git checkout: {cmd}"


def test_poll_github_issues_intake_cwd_passed_to_call_issue_intake(tmp_path):
    runs = tmp_path / "runs"
    runs.mkdir()
    worktrees_dir = tmp_path / "worktrees"
    intake = _make_intake_worktree(worktrees_dir)

    issues = [{"number": 42, "title": "New feature"}]
    pull_ok = MagicMock(returncode=0, stdout="", stderr="")

    with patch("run_daemon.fetch_ready_issues", return_value=issues), \
         patch("run_daemon.call_issue_intake", return_value=True) as mock_intake, \
         patch("run_daemon.ensure_intake_worktree", return_value=(True, intake)), \
         patch("run_daemon.subprocess.run", return_value=pull_ok), \
         patch("run_daemon.create_ticket_worktree", return_value=(True, "ok")):
        poll_github_issues(runs, "ai-ready", None, worktrees_dir=worktrees_dir)

    kwargs = mock_intake.call_args[1]
    assert kwargs.get("cwd") == str(intake)


def test_poll_github_issues_legacy_path_when_worktrees_dir_none(tmp_path):
    runs = tmp_path / "runs"
    runs.mkdir()
    issues = [{"number": 42, "title": "New feature"}]
    git_ok = MagicMock(returncode=0, stdout="", stderr="")

    with patch("run_daemon.fetch_ready_issues", return_value=issues), \
         patch("run_daemon.call_issue_intake", return_value=True), \
         patch("run_daemon.subprocess.run", return_value=git_ok) as mock_sub:
        poll_github_issues(runs, "ai-ready", None, worktrees_dir=None)

    cmds = [c[0][0] for c in mock_sub.call_args_list]
    checkout_calls = [c for c in cmds if "checkout" in c]
    assert len(checkout_calls) >= 1, "legacy path must call git checkout main"


def test_poll_github_issues_falls_back_to_legacy_when_intake_creation_fails(tmp_path):
    runs = tmp_path / "runs"
    runs.mkdir()
    worktrees_dir = tmp_path / "worktrees"
    intake = worktrees_dir / "_intake"  # does not exist yet

    issues = [{"number": 42, "title": "New feature"}]
    git_ok = MagicMock(returncode=0, stdout="", stderr="")

    with patch("run_daemon.fetch_ready_issues", return_value=issues), \
         patch("run_daemon.call_issue_intake", return_value=True), \
         patch("run_daemon.ensure_intake_worktree", return_value=(False, intake)), \
         patch("run_daemon.subprocess.run", return_value=git_ok) as mock_sub:
        poll_github_issues(runs, "ai-ready", None, worktrees_dir=worktrees_dir)

    cmds = [c[0][0] for c in mock_sub.call_args_list]
    checkout_calls = [c for c in cmds if "checkout" in c]
    assert len(checkout_calls) >= 1, "must fall back to legacy checkout main"


# ── _load_project_map with worktrees_dir ─────────────────────────────────────

def test_load_project_map_reads_from_intake_when_available(tmp_path):
    runs = tmp_path / "runs"
    runs.mkdir()
    worktrees_dir = tmp_path / "worktrees"
    intake = _make_intake_worktree(worktrees_dir)
    intake_map_path = intake / "runs" / ".project-map.json"
    intake_map_path.parent.mkdir(parents=True, exist_ok=True)
    intake_map_path.write_text(json.dumps({"next_recommended": "T005"}), encoding="utf-8")

    result = _load_project_map(runs, worktrees_dir=worktrees_dir)
    assert result == {"next_recommended": "T005"}


def test_load_project_map_falls_back_to_runs_dir_when_no_intake_map(tmp_path):
    runs = tmp_path / "runs"
    runs.mkdir()
    (runs / ".project-map.json").write_text(
        json.dumps({"next_recommended": "T003"}), encoding="utf-8"
    )
    worktrees_dir = tmp_path / "worktrees"
    _make_intake_worktree(worktrees_dir)  # _intake exists but no map

    result = _load_project_map(runs, worktrees_dir=worktrees_dir)
    assert result == {"next_recommended": "T003"}


def test_load_project_map_returns_none_when_no_map_anywhere(tmp_path):
    runs = tmp_path / "runs"
    runs.mkdir()
    worktrees_dir = tmp_path / "worktrees"
    _make_intake_worktree(worktrees_dir)

    result = _load_project_map(runs, worktrees_dir=worktrees_dir)
    assert result is None


# ── poll_project_map uses _intake/runs/ ───────────────────────────────────────

def test_poll_project_map_passes_intake_runs_as_runs_dir(tmp_path):
    runs = tmp_path / "runs"
    runs.mkdir()
    worktrees_dir = tmp_path / "worktrees"
    intake = _make_intake_worktree(worktrees_dir)
    intake_runs = intake / "runs"
    intake_runs.mkdir(parents=True, exist_ok=True)

    mock_result = MagicMock(returncode=0, stdout="", stderr="")
    with patch("run_daemon.subprocess.run", return_value=mock_result) as mock_sub:
        poll_project_map(runs, None, worktrees_dir=worktrees_dir)

    cmd = mock_sub.call_args[0][0]
    assert "--runs-dir" in cmd
    idx = cmd.index("--runs-dir")
    assert cmd[idx + 1] == str(intake_runs)


def test_poll_project_map_uses_original_runs_dir_when_no_intake(tmp_path):
    runs = tmp_path / "runs"
    runs.mkdir()
    worktrees_dir = tmp_path / "worktrees"
    worktrees_dir.mkdir()  # no _intake inside

    mock_result = MagicMock(returncode=0, stdout="", stderr="")
    with patch("run_daemon.subprocess.run", return_value=mock_result) as mock_sub:
        poll_project_map(runs, None, worktrees_dir=worktrees_dir)

    cmd = mock_sub.call_args[0][0]
    idx = cmd.index("--runs-dir")
    assert cmd[idx + 1] == str(runs)
