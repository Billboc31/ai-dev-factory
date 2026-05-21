"""Tests for workflow-aware commit and push (post hardening).

This module covers the *stable* contract that has survived the runtime
hardening refactor:

- ``COMMIT_SCOPE`` shape (still consumed by ``checkpoint_transition``).
- ``archive_daemon`` flag persistence.
- Branch validation in ``commit_ticket`` and ``push_branch``.
- ``push_branch`` blocks on *real* dirty files but tolerates runtime garbage.

The new ``git add -A`` + runtime-unstage commit strategy is exercised by
``tests/test_auto_commit_runtime_safety.py``.
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent / "tools" / "agent_runner"))

from run_ticket import (
    COMMIT_SCOPE,
    archive_daemon,
    commit_ticket,
    push_branch,
)


def _cp(stdout="", stderr="", returncode=0):
    r = MagicMock()
    r.stdout = stdout
    r.stderr = stderr
    r.returncode = returncode
    return r


def _write_state(run_dir: Path, branch: str = "ticket/T999-work") -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "state.json").write_text(json.dumps({
        "ticket_id": "T999",
        "state": "PLAN_APPROVED",
        "branch": branch,
        "updated_at": "2026-01-01T00:00:00Z",
    }))


# ── COMMIT_SCOPE content ──────────────────────────────────────────────────────

def test_commit_scope_contains_expected_paths():
    assert "tools/" in COMMIT_SCOPE
    assert "tests/" in COMMIT_SCOPE
    assert "prompts/" in COMMIT_SCOPE
    assert "tickets/" in COMMIT_SCOPE
    assert "docs/" in COMMIT_SCOPE
    assert "ai/" in COMMIT_SCOPE


def test_commit_scope_has_no_glob_or_dot():
    for path in COMMIT_SCOPE:
        assert path != "."
        assert "*" not in path
        assert path != "/"


def test_commit_scope_contains_apps_and_services():
    assert "apps/" in COMMIT_SCOPE
    assert "services/" in COMMIT_SCOPE


def test_commit_scope_contains_package_json():
    assert "package.json" in COMMIT_SCOPE
    assert "package-lock.json" in COMMIT_SCOPE


# ── archive_daemon ────────────────────────────────────────────────────────────

def test_archive_daemon_writes_daemon_archived_flag(tmp_path):
    run_dir = tmp_path / "runs" / "T999"
    run_dir.mkdir(parents=True)
    (run_dir / "state.json").write_text(json.dumps({
        "ticket_id": "T999",
        "state": "TEST_COMPLETE",
        "branch": "ticket/T999-work",
        "updated_at": "2026-01-01T00:00:00Z",
    }))
    orig = os.getcwd()
    os.chdir(tmp_path)
    try:
        rc = archive_daemon("T999")
    finally:
        os.chdir(orig)
    assert rc == 0
    saved = json.loads((run_dir / "state.json").read_text(encoding="utf-8"))
    assert saved["daemon_archived"] is True


def test_archive_daemon_returns_2_when_state_missing(tmp_path):
    orig = os.getcwd()
    os.chdir(tmp_path)
    try:
        rc = archive_daemon("T999")
    finally:
        os.chdir(orig)
    assert rc == 2


# ── Branch validation in commit_ticket ───────────────────────────────────────

def test_commit_refused_on_wrong_branch():
    with tempfile.TemporaryDirectory() as tmp:
        orig = os.getcwd()
        os.chdir(tmp)
        try:
            _write_state(Path(tmp) / "runs" / "T999", branch="ticket/T999-work")

            def fake(args):
                if "--abbrev-ref" in args:
                    return _cp("ticket/T999-other\n")
                return _cp()

            with patch("run_ticket.run_command", side_effect=fake):
                rc = commit_ticket("T999", None)

            assert rc == 2
        finally:
            os.chdir(orig)


# ── Push branch guardrails ────────────────────────────────────────────────────

def test_push_refused_on_wrong_branch():
    with tempfile.TemporaryDirectory() as tmp:
        orig = os.getcwd()
        os.chdir(tmp)
        try:
            _write_state(Path(tmp) / "runs" / "T999", branch="ticket/T999-work")

            def fake(args):
                if "--abbrev-ref" in args:
                    return _cp("ticket/T999-other\n")
                return _cp()

            with patch("run_ticket.run_command", side_effect=fake):
                rc = push_branch("T999", None)

            assert rc == 2
        finally:
            os.chdir(orig)


def test_push_blocked_on_real_dirty_file(capsys):
    """Real uncommitted code changes must block the push."""
    with tempfile.TemporaryDirectory() as tmp:
        orig = os.getcwd()
        os.chdir(tmp)
        try:
            _write_state(Path(tmp) / "runs" / "T999", branch="ticket/T999-work")

            def fake(args, **kwargs):
                if "--abbrev-ref" in args:
                    return _cp("ticket/T999-work\n")
                if args == ["git", "status", "--porcelain"]:
                    return _cp(" M uncommitted.py\n")
                if "push" in args:
                    return _cp("pushed\n")
                return _cp()

            with patch("run_ticket.run_command", side_effect=fake):
                rc = push_branch("T999", None)

            captured = capsys.readouterr()
            assert "DIRTY_RUNTIME_CHECKPOINT" in (captured.out + captured.err)
            assert rc == 2
        finally:
            os.chdir(orig)


def test_push_only_pushes_ticket_branch():
    with tempfile.TemporaryDirectory() as tmp:
        orig = os.getcwd()
        os.chdir(tmp)
        try:
            _write_state(Path(tmp) / "runs" / "T999", branch="ticket/T999-work")

            push_calls = []

            def fake(args):
                if "--abbrev-ref" in args:
                    return _cp("ticket/T999-work\n")
                if args == ["git", "status", "--porcelain"]:
                    return _cp("")
                if "push" in args:
                    push_calls.append(list(args))
                    return _cp("pushed\n")
                return _cp()

            with patch("run_ticket.run_command", side_effect=fake):
                push_branch("T999", None)

            assert len(push_calls) == 1
            assert "ticket/T999-work" in push_calls[0]
        finally:
            os.chdir(orig)
