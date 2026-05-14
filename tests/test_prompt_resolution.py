"""Tests for T022 — generic prompt fallback and resolution."""

import sys
from io import StringIO
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "tools" / "agent_runner"))

from run_step import RunnerError, find_prompt, main, prompt_candidates


def _make_ticket_prompt(tmp_path: Path, ticket_id: str, step: str) -> Path:
    p = tmp_path / "prompts" / f"{ticket_id}-{step}.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(f"# {ticket_id} {step} task", encoding="utf-8")
    return p


def _make_generic_prompt(tmp_path: Path, step: str) -> Path:
    p = tmp_path / "prompts" / "generic" / f"{step}.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(f"# Generic {step} task\n\nThe ticket follows.", encoding="utf-8")
    return p


def _make_ticket_md(tmp_path: Path, ticket_id: str, content: str = "# Ticket content") -> Path:
    p = tmp_path / "runs" / ticket_id / "ticket.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return p


def _make_run_tree(tmp_path: Path, ticket_id: str) -> None:
    for subdir in ["prompts", "reviews", "fixes", "tests", "memory"]:
        (tmp_path / "runs" / ticket_id / subdir).mkdir(parents=True, exist_ok=True)


def test_ticket_specific_takes_priority(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _make_ticket_prompt(tmp_path, "T099", "planner")
    _make_generic_prompt(tmp_path, "planner")
    _make_run_tree(tmp_path, "T099")

    path, source = find_prompt("T099", "planner")

    assert path == Path("prompts") / "T099-planner.md"
    assert source == "ticket-specific"


def test_generic_fallback_used_when_no_ticket_prompt(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _make_generic_prompt(tmp_path, "coder")
    _make_run_tree(tmp_path, "T099")

    path, source = find_prompt("T099", "coder")

    assert path == Path("prompts") / "generic" / "coder.md"
    assert source == "generic"


def test_error_when_no_prompt_exists(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _make_run_tree(tmp_path, "T099")

    with pytest.raises(RunnerError, match="prompt not found"):
        find_prompt("T099", "tester")


def test_find_prompt_logs_source(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _make_generic_prompt(tmp_path, "review")
    _make_run_tree(tmp_path, "T099")

    find_prompt("T099", "review")

    log = (tmp_path / "runs" / "T099" / "runtime.log").read_text(encoding="utf-8")
    assert "source=generic" in log
    assert "prompts/generic/review.md" in log


def test_generic_injects_ticket_md(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _make_generic_prompt(tmp_path, "planner")
    _make_ticket_md(tmp_path, "T099", content="# T099 specific ticket\nsome details")
    _make_run_tree(tmp_path, "T099")

    rc = main(["T099", "planner", "--show-prompt"])

    assert rc == 0
    captured = capsys.readouterr()
    assert "T099 specific ticket" in captured.out
    assert "some details" in captured.out


def test_generic_errors_when_ticket_md_missing(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    _make_generic_prompt(tmp_path, "coder")
    _make_run_tree(tmp_path, "T099")

    rc = main(["T099", "coder", "--show-prompt"])

    assert rc == 2
    captured = capsys.readouterr()
    assert "ticket.md" in captured.err
