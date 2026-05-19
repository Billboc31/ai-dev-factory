"""Tests for T023 — GitHub issue intake."""

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "tools" / "agent_runner"))

from run_issue_intake import (
    IntakeError,
    branch_name,
    fetch_issue,
    run_intake,
    validate_ticket_id,
)


def _cp(stdout="", stderr="", returncode=0):
    r = MagicMock()
    r.stdout = stdout
    r.stderr = stderr
    r.returncode = returncode
    return r


def _issue_json(title="Fix bug", body="Some description"):
    return json.dumps({"title": title, "body": body})


def _happy_fake_run(args):
    if args[:2] == ["git", "status"]:
        return _cp()  # clean tree
    if args[:3] == ["gh", "issue", "view"]:
        return _cp(stdout=_issue_json())
    if args[:3] == ["git", "rev-parse", "--abbrev-ref"]:
        return _cp(stdout="main\n")
    if args[:2] == ["git", "show-ref"]:
        return _cp(returncode=1)  # branch does not exist
    if args[:3] == ["git", "checkout", "-b"]:
        return _cp()
    return _cp(returncode=2, stderr=f"unexpected: {args}")


# ── validate_ticket_id ────────────────────────────────────────────────────────

def test_validate_ticket_id_valid():
    assert validate_ticket_id("T007") == "T007"
    assert validate_ticket_id("T123") == "T123"
    assert validate_ticket_id("T1234") == "T1234"


@pytest.mark.parametrize("bad", ["T1", "T", "t007", "ABC", "007", "T07"])
def test_validate_ticket_id_invalid(bad):
    with pytest.raises(IntakeError, match="invalid ticket-id"):
        validate_ticket_id(bad)


# ── branch_name ───────────────────────────────────────────────────────────────

def test_branch_name_basic():
    assert branch_name("T023", "github-issue-intake") == "ticket/T023-github-issue-intake"


def test_branch_name_slugifies():
    assert branch_name("T023", "My Feature!") == "ticket/T023-my-feature"


# ── fetch_issue ───────────────────────────────────────────────────────────────

def test_fetch_issue_success():
    with patch("run_issue_intake._run", return_value=_cp(stdout=_issue_json("Hello", "World"))):
        result = fetch_issue(42, None)
    assert result == {"title": "Hello", "body": "World"}


def test_fetch_issue_gh_failure():
    with patch("run_issue_intake._run", return_value=_cp(returncode=1, stderr="not found")):
        with pytest.raises(IntakeError, match="gh issue view failed"):
            fetch_issue(999, None)


def test_fetch_issue_auth_hint():
    with patch("run_issue_intake._run", return_value=_cp(returncode=1, stderr="authentication required")):
        with pytest.raises(IntakeError, match="gh auth login"):
            fetch_issue(1, None)


def test_fetch_issue_repo_flag_passed():
    captured = []

    def fake_run(args):
        captured.append(args)
        return _cp(stdout=_issue_json())

    with patch("run_issue_intake._run", side_effect=fake_run):
        fetch_issue(7, "owner/repo")

    assert "--repo" in captured[0]
    assert "owner/repo" in captured[0]


def test_fetch_issue_no_repo_flag_when_omitted():
    captured = []

    def fake_run(args):
        captured.append(args)
        return _cp(stdout=_issue_json())

    with patch("run_issue_intake._run", side_effect=fake_run):
        fetch_issue(7, None)

    assert "--repo" not in captured[0]


# ── run_intake happy path ─────────────────────────────────────────────────────

def test_happy_path(tmp_path):
    orig = os.getcwd()
    os.chdir(tmp_path)
    try:
        with patch("run_issue_intake._run", side_effect=_happy_fake_run):
            rc = run_intake("T099", 42, "my-feature", None)

        assert rc == 0
        assert (tmp_path / "runs" / "T099" / "ticket.md").exists()
        assert (tmp_path / "runs" / "T099" / "state.json").exists()
        # intake must not produce runtime.log — that file is owned by run_ticket.py
        assert not (tmp_path / "runs" / "T099" / "runtime.log").exists()
    finally:
        os.chdir(orig)


