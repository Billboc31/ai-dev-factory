"""Tests for T033 — bootstrap checkpoint commit in issue intake."""

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "tools" / "agent_runner"))

from run_issue_intake import commit_bootstrap, run_intake


def _cp(stdout="", stderr="", returncode=0):
    r = MagicMock()
    r.stdout = stdout
    r.stderr = stderr
    r.returncode = returncode
    return r


# ── commit_bootstrap: staging ────────────────────────────────────────────────

def test_commit_bootstrap_stages_ticket_md_path():
    calls = []

    def fake_run(args):
        calls.append(args)
        return _cp()

    with patch("run_issue_intake._run", side_effect=fake_run):
        commit_bootstrap("T099")

    add_calls = [c for c in calls if c[:2] == ["git", "add"]]
    staged_paths = [c[-1] for c in add_calls]
    # bootstrap stages ticket.md and state.json
    assert "runs/T099/ticket.md" in staged_paths


def test_commit_bootstrap_never_calls_git_add_dot():
    calls = []

    def fake_run(args):
        calls.append(args)
        return _cp()

    with patch("run_issue_intake._run", side_effect=fake_run):
        commit_bootstrap("T099")

    assert ["git", "add", "."] not in calls
    for c in calls:
        if c[:2] == ["git", "add"]:
            assert "." not in c[2:], f"git add . found in {c}"


# ── commit_bootstrap: commit message ─────────────────────────────────────────

def test_commit_bootstrap_uses_bootstrap_checkpoint_message():
    commit_calls = []

    def fake_run(args):
        if args[:2] == ["git", "commit"]:
            commit_calls.append(args)
        return _cp()

    with patch("run_issue_intake._run", side_effect=fake_run):
        commit_bootstrap("T099")

    assert len(commit_calls) == 1
    assert "T099: bootstrap checkpoint" in " ".join(commit_calls[0])


# ── commit_bootstrap: push flag ───────────────────────────────────────────────

def test_commit_bootstrap_no_push_by_default():
    calls = []

    def fake_run(args):
        calls.append(args)
        return _cp()

    with patch("run_issue_intake._run", side_effect=fake_run):
        commit_bootstrap("T099", push=False)

    push_calls = [c for c in calls if c[:2] == ["git", "push"]]
    assert push_calls == []


def test_commit_bootstrap_pushes_when_requested():
    calls = []

    def fake_run(args):
        calls.append(args)
        return _cp()

    with patch("run_issue_intake._run", side_effect=fake_run):
        commit_bootstrap("T099", push=True)

    push_calls = [c for c in calls if c[:2] == ["git", "push"]]
    assert len(push_calls) == 1


# ── commit_bootstrap: failure handling ───────────────────────────────────────

def test_commit_bootstrap_skips_commit_on_add_failure():
    calls = []

    def fake_run(args):
        calls.append(args)
        if args[:2] == ["git", "add"]:
            return _cp(returncode=1, stderr="permission denied")
        return _cp()

    with patch("run_issue_intake._run", side_effect=fake_run):
        commit_bootstrap("T099")  # must not raise

    commit_calls = [c for c in calls if c[:2] == ["git", "commit"]]
    assert commit_calls == []


def test_commit_bootstrap_skips_push_on_commit_failure():
    calls = []

    def fake_run(args):
        calls.append(args)
        if args[:2] == ["git", "commit"]:
            return _cp(returncode=1, stderr="nothing to commit")
        return _cp()

    with patch("run_issue_intake._run", side_effect=fake_run):
        commit_bootstrap("T099", push=True)

    push_calls = [c for c in calls if c[:2] == ["git", "push"]]
    assert push_calls == []


def test_commit_bootstrap_add_failure_does_not_raise():
    def fake_run(args):
        return _cp(returncode=2, stderr="unexpected error")

    with patch("run_issue_intake._run", side_effect=fake_run):
        commit_bootstrap("T099")  # must not raise


# ── run_intake: push flag propagation ────────────────────────────────────────

def test_run_intake_passes_push_true_to_commit_bootstrap(tmp_path):
    bootstrap_calls = []

    def fake_bootstrap(ticket_id, push=False):
        bootstrap_calls.append({"ticket_id": ticket_id, "push": push})

    def fake_run(args):
        if args[:2] == ["git", "status"]:
            return _cp()
        if args[:3] == ["gh", "issue", "view"]:
            return _cp(stdout=json.dumps({"title": "T", "body": "B"}))
        if args[:2] == ["git", "show-ref"]:
            return _cp(returncode=1)
        return _cp()

    orig = os.getcwd()
    os.chdir(tmp_path)
    try:
        with patch("run_issue_intake._run", side_effect=fake_run), \
             patch("run_issue_intake.commit_bootstrap", side_effect=fake_bootstrap):
            rc = run_intake("T099", 42, "slug", None, push=True)
    finally:
        os.chdir(orig)

    assert rc == 0
    assert len(bootstrap_calls) == 1
    assert bootstrap_calls[0] == {"ticket_id": "T099", "push": True}


def test_run_intake_passes_push_false_by_default(tmp_path):
    bootstrap_calls = []

    def fake_bootstrap(ticket_id, push=False):
        bootstrap_calls.append({"ticket_id": ticket_id, "push": push})

    def fake_run(args):
        if args[:2] == ["git", "status"]:
            return _cp()
        if args[:3] == ["gh", "issue", "view"]:
            return _cp(stdout=json.dumps({"title": "T", "body": "B"}))
        if args[:2] == ["git", "show-ref"]:
            return _cp(returncode=1)
        return _cp()

    orig = os.getcwd()
    os.chdir(tmp_path)
    try:
        with patch("run_issue_intake._run", side_effect=fake_run), \
             patch("run_issue_intake.commit_bootstrap", side_effect=fake_bootstrap):
            rc = run_intake("T099", 42, "slug", None)
    finally:
        os.chdir(orig)

    assert rc == 0
    assert bootstrap_calls[0]["push"] is False
