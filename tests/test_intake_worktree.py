"""Tests for the ephemeral intake flow (replaces persistent `_intake` worktree).

The daemon no longer maintains a long-lived `_intake` worktree. Instead, each
new GitHub issue is ingested by:

1. fetching ``origin/main`` (pure ref op),
2. creating the ticket branch directly from ``origin/main``,
3. adding ``worktrees/TXXX`` on that branch,
4. running ``run_issue_intake.py`` inside the new worktree.

On failure the just-created branch and worktree are cleaned up so the next
daemon cycle can retry from scratch.
"""

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
from worktree_manager import (
    cleanup_failed_intake,
    create_ticket_branch_and_worktree,
    fetch_origin_main,
)


# ── helpers ───────────────────────────────────────────────────────────────────

def _write_state_in_runs(runs_dir: Path, ticket_id: str, state: str) -> None:
    run_dir = runs_dir / ticket_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "state.json").write_text(
        json.dumps({"ticket_id": ticket_id, "state": state, "updated_at": "2026-01-01T00:00:00Z"}),
        encoding="utf-8",
    )


def _write_state_in_worktree(worktree: Path, ticket_id: str, state: str) -> None:
    run_dir = worktree / "runs" / ticket_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "state.json").write_text(
        json.dumps({"ticket_id": ticket_id, "state": state, "updated_at": "2026-01-01T00:00:00Z"}),
        encoding="utf-8",
    )


def _cp(returncode=0, stdout="", stderr=""):
    return MagicMock(returncode=returncode, stdout=stdout, stderr=stderr)


# ── fetch_origin_main ─────────────────────────────────────────────────────────

def test_fetch_origin_main_success(tmp_path):
    with patch("worktree_manager.subprocess.run", return_value=_cp()) as mock_sub:
        ok, msg = fetch_origin_main(repo_root=tmp_path)
    assert ok is True
    cmd, kwargs = mock_sub.call_args[0][0], mock_sub.call_args[1]
    assert cmd == ["git", "fetch", "origin", "main"]
    assert kwargs["cwd"] == str(tmp_path)


def test_fetch_origin_main_failure_returns_false_with_stderr(tmp_path):
    with patch("worktree_manager.subprocess.run", return_value=_cp(returncode=1, stderr="boom")):
        ok, msg = fetch_origin_main(repo_root=tmp_path)
    assert ok is False
    assert "boom" in msg


# ── create_ticket_branch_and_worktree ────────────────────────────────────────

def test_create_ticket_branch_and_worktree_happy_path(tmp_path):
    worktrees_dir = tmp_path / "worktrees"
    branch = "ticket/T001-feat"

    def fake_run(cmd, **kwargs):
        if cmd[:2] == ["git", "show-ref"]:
            return _cp(returncode=1)  # branch doesn't exist yet
        if cmd[:2] == ["git", "branch"] and "origin/main" in cmd:
            return _cp()
        if cmd[:3] == ["git", "worktree", "add"]:
            return _cp()
        return _cp(returncode=2, stderr=f"unexpected {cmd}")

    with patch("worktree_manager.subprocess.run", side_effect=fake_run) as mock_sub:
        ok, msg = create_ticket_branch_and_worktree("T001", branch, worktrees_dir, repo_root=tmp_path)

    assert ok is True
    assert "branch+worktree created" in msg
    calls = [c[0][0] for c in mock_sub.call_args_list]
    assert ["git", "branch", branch, "origin/main"] in calls
    assert any(c[:3] == ["git", "worktree", "add"] for c in calls)


def test_create_ticket_branch_and_worktree_refuses_if_worktree_exists(tmp_path):
    worktrees_dir = tmp_path / "worktrees"
    (worktrees_dir / "T001").mkdir(parents=True)
    ok, msg = create_ticket_branch_and_worktree(
        "T001", "ticket/T001-feat", worktrees_dir, repo_root=tmp_path,
    )
    assert ok is False
    assert "worktree already exists" in msg


