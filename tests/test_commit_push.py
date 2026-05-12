"""Tests for T017 — workflow-aware commit and push."""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "tools" / "agent_runner"))

from run_ticket import (
    COMMIT_SCOPE,
    commit_ticket,
    push_branch,
    _warn_out_of_scope,
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


def test_commit_succeeds_on_correct_branch():
    with tempfile.TemporaryDirectory() as tmp:
        orig = os.getcwd()
        os.chdir(tmp)
        try:
            _write_state(Path(tmp) / "runs" / "T999", branch="ticket/T999-work")

            def fake(args):
                if "--abbrev-ref" in args:
                    return _cp("ticket/T999-work\n")
                if "--porcelain" in args:
                    return _cp(" M runs/T999/state.json\n")
                if "add" in args:
                    return _cp()
                if "commit" in args:
                    return _cp("1 file changed")
                if "--short" in args:
                    return _cp("abc1234\n")
                return _cp()

            with patch("run_ticket.run_command", side_effect=fake):
                rc = commit_ticket("T999", None)

            assert rc == 0
        finally:
            os.chdir(orig)


# ── No git add . ──────────────────────────────────────────────────────────────

def test_commit_never_calls_git_add_dot():
    with tempfile.TemporaryDirectory() as tmp:
        orig = os.getcwd()
        os.chdir(tmp)
        try:
            _write_state(Path(tmp) / "runs" / "T999", branch="ticket/T999-work")

            calls = []

            def fake(args):
                calls.append(list(args))
                if "--abbrev-ref" in args:
                    return _cp("ticket/T999-work\n")
                if "--porcelain" in args:
                    return _cp(" M runs/T999/state.json\n")
                if "add" in args:
                    return _cp()
                if "commit" in args:
                    return _cp()
                if "--short" in args:
                    return _cp("abc1234\n")
                return _cp()

            with patch("run_ticket.run_command", side_effect=fake):
                commit_ticket("T999", None, include_code=True)

            add_calls = [c for c in calls if c[:2] == ["git", "add"]]
            for c in add_calls:
                assert "." not in c, f"git add . found in {c}"
                assert len(c) == 3, f"unexpected add args: {c}"
        finally:
            os.chdir(orig)


# ── include_code=False: only runs/ staged ────────────────────────────────────

def test_commit_without_include_code_stages_only_run_dir():
    with tempfile.TemporaryDirectory() as tmp:
        orig = os.getcwd()
        os.chdir(tmp)
        try:
            _write_state(Path(tmp) / "runs" / "T999", branch="ticket/T999-work")

            calls = []

            def fake(args):
                calls.append(list(args))
                if "--abbrev-ref" in args:
                    return _cp("ticket/T999-work\n")
                if "--porcelain" in args:
                    return _cp(" M runs/T999/state.json\n")
                if "add" in args:
                    return _cp()
                if "commit" in args:
                    return _cp()
                if "--short" in args:
                    return _cp("abc1234\n")
                return _cp()

            with patch("run_ticket.run_command", side_effect=fake):
                commit_ticket("T999", None, include_code=False)

            add_calls = [c for c in calls if c[:2] == ["git", "add"]]
            assert len(add_calls) == 1
            assert add_calls[0] == ["git", "add", "runs/T999/"]
        finally:
            os.chdir(orig)


# ── include_code=True: runs/ + COMMIT_SCOPE staged ───────────────────────────

def test_commit_with_include_code_stages_all_scope_paths():
    with tempfile.TemporaryDirectory() as tmp:
        orig = os.getcwd()
        os.chdir(tmp)
        try:
            _write_state(Path(tmp) / "runs" / "T999", branch="ticket/T999-work")

            calls = []

            def fake(args):
                calls.append(list(args))
                if "--abbrev-ref" in args:
                    return _cp("ticket/T999-work\n")
                if "--porcelain" in args:
                    return _cp(" M runs/T999/state.json\n")
                if "add" in args:
                    return _cp()
                if "commit" in args:
                    return _cp()
                if "--short" in args:
                    return _cp("abc1234\n")
                return _cp()

            with patch("run_ticket.run_command", side_effect=fake):
                commit_ticket("T999", None, include_code=True)

            add_calls = [c for c in calls if c[:2] == ["git", "add"]]
            staged = [c[2] for c in add_calls]
            assert "runs/T999/" in staged
            for scope_path in COMMIT_SCOPE:
                assert scope_path in staged, f"{scope_path} not staged with include_code=True"
        finally:
            os.chdir(orig)


# ── Nothing to commit ─────────────────────────────────────────────────────────

def test_commit_returns_1_when_nothing_to_commit():
    with tempfile.TemporaryDirectory() as tmp:
        orig = os.getcwd()
        os.chdir(tmp)
        try:
            _write_state(Path(tmp) / "runs" / "T999", branch="ticket/T999-work")

            def fake(args):
                if "--abbrev-ref" in args:
                    return _cp("ticket/T999-work\n")
                if "--porcelain" in args:
                    return _cp("")
                return _cp()

            with patch("run_ticket.run_command", side_effect=fake):
                rc = commit_ticket("T999", None)

            assert rc == 1
        finally:
            os.chdir(orig)


# ── Out-of-scope warning ──────────────────────────────────────────────────────

def test_warn_out_of_scope_reports_outside_files(capsys):
    with tempfile.TemporaryDirectory() as tmp:
        orig = os.getcwd()
        os.chdir(tmp)
        try:
            (Path(tmp) / "runs" / "T999").mkdir(parents=True)

            status_output = " M secret.env\n M runs/T999/state.json\n M tools/foo.py\n"

            def fake(args):
                if args == ["git", "status", "--porcelain"]:
                    return _cp(status_output)
                return _cp()

            with patch("run_ticket.run_command", side_effect=fake):
                _warn_out_of_scope("T999", "runs/T999/")

            captured = capsys.readouterr()
            combined = captured.out + captured.err
            assert "secret.env" in combined
            # tools/foo.py is in scope — must not be flagged
            assert "tools/foo.py" not in combined
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


def test_push_warns_on_dirty_working_tree(capsys):
    with tempfile.TemporaryDirectory() as tmp:
        orig = os.getcwd()
        os.chdir(tmp)
        try:
            _write_state(Path(tmp) / "runs" / "T999", branch="ticket/T999-work")

            def fake(args):
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
            assert "warning" in (captured.out + captured.err).lower()
            assert rc == 0
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
