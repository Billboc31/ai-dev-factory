"""Tests for T026 — continuous checkpoint publishing (auto-commit/push flags)."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "tools" / "agent_runner"))

from run_daemon import launch_ticket, run_once


def _write_state(runs_dir: Path, ticket_id: str, state: str) -> Path:
    run_dir = runs_dir / ticket_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "state.json").write_text(
        json.dumps({"ticket_id": ticket_id, "state": state, "updated_at": "2026-01-01T00:00:00Z"}),
        encoding="utf-8",
    )
    return run_dir


# ── launch_ticket auto flags ───────────────────────────────────────────────────

def test_launch_ticket_passes_auto_commit_flag(tmp_path):
    runs = tmp_path / "runs"
    _write_state(runs, "T001", "PLAN_APPROVED")
    mock_result = MagicMock(stdout="", stderr="", returncode=0)
    with patch("run_daemon.subprocess.run", return_value=mock_result) as mock_sub:
        launch_ticket("T001", "test-cmd", dry_run=False, runs_dir=runs, auto_commit=True)
    cmd = mock_sub.call_args[0][0]
    assert "--auto-commit" in cmd


def test_launch_ticket_passes_auto_push_flag(tmp_path):
    runs = tmp_path / "runs"
    _write_state(runs, "T001", "PLAN_APPROVED")
    mock_result = MagicMock(stdout="", stderr="", returncode=0)
    with patch("run_daemon.subprocess.run", return_value=mock_result) as mock_sub:
        launch_ticket("T001", "test-cmd", dry_run=False, runs_dir=runs, auto_push=True)
    cmd = mock_sub.call_args[0][0]
    assert "--auto-push" in cmd


def test_launch_ticket_passes_auto_include_code_flag(tmp_path):
    runs = tmp_path / "runs"
    _write_state(runs, "T001", "PLAN_APPROVED")
    mock_result = MagicMock(stdout="", stderr="", returncode=0)
    with patch("run_daemon.subprocess.run", return_value=mock_result) as mock_sub:
        launch_ticket("T001", "test-cmd", dry_run=False, runs_dir=runs, auto_include_code=True)
    cmd = mock_sub.call_args[0][0]
    assert "--auto-include-code" in cmd


def test_launch_ticket_no_auto_flags_by_default(tmp_path):
    runs = tmp_path / "runs"
    _write_state(runs, "T001", "PLAN_APPROVED")
    mock_result = MagicMock(stdout="", stderr="", returncode=0)
    with patch("run_daemon.subprocess.run", return_value=mock_result) as mock_sub:
        launch_ticket("T001", "test-cmd", dry_run=False, runs_dir=runs)
    cmd = mock_sub.call_args[0][0]
    assert "--auto-commit" not in cmd
    assert "--auto-push" not in cmd
    assert "--auto-include-code" not in cmd


def test_run_once_passes_auto_flags_to_launch_ticket(tmp_path):
    runs = tmp_path / "runs"
    _write_state(runs, "T001", "PLAN_APPROVED")
    with patch("run_daemon.launch_ticket") as mock_launch:
        run_once("test-cmd", False, runs, auto_commit=True, auto_push=True, auto_include_code=True)
    mock_launch.assert_called_once_with(
        "T001", "test-cmd", False, runs,
        auto_commit=True, auto_push=True, auto_include_code=True,
    )
