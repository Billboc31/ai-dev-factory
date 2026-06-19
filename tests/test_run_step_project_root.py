"""Tests for --project-root context loading in run_step.py (T195)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "tools" / "agent_runner"))

from run_step import compose_runtime_prompt, main


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


# ── compose_runtime_prompt with project_root ──────────────────────────────────

def test_project_root_global_context_preferred(tmp_path, monkeypatch):
    """project_root/docs/ai/global-context.md is used when it exists."""
    factory = tmp_path / "factory"
    project = tmp_path / "managed"
    factory.mkdir()

    monkeypatch.chdir(factory)
    _write(factory / "runs" / "T001" / "prompts" / ".keep", "")
    _write(factory / "docs" / "ai" / "global-context.md", "factory context")
    _write(project / "docs" / "ai" / "global-context.md", "project context")

    result = compose_runtime_prompt("T001", "coder", "task", project_root=project)
    assert "project context" in result
    assert "factory context" not in result


def test_project_root_falls_back_to_factory_context(tmp_path, monkeypatch):
    """Falls back to factory-relative global-context.md when absent in project_root."""
    factory = tmp_path / "factory"
    project = tmp_path / "managed"
    factory.mkdir()

    monkeypatch.chdir(factory)
    _write(factory / "runs" / "T001" / "prompts" / ".keep", "")
    _write(factory / "docs" / "ai" / "global-context.md", "factory context")
    project.mkdir(parents=True, exist_ok=True)

    result = compose_runtime_prompt("T001", "coder", "task", project_root=project)
    assert "factory context" in result


def test_no_project_root_uses_factory_context(tmp_path, monkeypatch):
    """Without project_root the factory-relative context is used (existing behaviour)."""
    monkeypatch.chdir(tmp_path)
    _write(tmp_path / "runs" / "T001" / "prompts" / ".keep", "")
    _write(tmp_path / "docs" / "ai" / "global-context.md", "factory context")

    result = compose_runtime_prompt("T001", "coder", "task")
    assert "factory context" in result


def test_project_root_role_preferred(tmp_path, monkeypatch):
    """project_root/ai/roles/planner.md is used when it exists."""
    factory = tmp_path / "factory"
    project = tmp_path / "managed"
    factory.mkdir()

    monkeypatch.chdir(factory)
    _write(factory / "runs" / "T001" / "prompts" / ".keep", "")
    _write(factory / "ai" / "roles" / "planner.md", "factory planner role")
    _write(project / "ai" / "roles" / "planner.md", "project planner role")

    result = compose_runtime_prompt("T001", "planner", "task", project_root=project)
    assert "project planner role" in result
    assert "factory planner role" not in result


def test_project_root_role_falls_back_to_factory(tmp_path, monkeypatch):
    """Falls back to factory role when absent in project_root."""
    factory = tmp_path / "factory"
    project = tmp_path / "managed"
    factory.mkdir()
    project.mkdir(parents=True, exist_ok=True)

    monkeypatch.chdir(factory)
    _write(factory / "runs" / "T001" / "prompts" / ".keep", "")
    _write(factory / "ai" / "roles" / "planner.md", "factory planner role")

    result = compose_runtime_prompt("T001", "planner", "task", project_root=project)
    assert "factory planner role" in result


def test_project_root_skill_preferred(tmp_path, monkeypatch):
    """project_root/ai/skills/code-quality.md is used when it exists."""
    factory = tmp_path / "factory"
    project = tmp_path / "managed"
    factory.mkdir()

    monkeypatch.chdir(factory)
    _write(factory / "runs" / "T001" / "prompts" / ".keep", "")
    _write(factory / "ai" / "skills" / "code-quality.md", "factory skill")
    _write(project / "ai" / "skills" / "code-quality.md", "project skill")

    result = compose_runtime_prompt("T001", "coder", "task", project_root=project)
    assert "project skill" in result
    assert "factory skill" not in result


def test_project_root_skill_falls_back_to_factory(tmp_path, monkeypatch):
    """Falls back to factory skill when absent in project_root."""
    factory = tmp_path / "factory"
    project = tmp_path / "managed"
    factory.mkdir()
    project.mkdir(parents=True, exist_ok=True)

    monkeypatch.chdir(factory)
    _write(factory / "runs" / "T001" / "prompts" / ".keep", "")
    _write(factory / "ai" / "skills" / "code-quality.md", "factory skill")

    result = compose_runtime_prompt("T001", "coder", "task", project_root=project)
    assert "factory skill" in result


def test_project_root_task_always_included(tmp_path, monkeypatch):
    """The TASK section is always included regardless of project_root."""
    project = tmp_path / "managed"
    project.mkdir(parents=True, exist_ok=True)

    monkeypatch.chdir(tmp_path)
    _write(tmp_path / "runs" / "T001" / "prompts" / ".keep", "")

    result = compose_runtime_prompt("T001", "coder", "my task content", project_root=project)
    assert "my task content" in result


# ── --project-root CLI flag ───────────────────────────────────────────────────

def test_cli_project_root_loads_project_context(tmp_path, monkeypatch, capsys):
    """--project-root CLI flag causes project context to appear in rendered prompt."""
    factory = tmp_path / "factory"
    project = tmp_path / "managed"
    factory.mkdir()

    monkeypatch.chdir(factory)
    _write(factory / "docs" / "ai" / "global-context.md", "factory context")
    _write(project / "docs" / "ai" / "global-context.md", "project context")
    _write(factory / "prompts" / "T001-coder.md", "# TASK\n\ntask content")
    (factory / "runs" / "T001").mkdir(parents=True, exist_ok=True)

    rc = main(["T001", "coder", "--show-prompt", "--project-root", str(project)])
    assert rc == 0
    captured = capsys.readouterr()
    assert "project context" in captured.out
    assert "factory context" not in captured.out


def test_cli_project_root_absent_uses_factory(tmp_path, monkeypatch, capsys):
    """Without --project-root, factory context is used (no regression)."""
    monkeypatch.chdir(tmp_path)
    _write(tmp_path / "docs" / "ai" / "global-context.md", "factory context")
    _write(tmp_path / "prompts" / "T001-coder.md", "# TASK\n\ntask content")
    (tmp_path / "runs" / "T001").mkdir(parents=True, exist_ok=True)

    rc = main(["T001", "coder", "--show-prompt"])
    assert rc == 0
    captured = capsys.readouterr()
    assert "factory context" in captured.out