def test_skip_create_branch_when_already_on_target_branch(tmp_path):
    """Daemon's ephemeral flow lands intake in a worktree already on the ticket branch."""
    orig = os.getcwd()
    os.chdir(tmp_path)
    try:
        seen_args: list[list[str]] = []

        def fake_run(args):
            seen_args.append(list(args))
            if args[:2] == ["git", "status"]:
                return _cp()
            if args[:3] == ["gh", "issue", "view"]:
                return _cp(stdout=_issue_json())
            if args[:3] == ["git", "rev-parse", "--abbrev-ref"]:
                return _cp(stdout="ticket/T099-my-feature\n")
            return _cp(returncode=2, stderr=f"unexpected: {args}")

        with patch("run_issue_intake._run", side_effect=fake_run):
            rc = run_intake("T099", 42, "my-feature", None)

        assert rc == 0
        # No git show-ref / checkout -b must have been issued
        for args in seen_args:
            assert args[:2] != ["git", "show-ref"]
            assert args[:3] != ["git", "checkout", "-b"]
    finally:
        os.chdir(orig)


# ── ticket.md format ──────────────────────────────────────────────────────────

def test_ticket_md_format(tmp_path):
    orig = os.getcwd()
    os.chdir(tmp_path)
    try:
        def fake_run(args):
            if args[:2] == ["git", "status"]:
                return _cp()
            if args[:3] == ["gh", "issue", "view"]:
                return _cp(stdout=_issue_json("Fix the bug", "Detailed body here"))
            if args[:2] == ["git", "show-ref"]:
                return _cp(returncode=1)
            return _cp()

        with patch("run_issue_intake._run", side_effect=fake_run):
            run_intake("T099", 42, "fix-bug", None)

        content = (tmp_path / "runs" / "T099" / "ticket.md").read_text()
        assert "# T099 — Fix the bug" in content
        assert "GitHub Issue #42" in content
        assert "Detailed body here" in content
    finally:
        os.chdir(orig)


# ── state.json format ─────────────────────────────────────────────────────────

def test_state_json_format(tmp_path):
    orig = os.getcwd()
    os.chdir(tmp_path)
    try:
        with patch("run_issue_intake._run", side_effect=_happy_fake_run):
            run_intake("T099", 42, "my-feature", None)

        state = json.loads((tmp_path / "runs" / "T099" / "state.json").read_text())
        assert state["ticket_id"] == "T099"
        assert state["state"] == "INIT"
        assert state["branch"] == "ticket/T099-my-feature"
        assert "updated_at" in state
    finally:
        os.chdir(orig)


# ── guard: state.json already exists ─────────────────────────────────────────

def test_state_already_exists_refused(tmp_path, capsys):
    orig = os.getcwd()
    os.chdir(tmp_path)
    try:
        run_dir = tmp_path / "runs" / "T099"
        run_dir.mkdir(parents=True)
        (run_dir / "state.json").write_text("{}", encoding="utf-8")

        with patch("run_issue_intake._run", side_effect=_happy_fake_run):
            rc = run_intake("T099", 42, "my-feature", None)

        assert rc == 2
        assert "state.json already exists" in capsys.readouterr().err
    finally:
        os.chdir(orig)


# ── guard: working tree dirty ─────────────────────────────────────────────────

def test_working_tree_dirty_refused(tmp_path, capsys):
    orig = os.getcwd()
    os.chdir(tmp_path)
    try:
        def fake_run(args):
            if args[:2] == ["git", "status"]:
                return _cp(stdout="M  some-file.py\n")
            return _cp()

        with patch("run_issue_intake._run", side_effect=fake_run):
            rc = run_intake("T099", 42, "my-feature", None)

        assert rc == 2
        assert "working tree" in capsys.readouterr().err
    finally:
        os.chdir(orig)


# ── guard: branch already exists ─────────────────────────────────────────────

def test_branch_already_exists_refused(tmp_path, capsys):
    """CLI path: if branch already exists AND we're not on it, intake must refuse."""
    orig = os.getcwd()
    os.chdir(tmp_path)
    try:
        def fake_run(args):
            if args[:2] == ["git", "status"]:
                return _cp()
            if args[:3] == ["gh", "issue", "view"]:
                return _cp(stdout=_issue_json())
            if args[:3] == ["git", "rev-parse", "--abbrev-ref"]:
                return _cp(stdout="main\n")  # not on target branch
            if args[:2] == ["git", "show-ref"]:
                return _cp(returncode=0)  # branch exists
            return _cp()

        with patch("run_issue_intake._run", side_effect=fake_run):
            rc = run_intake("T099", 42, "my-feature", None)

        assert rc == 2
        assert "already exists" in capsys.readouterr().err
    finally:
        os.chdir(orig)
