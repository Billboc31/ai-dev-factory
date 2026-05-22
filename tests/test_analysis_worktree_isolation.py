"""Tests for run_analysis worktree isolation when --worktrees-dir is provided."""
from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "agent_runner"))

import run_analysis

_VALID_OUTPUT = """\
--- BEGIN FILE: .ai-dev-factory/deploy.yml ---
version: "1"
components: []
--- END FILE ---
--- BEGIN FILE: .ai-dev-factory/deployment.md ---
# Deployment Guide
--- END FILE ---
"""

_MOCK_SCAN = {
    "docker_services": [],
    "python_backend": False,
    "node_frontend": False,
    "required_tools": [],
}


def _make_fake_worktree(tmp_path: Path) -> Path:
    wt = tmp_path / "worktrees" / "analysis-testproj-20260101T120000"
    wt.mkdir(parents=True)
    return wt


def _patch_main(monkeypatch, tmp_path: Path, project_id: str = "testproj") -> Path:
    worktrees_dir = tmp_path / "worktrees"
    monkeypatch.setenv("AI_DEV_FACTORY_RUNTIME_ROOT", str(tmp_path))
    monkeypatch.setattr(run_analysis, "_invoke_llm", lambda *a, **kw: _VALID_OUTPUT)
    monkeypatch.setattr(run_analysis, "_scan_project", lambda p: _MOCK_SCAN)
    monkeypatch.setattr(
        run_analysis,
        "commit_and_push",
        lambda root, pid: ("ai-analysis/testproj-20260101-120000", "https://github.com/org/repo/pull/42"),
    )
    monkeypatch.setattr(sys, "argv", [
        "run_analysis.py",
        "--project-root", str(tmp_path),
        "--project-id", project_id,
        "--exec-cmd", "claude",
        "--worktrees-dir", str(worktrees_dir),
    ])
    return worktrees_dir


def test_create_worktree_called_on_startup(tmp_path, monkeypatch):
    _patch_main(monkeypatch, tmp_path)
    fake_wt = _make_fake_worktree(tmp_path)

    with patch("run_analysis.create_ticket_branch_and_worktree", return_value=(True, "created")) as mock_create, \
         patch("run_analysis.get_ticket_worktree_path", return_value=fake_wt), \
         patch("run_analysis.remove_ticket_worktree", return_value=(True, "removed")):
        run_analysis.main()

    mock_create.assert_called_once()
    job_id, branch = mock_create.call_args[0][0], mock_create.call_args[0][1]
    assert job_id.startswith("analysis-testproj-")
    assert branch.startswith("analysis/analysis-testproj-")


def test_files_written_to_worktree_not_project_root(tmp_path, monkeypatch):
    _patch_main(monkeypatch, tmp_path)
    fake_wt = _make_fake_worktree(tmp_path)

    with patch("run_analysis.create_ticket_branch_and_worktree", return_value=(True, "created")), \
         patch("run_analysis.get_ticket_worktree_path", return_value=fake_wt), \
         patch("run_analysis.remove_ticket_worktree", return_value=(True, "removed")):
        run_analysis.main()

    assert (fake_wt / ".ai-dev-factory" / "deploy.yml").exists()
    assert not (tmp_path / ".ai-dev-factory" / "deploy.yml").exists()


def test_remove_worktree_called_on_success(tmp_path, monkeypatch):
    _patch_main(monkeypatch, tmp_path)
    fake_wt = _make_fake_worktree(tmp_path)

    with patch("run_analysis.create_ticket_branch_and_worktree", return_value=(True, "created")), \
         patch("run_analysis.get_ticket_worktree_path", return_value=fake_wt), \
         patch("run_analysis.remove_ticket_worktree", return_value=(True, "removed")) as mock_remove:
        run_analysis.main()

    mock_remove.assert_called_once()
    _, kwargs = mock_remove.call_args
    assert kwargs.get("force") is True


def test_remove_worktree_called_on_failure(tmp_path, monkeypatch):
    _patch_main(monkeypatch, tmp_path)
    fake_wt = _make_fake_worktree(tmp_path)
    monkeypatch.setattr(run_analysis, "_invoke_llm", lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("LLM failed")))

    with patch("run_analysis.create_ticket_branch_and_worktree", return_value=(True, "created")), \
         patch("run_analysis.get_ticket_worktree_path", return_value=fake_wt), \
         patch("run_analysis.remove_ticket_worktree", return_value=(True, "removed")) as mock_remove:
        with pytest.raises(SystemExit):
            run_analysis.main()

    mock_remove.assert_called_once()


def test_worktree_path_in_state_json(tmp_path, monkeypatch):
    _patch_main(monkeypatch, tmp_path)
    fake_wt = _make_fake_worktree(tmp_path)

    with patch("run_analysis.create_ticket_branch_and_worktree", return_value=(True, "created")), \
         patch("run_analysis.get_ticket_worktree_path", return_value=fake_wt), \
         patch("run_analysis.remove_ticket_worktree", return_value=(True, "removed")):
        run_analysis.main()

    state = json.loads((tmp_path / "state" / "analysis-testproj.json").read_text())
    assert state.get("worktree_path") == str(fake_wt)
