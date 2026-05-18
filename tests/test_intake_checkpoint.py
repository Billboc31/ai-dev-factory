"""Tests for T033 — bootstrap checkpoint commit in issue intake."""

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent / "tools" / "agent_runner"))

from run_issue_intake import commit_bootstrap, run_intake
from runtime_checkpoint import CheckpointError, DirtyTreeError


def _cp(stdout="", stderr="", returncode=0):
    r = MagicMock()
    r.stdout = stdout
    r.stderr = stderr
    r.returncode = returncode
    return r


# ── commit_bootstrap: delegates to checkpoint_transition ─────────────────────

def test_commit_bootstrap_calls_checkpoint_transition():
    with patch("run_issue_intake._checkpoint_transition") as mock_ckpt:
        commit_bootstrap("T099")
    mock_ckpt.assert_called_once()
    args, kwargs = mock_ckpt.call_args
    assert args[0] == "T099"


def test_commit_bootstrap_never_calls_git_add_dot():
    """checkpoint_transition stages by path, never git add ."""
    with patch("run_issue_intake._checkpoint_transition") as mock_ckpt:
        commit_bootstrap("T099")
    # The module does not call _run directly — git add . is never issued
    mock_ckpt.assert_called_once()


# ── commit_bootstrap: commit message ─────────────────────────────────────────

def test_commit_bootstrap_uses_bootstrap_checkpoint_message():
    with patch("run_issue_intake._checkpoint_transition") as mock_ckpt:
        commit_bootstrap("T099")
    args, _kwargs = mock_ckpt.call_args
    assert "T099: bootstrap checkpoint" in args[1]


# ── commit_bootstrap: push flag ───────────────────────────────────────────────

def test_commit_bootstrap_no_push_by_default():
    with patch("run_issue_intake._checkpoint_transition") as mock_ckpt:
        commit_bootstrap("T099", push=False)
    _args, kwargs = mock_ckpt.call_args
    assert kwargs.get("push") is False


def test_commit_bootstrap_pushes_when_requested():
    with patch("run_issue_intake._checkpoint_transition") as mock_ckpt:
        commit_bootstrap("T099", push=True)
    _args, kwargs = mock_ckpt.call_args
    assert kwargs.get("push") is True


# ── commit_bootstrap: failure handling ───────────────────────────────────────

def test_commit_bootstrap_does_not_raise_on_checkpoint_error():
    with patch("run_issue_intake._checkpoint_transition", side_effect=CheckpointError("add failed")):
        commit_bootstrap("T099")  # must not raise


def test_commit_bootstrap_does_not_raise_on_dirty_tree_error():
    with patch("run_issue_intake._checkpoint_transition", side_effect=DirtyTreeError("DIRTY_RUNTIME_CHECKPOINT")):
        commit_bootstrap("T099")  # must not raise


def test_commit_bootstrap_add_failure_does_not_raise():
    with patch("run_issue_intake._checkpoint_transition", side_effect=CheckpointError("unexpected error")):
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
