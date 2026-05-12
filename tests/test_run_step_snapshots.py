"""Tests ciblés pour la persistance des runtime prompt snapshots (T016)."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "tools" / "agent_runner"))

from run_step import _next_attempt_number, _write_prompt_snapshot, main


def test_snapshot_created(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _setup_minimal_tree(tmp_path, "T016", "planner")
    _write_prompt_snapshot("T016", "planner", "mon prompt")
    snapshots = list((tmp_path / "runs" / "T016" / "prompts").glob("planner-attempt-*.md"))
    assert len(snapshots) == 1


def test_snapshot_naming(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _setup_minimal_tree(tmp_path, "T016", "coder")
    path = _write_prompt_snapshot("T016", "coder", "contenu")
    assert path.name == "coder-attempt-1.md"


def test_snapshot_attempt_increment(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _setup_minimal_tree(tmp_path, "T016", "review")
    _write_prompt_snapshot("T016", "review", "premier")
    _write_prompt_snapshot("T016", "review", "deuxieme")
    path3 = _write_prompt_snapshot("T016", "review", "troisieme")
    assert path3.name == "review-attempt-3.md"
    assert _next_attempt_number("T016", "review") == 4


def test_snapshot_contains_extra_context(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _setup_minimal_tree(tmp_path, "T016", "planner")
    extra = "## Contexte de retry injecté\n\nfix context contenu"
    prompt_with_extra = "prompt de base\n\n---\n\n" + extra
    path = _write_prompt_snapshot("T016", "planner", prompt_with_extra)
    assert extra in path.read_text(encoding="utf-8")


def test_snapshot_content_exact(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _setup_minimal_tree(tmp_path, "T016", "tester")
    expected = "# GLOBAL CONTEXT\n\nglobal\n\n---\n\n# ROLE\n\nrole\n\n---\n\n# TASK\n\ntask"
    path = _write_prompt_snapshot("T016", "tester", expected)
    assert path.read_text(encoding="utf-8") == expected


def test_no_snapshot_without_exec_cmd(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _setup_minimal_tree(tmp_path, "T099", "planner")
    (tmp_path / "prompts").mkdir(exist_ok=True)
    (tmp_path / "prompts" / "T099-planner.md").write_text("# TASK\n\ntask content", encoding="utf-8")
    main(["T099", "planner", "--show-prompt"])
    snapshots = list((tmp_path / "runs" / "T099" / "prompts").glob("planner-attempt-*.md"))
    assert len(snapshots) == 0


# --- helpers ---

def _setup_minimal_tree(tmp_path: Path, ticket_id: str, step: str) -> None:
    """Create the minimum file structure for _write_prompt_snapshot to work."""
    prompts_dir = tmp_path / "runs" / ticket_id / "prompts"
    prompts_dir.mkdir(parents=True, exist_ok=True)
