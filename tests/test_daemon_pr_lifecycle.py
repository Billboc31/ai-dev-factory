"""Tests for T026 — PR lifecycle functions in the daemon."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "tools" / "agent_runner"))

from run_daemon import (
    _checkpoint_and_push_before_pr,
    _load_state_json,
    _pr_body,
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
    saved = json.loads((run_dir / "state.json").read_text(encoding="utf-8"))
    assert saved.get("pr_synced") is True


def test_create_or_update_pr_skips_when_pr_synced(tmp_path):
    run_dir = _make_run_dir(tmp_path, pr_number=55, pr_synced=True)
    with patch("run_daemon.subprocess.run") as mock_sub:
        create_or_update_pr("T001", run_dir, None)
    mock_sub.assert_not_called()


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
    saved = json.loads((run_dir / "state.json").read_text(encoding="utf-8"))
    assert saved.get("issue_closed") is True


def test_check_and_close_issue_skips_when_already_closed(tmp_path):
    run_dir = _make_run_dir(tmp_path, pr_number=42, issue_number=21, issue_closed=True)
    with patch("run_daemon.subprocess.run") as mock_sub:
        check_and_close_issue("T001", run_dir, None)
    mock_sub.assert_not_called()


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


# ── _pr_body ─────────────────────────────────────────────────────────────────

def test_pr_body_has_approved_gates_checked():
    body = _pr_body("T001", 21)
    assert "- [x] PLAN_APPROVED" in body
    assert "- [x] IMPLEMENTATION_APPROVED" in body
    assert "- [ ] MEMORY_APPROVED" in body
    assert "Closes #21" in body


# ── handle_test_complete ──────────────────────────────────────────────────────

def test_handle_test_complete_orchestrates_pr_and_issue(tmp_path):
    run_dir = _make_run_dir(tmp_path)
    with patch("run_daemon._checkpoint_and_push_before_pr") as mock_ckpt, \
         patch("run_daemon.create_or_update_pr") as mock_pr, \
         patch("run_daemon.check_and_close_issue") as mock_close:
        handle_test_complete("T001", run_dir, None)
    mock_ckpt.assert_called_once_with("T001")
    mock_pr.assert_called_once_with("T001", run_dir, None)
    mock_close.assert_called_once_with("T001", run_dir, None)


def test_handle_test_complete_checkpoints_before_pr(tmp_path):
    call_order = []
    run_dir = _make_run_dir(tmp_path)
    with patch("run_daemon._checkpoint_and_push_before_pr", side_effect=lambda *a: call_order.append("ckpt")), \
         patch("run_daemon.create_or_update_pr", side_effect=lambda *a: call_order.append("pr")), \
         patch("run_daemon.check_and_close_issue"):
        handle_test_complete("T001", run_dir, None)
    assert call_order.index("ckpt") < call_order.index("pr")


def test_checkpoint_and_push_before_pr_calls_commit_with_include_code(tmp_path):
    subprocess_calls = []

    def fake_run(args, **kwargs):
        subprocess_calls.append(args)
        return MagicMock(stdout="", stderr="", returncode=0)

    with patch("run_daemon.subprocess.run", side_effect=fake_run):
        _checkpoint_and_push_before_pr("T001")

    commit_calls = [c for c in subprocess_calls if "--commit" in c]
    assert len(commit_calls) == 1
    assert "--include-code" in commit_calls[0]


def test_checkpoint_and_push_before_pr_pushes_after_successful_commit(tmp_path):
    subprocess_calls = []

    def fake_run(args, **kwargs):
        subprocess_calls.append(args)
        return MagicMock(stdout="", stderr="", returncode=0)

    with patch("run_daemon.subprocess.run", side_effect=fake_run):
        _checkpoint_and_push_before_pr("T001")

    push_calls = [c for c in subprocess_calls if "--push" in c]
    assert len(push_calls) == 1


def test_checkpoint_and_push_before_pr_skips_push_when_nothing_to_commit(tmp_path):
    subprocess_calls = []

    def fake_run(args, **kwargs):
        subprocess_calls.append(args)
        # rc=1 means nothing to commit
        return MagicMock(stdout="", stderr="", returncode=1)

    with patch("run_daemon.subprocess.run", side_effect=fake_run):
        _checkpoint_and_push_before_pr("T001")

    push_calls = [c for c in subprocess_calls if "--push" in c]
    assert push_calls == []


# ── no-diff PR hardening ──────────────────────────────────────────────────────

def test_create_or_update_pr_marks_archived_on_no_diff_error(tmp_path):
    run_dir = _make_run_dir(tmp_path)
    mock_list = MagicMock(returncode=0, stdout="[]")
    mock_create = MagicMock(
        returncode=1, stdout="",
        stderr="No commits between main and ticket/T001-my-feature",
    )
    with patch("run_daemon.subprocess.run", side_effect=[mock_list, mock_create]):
        create_or_update_pr("T001", run_dir, None)
    saved = json.loads((run_dir / "state.json").read_text(encoding="utf-8"))
    assert saved.get("pr_skipped_no_diff") is True
    assert saved.get("daemon_archived") is True


def test_create_or_update_pr_does_not_mark_archived_on_other_error(tmp_path):
    run_dir = _make_run_dir(tmp_path)
    mock_list = MagicMock(returncode=0, stdout="[]")
    mock_create = MagicMock(returncode=1, stdout="", stderr="some other gh error")
    with patch("run_daemon.subprocess.run", side_effect=[mock_list, mock_create]):
        create_or_update_pr("T001", run_dir, None)
    saved = json.loads((run_dir / "state.json").read_text(encoding="utf-8"))
    assert saved.get("pr_skipped_no_diff") is None
    assert saved.get("daemon_archived") is None