def test_create_ticket_branch_and_worktree_recovers_orphan_branch(tmp_path):
    """If the branch exists locally and no worktree uses it, adopt it (recovery path)."""
    worktrees_dir = tmp_path / "worktrees"
    branch = "ticket/T001-feat"

    def fake_run(cmd, **kwargs):
        if cmd[:2] == ["git", "show-ref"]:
            return _cp(returncode=0)  # branch exists
        if cmd[:3] == ["git", "worktree", "list"]:
            return _cp(stdout="worktree /repo\nHEAD abc\nbranch refs/heads/main\n\n")
        if cmd[:3] == ["git", "worktree", "add"]:
            return _cp()
        return _cp(returncode=2, stderr=f"unexpected {cmd}")

    with patch("worktree_manager.subprocess.run", side_effect=fake_run) as mock_sub:
        ok, msg = create_ticket_branch_and_worktree(
            "T001", branch, worktrees_dir, repo_root=tmp_path,
        )

    assert ok is True
    assert "recovered orphan branch" in msg
    calls = [c[0][0] for c in mock_sub.call_args_list]
    # We must NOT recreate the branch in recovery mode
    assert not any(c[:2] == ["git", "branch"] and "origin/main" in c for c in calls)
    # We must attach a worktree to the existing branch
    assert any(c[:3] == ["git", "worktree", "add"] for c in calls)


def test_create_ticket_branch_and_worktree_refuses_if_branch_in_other_worktree(tmp_path):
    """If the branch is already checked out in another worktree, refuse — real conflict."""
    worktrees_dir = tmp_path / "worktrees"
    branch = "ticket/T001-feat"

    def fake_run(cmd, **kwargs):
        if cmd[:2] == ["git", "show-ref"]:
            return _cp(returncode=0)  # branch exists
        if cmd[:3] == ["git", "worktree", "list"]:
            return _cp(stdout=f"worktree /repo\nHEAD abc\nbranch refs/heads/{branch}\n\n")
        return _cp(returncode=2, stderr=f"unexpected {cmd}")

    with patch("worktree_manager.subprocess.run", side_effect=fake_run):
        ok, msg = create_ticket_branch_and_worktree(
            "T001", branch, worktrees_dir, repo_root=tmp_path,
        )

    assert ok is False
    assert "already checked out in another worktree" in msg


def test_create_ticket_branch_and_worktree_rolls_back_branch_when_worktree_add_fails(tmp_path):
    worktrees_dir = tmp_path / "worktrees"
    branch = "ticket/T001-feat"
    calls: list[list[str]] = []

    def fake_run(cmd, **kwargs):
        calls.append(list(cmd))
        if cmd[:2] == ["git", "show-ref"]:
            return _cp(returncode=1)
        if cmd[:2] == ["git", "branch"] and "origin/main" in cmd:
            return _cp()
        if cmd[:3] == ["git", "worktree", "add"]:
            return _cp(returncode=1, stderr="cannot add worktree")
        if cmd[:3] == ["git", "branch", "-D"]:
            return _cp()
        return _cp(returncode=2, stderr=f"unexpected {cmd}")

    with patch("worktree_manager.subprocess.run", side_effect=fake_run):
        ok, msg = create_ticket_branch_and_worktree("T001", branch, worktrees_dir, repo_root=tmp_path)

    assert ok is False
    assert "worktree add failed" in msg
    # rollback step must have run
    assert ["git", "branch", "-D", branch] in calls


# ── cleanup_failed_intake ─────────────────────────────────────────────────────

