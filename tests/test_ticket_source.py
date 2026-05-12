"""Tests for T019 — ticket source snapshot initialization."""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "tools" / "agent_runner"))

from run_ticket import TicketRunnerError, _copy_ticket_source, init_auto


def _cp(stdout="", stderr="", returncode=0):
    r = MagicMock()
    r.stdout = stdout
    r.stderr = stderr
    r.returncode = returncode
    return r


# ── _copy_ticket_source unit tests ────────────────────────────────────────────

def test_copy_valid_file(tmp_path):
    src = tmp_path / "source-ticket.md"
    src.write_text("# My ticket\ncontent here\n", encoding="utf-8")
    runs_dir = tmp_path / "runs" / "T099"
    runs_dir.mkdir(parents=True)
    orig = os.getcwd()
    os.chdir(tmp_path)
    try:
        _copy_ticket_source("T099", str(src))
        dest = tmp_path / "runs" / "T099" / "ticket.md"
        assert dest.exists()
        assert dest.read_text(encoding="utf-8") == "# My ticket\ncontent here\n"
    finally:
        os.chdir(orig)


def test_copy_missing_file(tmp_path):
    orig = os.getcwd()
    os.chdir(tmp_path)
    try:
        (tmp_path / "runs" / "T099").mkdir(parents=True)
        with pytest.raises(TicketRunnerError, match="ticket-source not found"):
            _copy_ticket_source("T099", str(tmp_path / "nonexistent.md"))
    finally:
        os.chdir(orig)


def test_copy_traversal_blocked(tmp_path):
    orig = os.getcwd()
    os.chdir(tmp_path)
    try:
        with pytest.raises(TicketRunnerError, match="must not contain"):
            _copy_ticket_source("T099", "../some/path.md")
    finally:
        os.chdir(orig)


def test_copy_directory_blocked(tmp_path):
    src_dir = tmp_path / "a-directory"
    src_dir.mkdir()
    orig = os.getcwd()
    os.chdir(tmp_path)
    try:
        (tmp_path / "runs" / "T099").mkdir(parents=True)
        with pytest.raises(TicketRunnerError, match="must be a file, not a directory"):
            _copy_ticket_source("T099", str(src_dir))
    finally:
        os.chdir(orig)


# ── init_auto integration tests ───────────────────────────────────────────────

def test_init_auto_with_ticket_source(tmp_path):
    src = tmp_path / "tickets" / "T099-task.md"
    src.parent.mkdir()
    src.write_text("# T099\ndescription\n", encoding="utf-8")

    orig = os.getcwd()
    os.chdir(tmp_path)
    try:
        def fake_git(args):
            if "--abbrev-ref" in args:
                return _cp("ticket/T099-work\n")
            return _cp()

        with patch("run_ticket.run_command", side_effect=fake_git):
            rc = init_auto("T099", "work", ticket_source=str(src))

        assert rc == 0
        dest = tmp_path / "runs" / "T099" / "ticket.md"
        assert dest.exists()
        assert dest.read_text(encoding="utf-8") == "# T099\ndescription\n"
    finally:
        os.chdir(orig)


def test_init_auto_without_ticket_source(tmp_path):
    orig = os.getcwd()
    os.chdir(tmp_path)
    try:
        def fake_git(args):
            if "--abbrev-ref" in args:
                return _cp("ticket/T099-work\n")
            return _cp()

        with patch("run_ticket.run_command", side_effect=fake_git):
            rc = init_auto("T099", "work", ticket_source=None)

        assert rc == 0
        state_path = tmp_path / "runs" / "T099" / "state.json"
        assert state_path.exists()
        ticket_path = tmp_path / "runs" / "T099" / "ticket.md"
        assert not ticket_path.exists()
    finally:
        os.chdir(orig)
