"""Tests for T024 — daemon GitHub issue polling."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "tools" / "agent_runner"))

from run_daemon import (
    call_issue_intake,
    fetch_ready_issues,
    load_issue_index,
    main,
    next_ticket_id,
    poll_github_issues,
    save_issue_index,
    slugify_title,
)


# ── helpers ───────────────────────────────────────────────────────────────────

def _make_runs(tmp_path: Path, ticket_ids: list[str] = ()) -> Path:
    runs = tmp_path / "runs"
    runs.mkdir()
    for tid in ticket_ids:
        (runs / tid).mkdir()
    return runs


# ── load_issue_index ──────────────────────────────────────────────────────────

def test_load_issue_index_returns_empty_when_file_absent(tmp_path):
    runs = _make_runs(tmp_path)
    assert load_issue_index(runs) == {}


def test_load_issue_index_reads_existing_file(tmp_path):
    runs = _make_runs(tmp_path)
    (runs / ".issue-intake.json").write_text(
        json.dumps({"42": "T025"}), encoding="utf-8"
    )
    assert load_issue_index(runs) == {"42": "T025"}


def test_load_issue_index_returns_empty_on_corrupted_file(tmp_path):
    runs = _make_runs(tmp_path)
    (runs / ".issue-intake.json").write_text("not json", encoding="utf-8")
    assert load_issue_index(runs) == {}


# ── save_issue_index ──────────────────────────────────────────────────────────

def test_save_issue_index_writes_file(tmp_path):
    runs = _make_runs(tmp_path)
    save_issue_index(runs, {"10": "T001"})
    data = json.loads((runs / ".issue-intake.json").read_text(encoding="utf-8"))
    assert data == {"10": "T001"}


def test_save_issue_index_roundtrip(tmp_path):
    runs = _make_runs(tmp_path)
    original = {"1": "T001", "2": "T002", "99": "T100"}
    save_issue_index(runs, original)
    assert load_issue_index(runs) == original


def test_save_issue_index_leaves_no_tmp_file(tmp_path):
    runs = _make_runs(tmp_path)
    save_issue_index(runs, {"1": "T001"})
    assert not (runs / ".issue-intake.tmp").exists()


# ── next_ticket_id ────────────────────────────────────────────────────────────

def test_next_ticket_id_with_no_runs(tmp_path):
    runs = _make_runs(tmp_path)
    assert next_ticket_id(runs) == "T001"


def test_next_ticket_id_increments_from_max(tmp_path):
    runs = _make_runs(tmp_path, ["T001", "T002", "T010"])
    assert next_ticket_id(runs) == "T011"


def test_next_ticket_id_zero_pads_to_three_digits(tmp_path):
    runs = _make_runs(tmp_path, ["T009"])
    assert next_ticket_id(runs) == "T010"


def test_next_ticket_id_ignores_non_ticket_dirs(tmp_path):
    runs = _make_runs(tmp_path, ["T003"])
    (runs / "some-other-dir").mkdir()
    (runs / ".hidden").mkdir()
    assert next_ticket_id(runs) == "T004"


def test_next_ticket_id_t034_gives_t035(tmp_path):
    runs = _make_runs(tmp_path, [f"T{i:03d}" for i in range(1, 35)])
    assert next_ticket_id(runs) == "T035"


def test_next_ticket_id_t099_gives_t100(tmp_path):
    runs = _make_runs(tmp_path, ["T099"])
    assert next_ticket_id(runs) == "T100"


def test_next_ticket_id_lexicographic_trap(tmp_path):
    # T1, T10, T100 — numeric max is 100, next must be T101 not T11
    runs = _make_runs(tmp_path, ["T001", "T010", "T100"])
    assert next_ticket_id(runs) == "T101"


def test_next_ticket_id_with_gaps(tmp_path):
    runs = _make_runs(tmp_path, ["T001", "T005", "T020"])
    assert next_ticket_id(runs) == "T021"


def test_next_ticket_id_respects_reserved_set(tmp_path):
    runs = _make_runs(tmp_path, ["T003"])
    assert next_ticket_id(runs, reserved={"T010", "T020"}) == "T021"


def test_next_ticket_id_reserved_set_only(tmp_path):
    runs = _make_runs(tmp_path)
    assert next_ticket_id(runs, reserved={"T034"}) == "T035"


# ── slugify_title ─────────────────────────────────────────────────────────────

def test_slugify_title_basic():
    assert slugify_title("Add GitHub polling") == "add-github-polling"


def test_slugify_title_special_chars():
    assert slugify_title("Fix: crash on empty input!") == "fix-crash-on-empty-input"


def test_slugify_title_truncates_at_50_chars():
    long_title = "a" * 60
    result = slugify_title(long_title)
    assert len(result) <= 50


def test_slugify_title_empty_string_falls_back():
    assert slugify_title("") == "issue"


def test_slugify_title_only_special_chars_falls_back():
    assert slugify_title("!!!") == "issue"


def test_slugify_title_no_trailing_hyphens():
    result = slugify_title("hello world   ")
    assert not result.endswith("-")


# ── fetch_ready_issues ────────────────────────────────────────────────────────

def test_fetch_ready_issues_returns_parsed_issues(tmp_path):
    payload = json.dumps([{"number": 42, "title": "My feature"}])
    mock_result = MagicMock(returncode=0, stdout=payload)
    with patch("run_daemon.subprocess.run", return_value=mock_result):
        result = fetch_ready_issues("ai-ready", None)
    assert result == [{"number": 42, "title": "My feature"}]


def test_fetch_ready_issues_passes_repo_flag():
    mock_result = MagicMock(returncode=0, stdout="[]")
    with patch("run_daemon.subprocess.run", return_value=mock_result) as mock_sub:
        fetch_ready_issues("ai-ready", "owner/repo")
    cmd = mock_sub.call_args[0][0]
    assert "--repo" in cmd
    assert "owner/repo" in cmd


def test_fetch_ready_issues_omits_repo_flag_when_none():
    mock_result = MagicMock(returncode=0, stdout="[]")
    with patch("run_daemon.subprocess.run", return_value=mock_result) as mock_sub:
        fetch_ready_issues("ai-ready", None)
    cmd = mock_sub.call_args[0][0]
    assert "--repo" not in cmd


def test_fetch_ready_issues_returns_empty_on_gh_failure():
    mock_result = MagicMock(returncode=1, stdout="", stderr="not logged in")
    with patch("run_daemon.subprocess.run", return_value=mock_result):
        result = fetch_ready_issues("ai-ready", None)
    assert result == []


def test_fetch_ready_issues_returns_empty_when_gh_not_found():
    with patch("run_daemon.subprocess.run", side_effect=FileNotFoundError):
        result = fetch_ready_issues("ai-ready", None)
    assert result == []


def test_fetch_ready_issues_returns_empty_on_empty_output():
    mock_result = MagicMock(returncode=0, stdout="")
    with patch("run_daemon.subprocess.run", return_value=mock_result):
        result = fetch_ready_issues("ai-ready", None)
    assert result == []


def test_fetch_ready_issues_passes_label_flag():
    mock_result = MagicMock(returncode=0, stdout="[]")
    with patch("run_daemon.subprocess.run", return_value=mock_result) as mock_sub:
        fetch_ready_issues("my-label", None)
    cmd = mock_sub.call_args[0][0]
    assert "--label" in cmd
    assert "my-label" in cmd


# ── call_issue_intake ─────────────────────────────────────────────────────────

def test_call_issue_intake_returns_true_on_success():
    mock_result = MagicMock(returncode=0, stdout="", stderr="")
    with patch("run_daemon.subprocess.run", return_value=mock_result):
        assert call_issue_intake(42, "T025", "my-feature", None) is True


def test_call_issue_intake_returns_false_on_failure():
    mock_result = MagicMock(returncode=2, stdout="", stderr="error")
    with patch("run_daemon.subprocess.run", return_value=mock_result):
        assert call_issue_intake(42, "T025", "my-feature", None) is False


def test_call_issue_intake_passes_correct_args():
    mock_result = MagicMock(returncode=0, stdout="", stderr="")
    with patch("run_daemon.subprocess.run", return_value=mock_result) as mock_sub:
        call_issue_intake(42, "T025", "my-feature", None)
    cmd = mock_sub.call_args[0][0]
    assert "--issue" in cmd
    assert "42" in cmd
    assert "--ticket-id" in cmd
    assert "T025" in cmd
    assert "--branch-slug" in cmd
    assert "my-feature" in cmd


def test_call_issue_intake_passes_repo_when_set():
    mock_result = MagicMock(returncode=0, stdout="", stderr="")
    with patch("run_daemon.subprocess.run", return_value=mock_result) as mock_sub:
        call_issue_intake(42, "T025", "my-feature", "owner/repo")
    cmd = mock_sub.call_args[0][0]
    assert "--repo" in cmd
    assert "owner/repo" in cmd


def test_call_issue_intake_passes_push_flag_when_set():
    mock_result = MagicMock(returncode=0, stdout="", stderr="")
    with patch("run_daemon.subprocess.run", return_value=mock_result) as mock_sub:
        call_issue_intake(42, "T025", "my-feature", None, push=True)
    cmd = mock_sub.call_args[0][0]
    assert "--push" in cmd


def test_call_issue_intake_omits_push_flag_by_default():
    mock_result = MagicMock(returncode=0, stdout="", stderr="")
    with patch("run_daemon.subprocess.run", return_value=mock_result) as mock_sub:
        call_issue_intake(42, "T025", "my-feature", None)
    cmd = mock_sub.call_args[0][0]
    assert "--push" not in cmd


# ── poll_github_issues ────────────────────────────────────────────────────────

def _git_ok(*args, **kwargs):
    """Return success for git checkout/pull preflight calls in poll_github_issues."""
    return MagicMock(returncode=0, stdout="", stderr="")


def test_poll_github_issues_ingests_new_issue(tmp_path):
    runs = _make_runs(tmp_path)
    issues = [{"number": 42, "title": "Add feature"}]

    with patch("run_daemon.fetch_ready_issues", return_value=issues), \
         patch("run_daemon.call_issue_intake", return_value=True), \
         patch("run_daemon._commit_after_intake"), \
         patch("run_daemon.subprocess.run", side_effect=_git_ok):
        poll_github_issues(runs, "ai-ready", None)

    index = load_issue_index(runs)
    assert "42" in index
    assert index["42"] == "T001"


def test_poll_github_issues_skips_already_ingested(tmp_path, capsys):
    runs = _make_runs(tmp_path, ["T001"])
    save_issue_index(runs, {"42": "T001"})
    issues = [{"number": 42, "title": "Add feature"}]

    with patch("run_daemon.fetch_ready_issues", return_value=issues):
        with patch("run_daemon.call_issue_intake") as mock_intake:
            poll_github_issues(runs, "ai-ready", None)

    mock_intake.assert_not_called()
    assert "skipping" in capsys.readouterr().out


def test_poll_github_issues_does_not_update_index_on_intake_failure(tmp_path):
    runs = _make_runs(tmp_path)
    issues = [{"number": 42, "title": "Add feature"}]

    with patch("run_daemon.fetch_ready_issues", return_value=issues):
        with patch("run_daemon.call_issue_intake", return_value=False):
            poll_github_issues(runs, "ai-ready", None)

    index = load_issue_index(runs)
    assert "42" not in index


def test_poll_github_issues_logs_retry_on_intake_failure(tmp_path, capsys):
    runs = _make_runs(tmp_path)
    issues = [{"number": 7, "title": "Broken"}]

    with patch("run_daemon.fetch_ready_issues", return_value=issues), \
         patch("run_daemon.call_issue_intake", return_value=False), \
         patch("run_daemon.subprocess.run", side_effect=_git_ok):
        poll_github_issues(runs, "ai-ready", None)

    assert "retry" in capsys.readouterr().out


def test_poll_github_issues_no_issues_found_logs(tmp_path, capsys):
    runs = _make_runs(tmp_path)

    with patch("run_daemon.fetch_ready_issues", return_value=[]):
        poll_github_issues(runs, "ai-ready", None)

    assert "no issues found" in capsys.readouterr().out


def test_poll_github_issues_assigns_correct_next_ticket_id(tmp_path):
    runs = _make_runs(tmp_path, ["T001", "T002", "T003"])
    issues = [{"number": 10, "title": "Next ticket"}]

    with patch("run_daemon.fetch_ready_issues", return_value=issues), \
         patch("run_daemon.call_issue_intake", return_value=True) as mock_intake, \
         patch("run_daemon._commit_after_intake"), \
         patch("run_daemon.subprocess.run", side_effect=_git_ok):
        poll_github_issues(runs, "ai-ready", None)

    _, ticket_id, _, _ = mock_intake.call_args[0]
    assert ticket_id == "T004"


def test_poll_github_issues_multiple_issues_sequential_ids(tmp_path):
    # poll_github_issues processes one issue per daemon cycle (candidates[:1])
    runs = _make_runs(tmp_path)
    issues = [
        {"number": 1, "title": "First"},
        {"number": 2, "title": "Second"},
    ]

    with patch("run_daemon.fetch_ready_issues", return_value=issues), \
         patch("run_daemon.call_issue_intake", return_value=True), \
         patch("run_daemon._commit_after_intake"), \
         patch("run_daemon.subprocess.run", side_effect=_git_ok):
        poll_github_issues(runs, "ai-ready", None)

    index = load_issue_index(runs)
    # Only the first candidate is processed per cycle
    assert index["1"] == "T001"
    assert "2" not in index


def test_poll_github_issues_calls_commit_after_intake_on_success(tmp_path):
    runs = _make_runs(tmp_path)
    issues = [{"number": 42, "title": "Add feature"}]

    with patch("run_daemon.fetch_ready_issues", return_value=issues), \
         patch("run_daemon.call_issue_intake", return_value=True), \
         patch("run_daemon._commit_after_intake") as mock_commit, \
         patch("run_daemon.subprocess.run", side_effect=_git_ok):
        poll_github_issues(runs, "ai-ready", None)

    mock_commit.assert_called_once_with("T001", runs)


def test_poll_github_issues_does_not_call_commit_after_intake_on_failure(tmp_path):
    runs = _make_runs(tmp_path)
    issues = [{"number": 42, "title": "Add feature"}]

    with patch("run_daemon.fetch_ready_issues", return_value=issues):
        with patch("run_daemon.call_issue_intake", return_value=False):
            with patch("run_daemon._commit_after_intake") as mock_commit:
                poll_github_issues(runs, "ai-ready", None)

    mock_commit.assert_not_called()


# ── main CLI integration ──────────────────────────────────────────────────────

def test_main_poll_issues_flag_calls_poll_before_run_once(tmp_path):
    runs = tmp_path / "runs"
    runs.mkdir()

    with patch("run_daemon.poll_github_issues") as mock_poll:
        with patch("run_daemon.run_once") as mock_run:
            rc = main([
                "--exec-cmd", "test-cmd",
                "--once",
                "--poll-issues",
                "--runs-dir", str(runs),
            ])

    assert rc == 0
    mock_run.assert_called_once()
    # positional args: (runs_dir, label, repo)
    assert mock_poll.call_args[0][:3] == (runs, "ai-ready", None)


def test_main_without_poll_issues_does_not_call_poll(tmp_path):
    runs = tmp_path / "runs"
    runs.mkdir()

    with patch("run_daemon.poll_github_issues") as mock_poll:
        with patch("run_daemon.run_once"):
            main(["--exec-cmd", "test-cmd", "--once", "--runs-dir", str(runs)])

    mock_poll.assert_not_called()


def test_main_issue_label_passed_to_poll(tmp_path):
    runs = tmp_path / "runs"
    runs.mkdir()

    with patch("run_daemon.poll_github_issues") as mock_poll:
        with patch("run_daemon.run_once"):
            main([
                "--exec-cmd", "test-cmd",
                "--once",
                "--poll-issues",
                "--issue-label", "my-label",
                "--runs-dir", str(runs),
            ])

    _, label, _ = mock_poll.call_args[0]
    assert label == "my-label"


def test_main_issue_repo_passed_to_poll(tmp_path):
    runs = tmp_path / "runs"
    runs.mkdir()

    with patch("run_daemon.poll_github_issues") as mock_poll:
        with patch("run_daemon.run_once"):
            main([
                "--exec-cmd", "test-cmd",
                "--once",
                "--poll-issues",
                "--issue-repo", "owner/repo",
                "--runs-dir", str(runs),
            ])

    _, _, repo = mock_poll.call_args[0]
    assert repo == "owner/repo"


def test_main_default_issue_label_is_ai_ready(tmp_path):
    runs = tmp_path / "runs"
    runs.mkdir()

    with patch("run_daemon.poll_github_issues") as mock_poll:
        with patch("run_daemon.run_once"):
            main(["--exec-cmd", "cmd", "--once", "--poll-issues", "--runs-dir", str(runs)])

    _, label, _ = mock_poll.call_args[0]
    assert label == "ai-ready"