def test_cleanup_failed_intake_removes_worktree_and_deletes_branch(tmp_path):
    worktrees_dir = tmp_path / "worktrees"
    worktree_path = worktrees_dir / "T001"
    worktree_path.mkdir(parents=True)
    branch = "ticket/T001-feat"

    def fake_run(cmd, **kwargs):
        if cmd[:3] == ["git", "worktree", "remove"]:
            return _cp()
        if cmd[:2] == ["git", "show-ref"]:
            return _cp(returncode=0)  # branch exists
        if cmd[:3] == ["git", "branch", "-D"]:
            return _cp()
        return _cp()

    with patch("worktree_manager.subprocess.run", side_effect=fake_run) as mock_sub:
        msgs = cleanup_failed_intake("T001", branch, worktrees_dir, repo_root=tmp_path)

    calls = [c[0][0] for c in mock_sub.call_args_list]
    assert any(c[:3] == ["git", "worktree", "remove"] for c in calls)
    assert ["git", "branch", "-D", branch] in calls
    assert any("removed worktree" in m for m in msgs)
    assert any("deleted branch" in m for m in msgs)


def test_cleanup_failed_intake_handles_missing_worktree_and_branch(tmp_path):
    worktrees_dir = tmp_path / "worktrees"
    worktrees_dir.mkdir()
    # neither worktree nor branch exists
    with patch("worktree_manager.subprocess.run", return_value=_cp(returncode=1)) as mock_sub:
        msgs = cleanup_failed_intake("T001", "ticket/T001-feat", worktrees_dir, repo_root=tmp_path)

    # no git worktree remove and no git branch -D — both gated by existence checks
    calls = [c[0][0] for c in mock_sub.call_args_list]
    for c in calls:
        assert c[:3] != ["git", "worktree", "remove"]
        assert c[:3] != ["git", "branch", "-D"]
    assert msgs == []


# ── call_issue_intake passes cwd ──────────────────────────────────────────────

def test_call_issue_intake_passes_cwd_to_subprocess(tmp_path):
    with patch("run_daemon.subprocess.run", return_value=_cp()) as mock_sub:
        call_issue_intake(42, "T001", "feat", None, cwd="/some/worktree/path")
    assert mock_sub.call_args[1].get("cwd") == "/some/worktree/path"


def test_call_issue_intake_cwd_none_by_default():
    with patch("run_daemon.subprocess.run", return_value=_cp()) as mock_sub:
        call_issue_intake(42, "T001", "feat", None)
    assert mock_sub.call_args[1].get("cwd") is None


# ── scan_tickets — no more _intake tier ──────────────────────────────────────

def test_scan_tickets_only_uses_worktrees_and_main_runs(tmp_path):
    runs = tmp_path / "runs"
    runs.mkdir()
    worktrees_dir = tmp_path / "worktrees"

    # Plain runs/ entry
    _write_state_in_runs(runs, "T001", "INIT")
    # TXXX worktree entry
    _write_state_in_worktree(worktrees_dir / "T002", "T002", "PLAN_APPROVED")
    # Any stray _intake subdirectory must now be ignored
    legacy_intake = worktrees_dir / "_intake" / "runs" / "T999"
    legacy_intake.mkdir(parents=True)
    (legacy_intake / "state.json").write_text(
        json.dumps({"ticket_id": "T999", "state": "INIT"}), encoding="utf-8"
    )

    result = dict(scan_tickets(runs, worktrees_dir=worktrees_dir))
    assert result == {"T001": "INIT", "T002": "PLAN_APPROVED"}
    assert "T999" not in result


# ── _get_run_dir — no _intake fallback ────────────────────────────────────────

def test_get_run_dir_prefers_txxx_worktree(tmp_path):
    runs = tmp_path / "runs"
    runs.mkdir()
    worktrees_dir = tmp_path / "worktrees"
    txxx_run_dir = worktrees_dir / "T001" / "runs" / "T001"
    txxx_run_dir.mkdir(parents=True)
    assert _get_run_dir("T001", runs, worktrees_dir=worktrees_dir) == txxx_run_dir


def test_get_run_dir_falls_back_to_main_runs(tmp_path):
    runs = tmp_path / "runs"
    runs.mkdir()
    worktrees_dir = tmp_path / "worktrees"
    assert _get_run_dir("T001", runs, worktrees_dir=worktrees_dir) == runs / "T001"


