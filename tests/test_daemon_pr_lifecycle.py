"""Tests for T026 — PR lifecycle functions."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "tools" / "agent_runner"))

from ticket_pr_lifecycle import (
    INTEGRATION_BRANCH,
    _checkpoint_and_push_before_pr,
    _load_state_json,
    _pr_body,
    _save_state_json,
    auto_merge_pr,
    check_and_close_issue,
    create_or_update_pr,
    ensure_pr_base_branch,
    handle_test_complete,
    rebase_onto_ref,
    resolve_integration_branch,
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
    mock_fallback = MagicMock(returncode=0, stdout="[]")
    mock_create = MagicMock(
        returncode=0,
        stdout=json.dumps({"number": 42, "html_url": "https://github.com/owner/repo/pull/42"}),
    )
    with patch("ticket_pr_lifecycle._resolve_owner_repo", return_value="owner/repo"), \
         patch("ticket_pr_lifecycle.subprocess.run", side_effect=[mock_list, mock_fallback, mock_create]) as mock_sub:
        create_or_update_pr("T001", run_dir, "owner/repo")
    create_args = mock_sub.call_args_list[2][0][0]
    assert create_args[:3] == ["gh", "api", "repos/owner/repo/pulls"]
    assert "--method" in create_args and "POST" in create_args
    assert any(a.startswith("base=") for a in create_args)
    assert any(a == f"base={INTEGRATION_BRANCH}" or a.endswith(f"={INTEGRATION_BRANCH}") for a in create_args)
    saved = json.loads((run_dir / "state.json").read_text(encoding="utf-8"))
    assert saved["pr_number"] == 42


def test_create_or_update_pr_targets_integration_branch(tmp_path):
    run_dir = _make_run_dir(tmp_path)
    mock_list = MagicMock(returncode=0, stdout="[]")
    mock_fallback = MagicMock(returncode=0, stdout="[]")
    mock_create = MagicMock(
        returncode=0,
        stdout=json.dumps({"number": 5, "html_url": "https://github.com/owner/repo/pull/5"}),
    )
    with patch("ticket_pr_lifecycle._resolve_owner_repo", return_value="owner/repo"), \
         patch("ticket_pr_lifecycle.subprocess.run", side_effect=[mock_list, mock_fallback, mock_create]) as mock_sub:
        create_or_update_pr("T001", run_dir, "owner/repo")
    create_args = mock_sub.call_args_list[2][0][0]
    assert "base=main" in create_args


def test_ensure_pr_base_branch_retargests_when_needed(tmp_path):
    run_dir = _make_run_dir(tmp_path, pr_number=34)
    mock_view = MagicMock(returncode=0, stdout='{"baseRefName":"ai-dev-factory/bootstrap-agent-layout"}')
    mock_edit = MagicMock(returncode=0, stdout="")
    with patch("ticket_pr_lifecycle.subprocess.run", side_effect=[mock_view, mock_edit]) as mock_sub:
        assert ensure_pr_base_branch("T001", run_dir, "owner/repo") is True
    edit_args = mock_sub.call_args_list[1][0][0]
    assert edit_args == ["gh", "pr", "edit", "34", "--base", "main", "--repo", "owner/repo"]


def test_rebase_onto_ref_normalizes_branch():
    assert rebase_onto_ref("main") == "origin/main"
    assert rebase_onto_ref("origin/main") == "origin/main"


def test_resolve_integration_branch_defaults_to_main(tmp_path):
    run_dir = _make_run_dir(tmp_path)
    assert resolve_integration_branch("T001", run_dir) == "main"

def test_create_or_update_pr_updates_existing_pr(tmp_path):
    run_dir = _make_run_dir(tmp_path, pr_number=55)
    mock_edit = MagicMock(returncode=0, stdout="")
    with patch("ticket_pr_lifecycle._resolve_owner_repo", return_value="owner/repo"), \
         patch("ticket_pr_lifecycle.subprocess.run", return_value=mock_edit) as mock_sub:
        create_or_update_pr("T001", run_dir, "owner/repo")
    cmd = mock_sub.call_args[0][0]
    assert cmd[:3] == ["gh", "api", "repos/owner/repo/pulls/55"]
    assert "PATCH" in cmd
    saved = json.loads((run_dir / "state.json").read_text(encoding="utf-8"))
    assert saved.get("pr_synced") is True


def test_create_or_update_pr_skips_when_pr_synced(tmp_path):
    run_dir = _make_run_dir(tmp_path, pr_number=55, pr_synced=True)
    with patch("ticket_pr_lifecycle.subprocess.run") as mock_sub:
        create_or_update_pr("T001", run_dir, None)
    mock_sub.assert_not_called()


def test_create_or_update_pr_finds_existing_pr_by_head(tmp_path):
    run_dir = _make_run_dir(tmp_path)
    mock_list = MagicMock(returncode=0, stdout=json.dumps([{"number": 33}]))
    mock_edit = MagicMock(returncode=0, stdout="")
    with patch("ticket_pr_lifecycle._resolve_owner_repo", return_value="owner/repo"), \
         patch("ticket_pr_lifecycle.subprocess.run", side_effect=[mock_list, mock_edit]) as mock_sub:
        create_or_update_pr("T001", run_dir, "owner/repo")
    list_cmd = mock_sub.call_args_list[0][0][0]
    assert "repos/owner/repo/pulls?" in list_cmd[2]
    assert "head=owner:ticket/T001-my-feature" in list_cmd[2]
    edit_cmd = mock_sub.call_args_list[1][0][0]
    assert "pulls/33" in edit_cmd[2]
    assert "PATCH" in edit_cmd


def test_create_or_update_pr_skips_when_no_branch(tmp_path):
    run_dir = tmp_path / "T001"
    run_dir.mkdir()
    (run_dir / "state.json").write_text(
        json.dumps({"ticket_id": "T001", "state": "TEST_COMPLETE"}), encoding="utf-8"
    )
    with patch("ticket_pr_lifecycle.subprocess.run") as mock_sub:
        create_or_update_pr("T001", run_dir, None)
    mock_sub.assert_not_called()


# ── check_and_close_issue ─────────────────────────────────────────────────────

def test_check_and_close_issue_closes_merged_pr(tmp_path):
    run_dir = _make_run_dir(tmp_path, pr_number=42, issue_number=21)
    mock_view = MagicMock(returncode=0, stdout=json.dumps({"merged": True, "state": "closed"}))
    mock_close = MagicMock(returncode=0, stdout="")
    mock_label = MagicMock(returncode=0, stdout="")
    with patch("ticket_pr_lifecycle._resolve_owner_repo", return_value="owner/repo"), \
         patch("ticket_pr_lifecycle.subprocess.run", side_effect=[mock_view, mock_close, mock_label]) as mock_sub:
        check_and_close_issue("T001", run_dir, "owner/repo")
    close_cmd = mock_sub.call_args_list[1][0][0]
    assert close_cmd[:3] == ["gh", "api", "repos/owner/repo/issues/21"]
    assert "PATCH" in close_cmd
    saved = json.loads((run_dir / "state.json").read_text(encoding="utf-8"))
    assert saved.get("issue_closed") is True


def test_check_and_close_issue_skips_when_already_closed(tmp_path):
    run_dir = _make_run_dir(tmp_path, pr_number=42, issue_number=21, issue_closed=True)
    with patch("ticket_pr_lifecycle.subprocess.run") as mock_sub:
        check_and_close_issue("T001", run_dir, None)
    mock_sub.assert_not_called()


def test_check_and_close_issue_skips_open_pr(tmp_path):
    run_dir = _make_run_dir(tmp_path, pr_number=42, issue_number=21)
    mock_view = MagicMock(returncode=0, stdout=json.dumps({"merged": False, "state": "open"}))
    with patch("ticket_pr_lifecycle._resolve_owner_repo", return_value="owner/repo"), \
         patch("ticket_pr_lifecycle.subprocess.run", return_value=mock_view) as mock_sub:
        check_and_close_issue("T001", run_dir, "owner/repo")
    assert mock_sub.call_count == 1


def test_check_and_close_issue_skips_when_no_pr_number(tmp_path):
    run_dir = _make_run_dir(tmp_path, issue_number=21)
    with patch("ticket_pr_lifecycle.subprocess.run") as mock_sub:
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
    with patch("ticket_pr_lifecycle._checkpoint_and_push_before_pr") as mock_ckpt, \
         patch("ticket_pr_lifecycle.create_or_update_pr") as mock_pr, \
         patch("ticket_pr_lifecycle.auto_merge_pr") as mock_merge, \
         patch("ticket_pr_lifecycle.check_and_close_issue") as mock_close:
        handle_test_complete("T001", run_dir, None)
    mock_ckpt.assert_called_once_with("T001", cwd=None)
    mock_pr.assert_called_once_with("T001", run_dir, None)
    mock_merge.assert_called_once_with("T001", run_dir, None)
    mock_close.assert_called_once_with("T001", run_dir, None)


def test_handle_test_complete_checkpoints_before_pr(tmp_path):
    call_order = []
    run_dir = _make_run_dir(tmp_path)

    def ckpt_side(*a, **kw):
        call_order.append("ckpt")
        return True

    with patch("ticket_pr_lifecycle._checkpoint_and_push_before_pr", side_effect=ckpt_side), \
         patch("ticket_pr_lifecycle.create_or_update_pr", side_effect=lambda *a: call_order.append("pr")), \
         patch("ticket_pr_lifecycle.auto_merge_pr"), \
         patch("ticket_pr_lifecycle.check_and_close_issue"):
        handle_test_complete("T001", run_dir, None)
    assert call_order.index("ckpt") < call_order.index("pr")


def test_handle_test_complete_skips_pr_when_push_fails(tmp_path):
    run_dir = _make_run_dir(tmp_path)
    with patch("ticket_pr_lifecycle._checkpoint_and_push_before_pr", return_value=False), \
         patch("ticket_pr_lifecycle.create_or_update_pr") as mock_pr, \
         patch("ticket_pr_lifecycle.auto_merge_pr") as mock_merge, \
         patch("ticket_pr_lifecycle.check_and_close_issue") as mock_close:
        handle_test_complete("T001", run_dir, None)
    mock_pr.assert_not_called()
    mock_merge.assert_not_called()
    mock_close.assert_not_called()


def test_checkpoint_and_push_before_pr_calls_checkpoint_with_include_code():
    with patch("ticket_pr_lifecycle.checkpoint_transition") as mock_ckpt:
        _checkpoint_and_push_before_pr("T001")
    mock_ckpt.assert_called_once()
    _args, kwargs = mock_ckpt.call_args
    assert kwargs.get("include_code") is True


def test_checkpoint_and_push_before_pr_calls_checkpoint_with_push():
    with patch("ticket_pr_lifecycle.checkpoint_transition") as mock_ckpt:
        _checkpoint_and_push_before_pr("T001")
    mock_ckpt.assert_called_once()
    _args, kwargs = mock_ckpt.call_args
    assert kwargs.get("push") is True


def test_checkpoint_and_push_before_pr_returns_true_on_success():
    with patch("ticket_pr_lifecycle.checkpoint_transition"):
        result = _checkpoint_and_push_before_pr("T001")
    assert result is True


# ── no-diff PR hardening ──────────────────────────────────────────────────────

def test_create_or_update_pr_marks_archived_on_no_diff_error(tmp_path):
    run_dir = _make_run_dir(tmp_path)
    mock_list = MagicMock(returncode=0, stdout="[]")
    mock_fallback = MagicMock(returncode=0, stdout="[]")
    mock_create = MagicMock(
        returncode=1, stdout="",
        stderr='{"message":"Validation Failed","errors":[{"message":"No commits between main and ticket/T001-my-feature"}]}',
    )
    with patch("ticket_pr_lifecycle._resolve_owner_repo", return_value="owner/repo"), \
         patch("ticket_pr_lifecycle.subprocess.run", side_effect=[mock_list, mock_fallback, mock_create]):
        create_or_update_pr("T001", run_dir, "owner/repo")
    saved = json.loads((run_dir / "state.json").read_text(encoding="utf-8"))
    assert saved.get("pr_skipped_no_diff") is True
    assert saved.get("daemon_archived") is True


def test_create_or_update_pr_does_not_mark_archived_on_other_error(tmp_path):
    run_dir = _make_run_dir(tmp_path)
    mock_list = MagicMock(returncode=0, stdout="[]")
    mock_fallback = MagicMock(returncode=0, stdout="[]")
    mock_create = MagicMock(returncode=1, stdout="", stderr="some other gh error")
    with patch("ticket_pr_lifecycle._resolve_owner_repo", return_value="owner/repo"), \
         patch("ticket_pr_lifecycle.subprocess.run", side_effect=[mock_list, mock_fallback, mock_create]):
        create_or_update_pr("T001", run_dir, "owner/repo")
    saved = json.loads((run_dir / "state.json").read_text(encoding="utf-8"))
    assert saved.get("pr_skipped_no_diff") is None
    assert saved.get("daemon_archived") is None


# ── auto_merge_pr ─────────────────────────────────────────────────────────────

def test_auto_merge_pr_merges_open_pr(tmp_path):
    run_dir = _make_run_dir(tmp_path, pr_number=42)
    mock_view = MagicMock(returncode=0, stdout=json.dumps({"state": "OPEN", "mergeable": "MERGEABLE"}))
    mock_merge = MagicMock(returncode=0, stdout="", stderr="")
    with patch("ticket_pr_lifecycle.subprocess.run", side_effect=[mock_view, mock_merge]) as mock_sub:
        result = auto_merge_pr("T001", run_dir, None)
    assert result is True
    merge_cmd = mock_sub.call_args_list[1][0][0]
    assert "pr" in merge_cmd
    assert "merge" in merge_cmd
    assert "42" in merge_cmd
    assert "--squash" in merge_cmd
    assert "--delete-branch" in merge_cmd
    saved = json.loads((run_dir / "state.json").read_text(encoding="utf-8"))
    assert saved.get("pr_merged") is True
    assert saved.get("daemon_archived") is True


def test_auto_merge_pr_skips_when_no_pr_number(tmp_path):
    run_dir = _make_run_dir(tmp_path)
    with patch("ticket_pr_lifecycle.subprocess.run") as mock_sub:
        result = auto_merge_pr("T001", run_dir, None)
    assert result is False
    mock_sub.assert_not_called()


def test_auto_merge_pr_skips_when_already_merged(tmp_path):
    run_dir = _make_run_dir(tmp_path, pr_number=42, pr_merged=True)
    with patch("ticket_pr_lifecycle.subprocess.run") as mock_sub:
        result = auto_merge_pr("T001", run_dir, None)
    assert result is False
    mock_sub.assert_not_called()


def test_auto_merge_pr_detects_already_merged_pr(tmp_path):
    run_dir = _make_run_dir(tmp_path, pr_number=42)
    mock_view = MagicMock(returncode=0, stdout=json.dumps({"state": "MERGED", "mergeable": "MERGEABLE"}))
    with patch("ticket_pr_lifecycle.subprocess.run", return_value=mock_view):
        result = auto_merge_pr("T001", run_dir, None)
    assert result is True
    saved = json.loads((run_dir / "state.json").read_text(encoding="utf-8"))
    assert saved.get("pr_merged") is True
    assert saved.get("daemon_archived") is True


def test_auto_merge_pr_skips_closed_pr(tmp_path):
    run_dir = _make_run_dir(tmp_path, pr_number=42)
    mock_view = MagicMock(returncode=0, stdout=json.dumps({"state": "CLOSED", "mergeable": "MERGEABLE"}))
    with patch("ticket_pr_lifecycle.subprocess.run", return_value=mock_view):
        result = auto_merge_pr("T001", run_dir, None)
    assert result is False


def test_auto_merge_pr_skips_conflicting_pr(tmp_path):
    run_dir = _make_run_dir(tmp_path, pr_number=42)
    mock_view = MagicMock(returncode=0, stdout=json.dumps({"state": "OPEN", "mergeable": "CONFLICTING"}))
    with patch("ticket_pr_lifecycle.subprocess.run", return_value=mock_view):
        result = auto_merge_pr("T001", run_dir, None)
    assert result is False
    saved = json.loads((run_dir / "state.json").read_text(encoding="utf-8"))
    assert saved.get("pr_merged") is None


def test_auto_merge_pr_returns_false_when_gh_merge_fails(tmp_path):
    run_dir = _make_run_dir(tmp_path, pr_number=42)
    mock_view = MagicMock(returncode=0, stdout=json.dumps({"state": "OPEN", "mergeable": "MERGEABLE"}))
    mock_merge = MagicMock(returncode=1, stdout="", stderr="merge blocked by required review")
    with patch("ticket_pr_lifecycle.subprocess.run", side_effect=[mock_view, mock_merge]):
        result = auto_merge_pr("T001", run_dir, None)
    assert result is False
    saved = json.loads((run_dir / "state.json").read_text(encoding="utf-8"))
    assert saved.get("pr_merged") is None
    assert saved.get("daemon_archived") is None


def test_auto_merge_pr_returns_false_when_gh_not_found(tmp_path):
    run_dir = _make_run_dir(tmp_path, pr_number=42)
    with patch("ticket_pr_lifecycle.subprocess.run", side_effect=FileNotFoundError):
        result = auto_merge_pr("T001", run_dir, None)
    assert result is False


def test_auto_merge_pr_passes_repo_flag(tmp_path):
    run_dir = _make_run_dir(tmp_path, pr_number=42)
    mock_view = MagicMock(returncode=0, stdout=json.dumps({"state": "OPEN", "mergeable": "MERGEABLE"}))
    mock_merge = MagicMock(returncode=0, stdout="", stderr="")
    with patch("ticket_pr_lifecycle.subprocess.run", side_effect=[mock_view, mock_merge]) as mock_sub:
        auto_merge_pr("T001", run_dir, "owner/repo")
    view_cmd = mock_sub.call_args_list[0][0][0]
    merge_cmd = mock_sub.call_args_list[1][0][0]
    assert "--repo" in view_cmd and "owner/repo" in view_cmd
    assert "--repo" in merge_cmd and "owner/repo" in merge_cmd


def test_auto_merge_pr_does_not_mark_finalized_on_gh_view_failure(tmp_path):
    run_dir = _make_run_dir(tmp_path, pr_number=42)
    mock_view = MagicMock(returncode=1, stdout="", stderr="gh API error")
    with patch("ticket_pr_lifecycle.subprocess.run", return_value=mock_view):
        result = auto_merge_pr("T001", run_dir, None)
    assert result is False
    saved = json.loads((run_dir / "state.json").read_text(encoding="utf-8"))
    assert saved.get("pr_merged") is None


# ── handle_test_complete conflict detection (T162) ────────────────────────────

def test_handle_test_complete_calls_detect_conflict_on_failed_merge(tmp_path):
    run_dir = _make_run_dir(tmp_path, pr_number=42)
    with patch("ticket_pr_lifecycle._checkpoint_and_push_before_pr", return_value=True), \
         patch("ticket_pr_lifecycle.create_or_update_pr"), \
         patch("ticket_pr_lifecycle.auto_merge_pr", return_value=False), \
         patch("ticket_pr_lifecycle.detect_pr_conflict") as mock_detect, \
         patch("ticket_pr_lifecycle.check_and_close_issue") as mock_close:
        handle_test_complete("T001", run_dir, None)
    mock_detect.assert_called_once_with("T001", 42, run_dir, None)
    mock_close.assert_not_called()


def test_handle_test_complete_transitions_to_conflict_state(tmp_path):
    run_dir = _make_run_dir(tmp_path, pr_number=42)
    with patch("ticket_pr_lifecycle._checkpoint_and_push_before_pr", return_value=True), \
         patch("ticket_pr_lifecycle.create_or_update_pr"), \
         patch("ticket_pr_lifecycle.auto_merge_pr", return_value=False), \
         patch("ticket_pr_lifecycle.detect_pr_conflict", return_value=True), \
         patch("ticket_pr_lifecycle.check_and_close_issue") as mock_close:
        handle_test_complete("T001", run_dir, None)
    mock_close.assert_not_called()


def test_handle_test_complete_no_conflict_detection_without_pr_number(tmp_path):
    run_dir = _make_run_dir(tmp_path)  # no pr_number in state
    with patch("ticket_pr_lifecycle._checkpoint_and_push_before_pr", return_value=True), \
         patch("ticket_pr_lifecycle.create_or_update_pr"), \
         patch("ticket_pr_lifecycle.auto_merge_pr", return_value=False), \
         patch("ticket_pr_lifecycle.detect_pr_conflict") as mock_detect, \
         patch("ticket_pr_lifecycle.check_and_close_issue") as mock_close:
        handle_test_complete("T001", run_dir, None)
    mock_detect.assert_not_called()
    mock_close.assert_not_called()


# ── create_or_update_pr branch prefix fallback (T162) ────────────────────────

def test_create_or_update_pr_finds_pr_by_ticket_prefix_fallback(tmp_path):
    run_dir = _make_run_dir(tmp_path)  # no pr_number, branch is ticket/T001-my-feature
    mock_branch_list = MagicMock(returncode=0, stdout="[]")
    mock_prefix_list = MagicMock(
        returncode=0,
        stdout=json.dumps([{"number": 77, "head": {"ref": "ticket/T001-renamed-title"}}]),
    )
    mock_edit = MagicMock(returncode=0, stdout="")
    with patch("ticket_pr_lifecycle._resolve_owner_repo", return_value="owner/repo"), \
         patch("ticket_pr_lifecycle.subprocess.run", side_effect=[mock_branch_list, mock_prefix_list, mock_edit]) as mock_sub:
        create_or_update_pr("T001", run_dir, "owner/repo")
    saved = json.loads((run_dir / "state.json").read_text(encoding="utf-8"))
    assert saved["pr_number"] == 77
    edit_cmd = mock_sub.call_args_list[2][0][0]
    assert "pulls/77" in edit_cmd[2]
    assert "PATCH" in edit_cmd
