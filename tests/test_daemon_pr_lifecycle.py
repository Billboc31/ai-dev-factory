"""Tests for T026 — PR lifecycle functions in the daemon."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "tools" / "agent_runner"))

from run_daemon import (
    _load_state_json,
    _save_state_json,
    check_and_close_issue,
    create_or_update_pr,
    handle_test_complete,
)


def _make_run_dir(tmp_path: Path, ticket_id: str = "T001", **state_extra) -> Path:
    run_dir = tmp_path / ticket_id
    run_dir.mkdir()
    state = {
        "ticket_id": ticket_id,
        "state": "TEST_COMPLETE",
        "branch": f"ticket/{ticket_id}-my-feature",
        "updated_at": "2026-01-01T00:00:00Z",
        **state_extra,
    }
    (run_dir / "state.json").write_text(json.dumps(state, indent=2), encoding="utf-8")
    return run_dir


# ── _load_state_json ──────────────────────────────────────────────────────────

def test_load_state_json_reads_file(tmp_path):
    run_dir = _make_run_dir(tmp_path, issue_number=42)
    data = _load_state_json(run_dir)
    assert data["issue_number"] == 42
    assert data["state"] == "TEST_COMPLETE"


def test_load_state_json_returns_empty_on_missing(tmp_path):
    run_dir = tmp_path / "T999"
    run_dir.mkdir()
    assert _load_state_json(run_dir) == {}


# ── _save_state_json ──────────────────────────────────────────────────────────

def test_save_state_json_writes_atomically(tmp_path):
    run_dir = _make_run_dir(tmp_path)
    data = _load_state_json(run_dir)
    data["pr_number"] = 7
    _save_state_json(run_dir, data)
    assert not (run_dir / "state.tmp").exists()
    saved = json.loads((run_dir / "state.json").read_text(encoding="utf-8"))
    assert saved["pr_number"] == 7
    assert "updated_at" in saved


# ── create_or_update_pr ───────────────────────────────────────────────────────

def test_create_or_update_pr_creates_new_pr(tmp_path):
    run_dir = _make_run_dir(tmp_path, issue_number=21)
    mock_list = MagicMock(returncode=0, stdout="[]")
    mock_create = MagicMock(returncode=0, stdout="https://github.com/owner/repo/pull/42\n")
    with patch("run_daemon.subprocess.run", side_effect=[mock_list, mock_create]) as mock_sub:
        create_or_update_pr("T001", run_dir, None)
    create_args = mock_sub.call_args_list[1][0][0]
    assert "gh" in create_args
    assert "pr" in create_args
    assert "create" in create_args
    saved = json.loads((run_dir / "state.json").read_text(encoding="utf-8"))
    assert saved["pr_number"] == 42


def test_create_or_update_pr_updates_existing_pr(tmp_path):
    run_dir = _make_run_dir(tmp_path, pr_number=55)
    mock_edit = MagicMock(returncode=0, stdout="")
    with patch("run_daemon.subprocess.run", return_value=mock_edit) as mock_sub:
        create_or_update_pr("T001", run_dir, None)
    cmd = mock_sub.call_args[0][0]
    assert "pr" in cmd
    assert "edit" in cmd
    assert "55" in cmd


def test_create_or_update_pr_finds_existing_pr_by_head(tmp_path):
    run_dir = _make_run_dir(tmp_path)
    mock_list = MagicMock(returncode=0, stdout=json.dumps([{"number": 33}]))
    mock_edit = MagicMock(returncode=0, stdout="")
    with patch("run_daemon.subprocess.run", side_effect=[mock_list, mock_edit]) as mock_sub:
        create_or_update_pr("T001", run_dir, None)
    edit_cmd = mock_sub.call_args_list[1][0][0]
    assert "edit" in edit_cmd
    assert "33" in edit_cmd


def test_create_or_update_pr_skips_when_no_branch(tmp_path):
    run_dir = tmp_path / "T001"
    run_dir.mkdir()
    (run_dir / "state.json").write_text(
        json.dumps({"ticket_id": "T001", "state": "TEST_COMPLETE"}), encoding="utf-8"
    )
    with patch("run_daemon.subprocess.run") as mock_sub:
        create_or_update_pr("T001", run_dir, None)
    mock_sub.assert_not_called()


# ── check_and_close_issue ─────────────────────────────────────────────────────

def test_check_and_close_issue_closes_merged_pr(tmp_path):
    run_dir = _make_run_dir(tmp_path, pr_number=42, issue_number=21)
    mock_view = MagicMock(returncode=0, stdout=json.dumps({"state": "MERGED"}))
    mock_close = MagicMock(returncode=0, stdout="")
    mock_label = MagicMock(returncode=0, stdout="")
    with patch("run_daemon.subprocess.run", side_effect=[mock_view, mock_close, mock_label]) as mock_sub:
        check_and_close_issue("T001", run_dir, None)
    close_cmd = mock_sub.call_args_list[1][0][0]
    assert "issue" in close_cmd
    assert "close" in close_cmd


def test_check_and_close_issue_skips_open_pr(tmp_path):
    run_dir = _make_run_dir(tmp_path, pr_number=42, issue_number=21)
    mock_view = MagicMock(returncode=0, stdout=json.dumps({"state": "OPEN"}))
    with patch("run_daemon.subprocess.run", return_value=mock_view) as mock_sub:
        check_and_close_issue("T001", run_dir, None)
    assert mock_sub.call_count == 1


def test_check_and_close_issue_skips_when_no_pr_number(tmp_path):
    run_dir = _make_run_dir(tmp_path, issue_number=21)
    with patch("run_daemon.subprocess.run") as mock_sub:
        check_and_close_issue("T001", run_dir, None)
    mock_sub.assert_not_called()


# ── handle_test_complete ──────────────────────────────────────────────────────

def test_handle_test_complete_orchestrates_pr_and_issue(tmp_path):
    run_dir = _make_run_dir(tmp_path)
    with patch("run_daemon.create_or_update_pr") as mock_pr, \
         patch("run_daemon.check_and_close_issue") as mock_close:
        handle_test_complete("T001", run_dir, None)
    mock_pr.assert_called_once_with("T001", run_dir, None)
    mock_close.assert_called_once_with("T001", run_dir, None)