def test_get_run_dir_ignores_intake_subdir(tmp_path):
    runs = tmp_path / "runs"
    runs.mkdir()
    worktrees_dir = tmp_path / "worktrees"
    # Even if a stale _intake/runs/T001/ exists, it must not be used
    legacy = worktrees_dir / "_intake" / "runs" / "T001"
    legacy.mkdir(parents=True)
    assert _get_run_dir("T001", runs, worktrees_dir=worktrees_dir) == runs / "T001"


# ── poll_github_issues — ephemeral intake flow ────────────────────────────────

def test_poll_github_issues_fetches_main_creates_branch_and_worktree_and_runs_intake(tmp_path):
    runs = tmp_path / "runs"
    runs.mkdir()
    worktrees_dir = tmp_path / "worktrees"
    issues = [{"number": 42, "title": "New feature"}]
    worktree_path = worktrees_dir / "T001"

    with patch("run_daemon.fetch_ready_issues", return_value=issues), \
         patch("run_daemon.extract_ticket_id_from_title", return_value="T001"), \
         patch("run_daemon.next_ticket_id", return_value="T001"), \
         patch("run_daemon.slugify_title", return_value="new-feature"), \
         patch("run_daemon.fetch_origin_main", return_value=(True, "fetched origin/main")) as mock_fetch, \
         patch(
             "run_daemon.create_ticket_branch_and_worktree",
             return_value=(True, f"branch+worktree created at {worktree_path}"),
         ) as mock_create, \
         patch("run_daemon.call_issue_intake", return_value=True) as mock_intake, \
         patch("run_daemon.cleanup_failed_intake") as mock_cleanup:
        poll_github_issues(runs, "ai-ready", None, worktrees_dir=worktrees_dir, state_dir=tmp_path)

    mock_fetch.assert_called_once()
    mock_create.assert_called_once()
    create_args = mock_create.call_args
    assert create_args[0][0] == "T001"
    assert create_args[0][1].startswith("ticket/T001-")
    mock_intake.assert_called_once()
    intake_kwargs = mock_intake.call_args[1]
    assert intake_kwargs.get("cwd") == str(worktree_path)
    mock_cleanup.assert_not_called()


def test_poll_github_issues_skips_when_worktrees_dir_none(tmp_path):
    runs = tmp_path / "runs"
    runs.mkdir()
    issues = [{"number": 42, "title": "New feature"}]
    with patch("run_daemon.fetch_ready_issues", return_value=issues), \
         patch("run_daemon.extract_ticket_id_from_title", return_value="T001"), \
         patch("run_daemon.next_ticket_id", return_value="T001"), \
         patch("run_daemon.slugify_title", return_value="new-feature"), \
         patch("run_daemon.call_issue_intake") as mock_intake, \
         patch("run_daemon.fetch_origin_main") as mock_fetch:
        poll_github_issues(runs, "ai-ready", None, worktrees_dir=None, state_dir=tmp_path)

    mock_fetch.assert_not_called()
    mock_intake.assert_not_called()


def test_poll_github_issues_aborts_on_fetch_failure(tmp_path):
    runs = tmp_path / "runs"
    runs.mkdir()
    worktrees_dir = tmp_path / "worktrees"
    issues = [{"number": 42, "title": "New feature"}]

    with patch("run_daemon.fetch_ready_issues", return_value=issues), \
         patch("run_daemon.extract_ticket_id_from_title", return_value="T001"), \
         patch("run_daemon.next_ticket_id", return_value="T001"), \
         patch("run_daemon.slugify_title", return_value="new-feature"), \
         patch("run_daemon.fetch_origin_main", return_value=(False, "git fetch failed: network down")), \
         patch("run_daemon.create_ticket_branch_and_worktree") as mock_create, \
         patch("run_daemon.call_issue_intake") as mock_intake:
        poll_github_issues(runs, "ai-ready", None, worktrees_dir=worktrees_dir, state_dir=tmp_path)

    mock_create.assert_not_called()
    mock_intake.assert_not_called()


