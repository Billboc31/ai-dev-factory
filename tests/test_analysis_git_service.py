"""Tests for analysis_git_service — branch/PR Git operations."""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools" / "agent_runner"))

from analysis_git_service import commit_and_push  # noqa: E402

_PR_URL = "https://github.com/org/repo/pull/1"


def _completed(stdout: str = "", returncode: int = 0) -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess([], returncode, stdout=stdout, stderr="")


def test_branch_name_format(tmp_path, monkeypatch):
    def mock_run(cmd, **kwargs):
        if isinstance(cmd, list) and "list" in cmd:
            return _completed(stdout="[]")
        if isinstance(cmd, list) and "create" in cmd:
            return _completed(stdout=_PR_URL)
        return _completed()

    monkeypatch.setattr(
        "analysis_git_service.subprocess.run", mock_run
    )

    branch, _ = commit_and_push(tmp_path, "proj1")

    assert re.match(r"^ai-analysis/proj1-\d{8}-\d{6}$", branch), f"unexpected branch: {branch!r}"


def test_pr_created_on_new_branch(tmp_path, monkeypatch):
    calls = []

    def mock_run(cmd, **kwargs):
        if isinstance(cmd, list):
            calls.append(cmd)
            if "list" in cmd:
                return _completed(stdout="[]")
            if "create" in cmd:
                return _completed(stdout=_PR_URL)
        return _completed()

    monkeypatch.setattr("analysis_git_service.subprocess.run", mock_run)

    branch, pr_url = commit_and_push(tmp_path, "proj1")

    create_calls = [c for c in calls if isinstance(c, list) and "create" in c]
    assert create_calls, "gh pr create was not called"
    assert pr_url == _PR_URL


def test_pr_updated_on_existing_branch(tmp_path, monkeypatch):
    calls = []

    def mock_run(cmd, **kwargs):
        if isinstance(cmd, list):
            calls.append(cmd)
            if "list" in cmd:
                return _completed(stdout=json.dumps([{"url": _PR_URL}]))
            if "edit" in cmd:
                return _completed()
        return _completed()

    monkeypatch.setattr("analysis_git_service.subprocess.run", mock_run)

    branch, pr_url = commit_and_push(tmp_path, "proj1")

    edit_calls = [c for c in calls if isinstance(c, list) and "edit" in c]
    create_calls = [c for c in calls if isinstance(c, list) and "create" in c]
    assert edit_calls, "gh pr edit was not called"
    assert not create_calls, "gh pr create should not be called when PR already exists"
    assert pr_url == _PR_URL