def test_poll_github_issues_rolls_back_when_intake_fails(tmp_path):
    runs = tmp_path / "runs"
    runs.mkdir()
    worktrees_dir = tmp_path / "worktrees"
    worktree_path = worktrees_dir / "T001"
    issues = [{"number": 42, "title": "New feature"}]

    with patch("run_daemon.fetch_ready_issues", return_value=issues), \
         patch("run_daemon.extract_ticket_id_from_title", return_value="T001"), \
         patch("run_daemon.next_ticket_id", return_value="T001"), \
         patch("run_daemon.slugify_title", return_value="new-feature"), \
         patch("run_daemon.fetch_origin_main", return_value=(True, "fetched origin/main")), \
         patch(
             "run_daemon.create_ticket_branch_and_worktree",
             return_value=(True, f"branch+worktree created at {worktree_path}"),
         ), \
         patch("run_daemon.call_issue_intake", return_value=False), \
         patch("run_daemon.cleanup_failed_intake", return_value=["removed worktree", "deleted branch"]) as mock_cleanup:
        poll_github_issues(runs, "ai-ready", None, worktrees_dir=worktrees_dir, state_dir=tmp_path)

    mock_cleanup.assert_called_once()
    cleanup_args = mock_cleanup.call_args
    assert cleanup_args[0][0] == "T001"
    assert cleanup_args[0][1].startswith("ticket/T001-")


def test_poll_github_issues_aborts_when_branch_or_worktree_creation_fails(tmp_path):
    runs = tmp_path / "runs"
    runs.mkdir()
    worktrees_dir = tmp_path / "worktrees"
    issues = [{"number": 42, "title": "New feature"}]

    with patch("run_daemon.fetch_ready_issues", return_value=issues), \
         patch("run_daemon.extract_ticket_id_from_title", return_value="T001"), \
         patch("run_daemon.next_ticket_id", return_value="T001"), \
         patch("run_daemon.slugify_title", return_value="new-feature"), \
         patch("run_daemon.fetch_origin_main", return_value=(True, "fetched origin/main")), \
         patch(
             "run_daemon.create_ticket_branch_and_worktree",
             return_value=(False, "branch already exists: ticket/T001-new-feature — refusing"),
         ), \
         patch("run_daemon.call_issue_intake") as mock_intake, \
         patch("run_daemon.cleanup_failed_intake") as mock_cleanup:
        poll_github_issues(runs, "ai-ready", None, worktrees_dir=worktrees_dir, state_dir=tmp_path)

    mock_intake.assert_not_called()
    mock_cleanup.assert_not_called()


# ── _load_project_map / poll_project_map — no _intake lookups ────────────────

def test_load_project_map_reads_runs_dir_only(tmp_path):
    runs = tmp_path / "runs"
    runs.mkdir()
    (runs / ".project-map.json").write_text(
        json.dumps({"next_recommended": "T003"}), encoding="utf-8"
    )
    worktrees_dir = tmp_path / "worktrees"
    # any stale _intake map must not be considered anymore
    intake_map = worktrees_dir / "_intake" / "runs" / ".project-map.json"
    intake_map.parent.mkdir(parents=True, exist_ok=True)
    intake_map.write_text(json.dumps({"next_recommended": "T999"}), encoding="utf-8")

    assert _load_project_map(runs, worktrees_dir=worktrees_dir) == {"next_recommended": "T003"}


def test_load_project_map_returns_none_when_no_map(tmp_path):
    runs = tmp_path / "runs"
    runs.mkdir()
    assert _load_project_map(runs) is None


def test_poll_project_map_uses_runs_dir(tmp_path):
    runs = tmp_path / "runs"
    runs.mkdir()
    worktrees_dir = tmp_path / "worktrees"
    # any stale _intake/runs must be ignored
    (worktrees_dir / "_intake" / "runs").mkdir(parents=True)

    with patch("run_daemon.subprocess.run", return_value=_cp()) as mock_sub:
        poll_project_map(runs, None, worktrees_dir=worktrees_dir)

    cmd = mock_sub.call_args[0][0]
    assert "--runs-dir" in cmd
    assert cmd[cmd.index("--runs-dir") + 1] == str(runs)
