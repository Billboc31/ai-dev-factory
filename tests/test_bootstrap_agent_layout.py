"""Unit and integration tests for bootstrap_agent_layout."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.agent_runner.bootstrap_agent_layout import (
    SETUP_BRANCH,
    INTEGRATION_BRANCH,
    _ensure_local_main_baseline,
    _generate_global_context,
    _layout_exists,
    bootstrap_agent_layout,
)


def _init_git_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init"], cwd=path, capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=path, capture_output=True, check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=path, capture_output=True, check=True,
    )
    (path / "README.md").write_text("# test\n", encoding="utf-8")
    subprocess.run(["git", "add", "-A"], cwd=path, capture_output=True, check=True)
    subprocess.run(
        ["git", "commit", "-m", "init"],
        cwd=path, capture_output=True, check=True,
    )
    return path


def _init_empty_git_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init"], cwd=path, capture_output=True, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=path, capture_output=True, check=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=path, capture_output=True, check=True,
    )
    return path


# ── unit tests — helpers ──────────────────────────────────────────────────────

def test_layout_exists_when_ai_dir_present(tmp_path):
    (tmp_path / "ai").mkdir()
    assert _layout_exists(tmp_path) is True


def test_layout_exists_false_when_no_ai_dir(tmp_path):
    assert _layout_exists(tmp_path) is False


def test_generate_global_context_contains_project_id(tmp_path):
    content = _generate_global_context("my-proj", "My Proj", "https://github.com/org/repo")
    assert "my-proj" in content


def test_generate_global_context_contains_repo_url(tmp_path):
    content = _generate_global_context("my-proj", "My Proj", "https://github.com/org/repo")
    assert "https://github.com/org/repo" in content


def test_generate_global_context_contains_folder_list(tmp_path):
    content = _generate_global_context("p", "P", "url")
    assert "ai/" in content
    assert "docs/" in content
    assert "prompts/" in content
    assert "runs/" in content
    assert "tickets/" in content


def test_ensure_local_main_baseline_on_empty_repo(tmp_path):
    repo = _init_empty_git_repo(tmp_path / "empty")
    _ensure_local_main_baseline(repo)

    branch = subprocess.run(
        ["git", "symbolic-ref", "--short", "HEAD"],
        cwd=repo, capture_output=True, text=True, check=True,
    )
    assert branch.stdout.strip() == INTEGRATION_BRANCH
    log = subprocess.run(
        ["git", "log", "--oneline", "-1"],
        cwd=repo, capture_output=True, text=True, check=True,
    )
    assert "initial commit" in log.stdout


def test_bootstrap_virgin_repo_creates_local_main(tmp_path):
    repo = _init_empty_git_repo(tmp_path / "virgin")
    with patch("tools.agent_runner.bootstrap_agent_layout._get_remote_url", return_value=None):
        result = bootstrap_agent_layout(repo, "virgin-project")

    assert result["error"] is None
    branches = subprocess.run(
        ["git", "branch", "--list", INTEGRATION_BRANCH, SETUP_BRANCH],
        cwd=repo, capture_output=True, text=True, check=True,
    )
    assert INTEGRATION_BRANCH in branches.stdout
    assert SETUP_BRANCH in branches.stdout


def test_bootstrap_pushes_main_before_setup_branch(tmp_path):
    repo = _init_empty_git_repo(tmp_path / "remote-virgin")
    fake_url = "https://github.com/org/virgin.git"
    push_targets: list[str] = []

    def fake_git(args, cwd):
        if args[:2] == ["remote", "get-url"]:
            r = MagicMock()
            r.returncode = 0
            r.stdout = fake_url
            return r
        if args[:2] == ["ls-remote", "--heads"]:
            r = MagicMock()
            r.returncode = 0
            r.stdout = ""
            return r
        if args[0] == "push":
            push_targets.append(args[-1])
            r = MagicMock()
            r.returncode = 0
            r.stdout = ""
            r.stderr = ""
            return r
        return subprocess.run(["git"] + args, cwd=cwd, capture_output=True, text=True)

    with patch("tools.agent_runner.bootstrap_agent_layout._run_git", side_effect=fake_git):
        with patch("tools.agent_runner.bootstrap_agent_layout._get_remote_url", return_value=fake_url):
            with patch("subprocess.run") as mock_run:
                gh_result = MagicMock()
                gh_result.returncode = 0
                gh_result.stdout = "https://github.com/org/virgin/pull/1\n"
                gh_result.stderr = ""
                mock_run.return_value = gh_result
                result = bootstrap_agent_layout(repo, "virgin-project")

    assert result["error"] is None
    assert push_targets[0] == INTEGRATION_BRANCH
    assert push_targets[1] == SETUP_BRANCH


# ── integration tests — real git repo ────────────────────────────────────────

def test_bootstrap_creates_all_five_folders(tmp_path):
    repo = _init_git_repo(tmp_path / "target")
    with patch("tools.agent_runner.bootstrap_agent_layout._get_remote_url", return_value=None):
        result = bootstrap_agent_layout(repo, "target-project")

    assert result["error"] is None or "nothing to commit" not in (result["error"] or "")
    for folder in ("ai", "docs", "prompts", "runs", "tickets"):
        assert (repo / folder).is_dir(), f"missing folder: {folder}"


def test_bootstrap_creates_global_context(tmp_path):
    repo = _init_git_repo(tmp_path / "target")
    with patch("tools.agent_runner.bootstrap_agent_layout._get_remote_url", return_value=None):
        bootstrap_agent_layout(repo, "my-project")

    ctx = repo / "docs" / "ai" / "global-context.md"
    assert ctx.exists()
    content = ctx.read_text(encoding="utf-8")
    assert "my-project" in content


def test_bootstrap_creates_setup_branch(tmp_path):
    repo = _init_git_repo(tmp_path / "target")
    with patch("tools.agent_runner.bootstrap_agent_layout._get_remote_url", return_value=None):
        result = bootstrap_agent_layout(repo, "my-project")

    assert result["branch"] == SETUP_BRANCH
    branch_result = subprocess.run(
        ["git", "branch", "--list", SETUP_BRANCH],
        cwd=repo, capture_output=True, text=True,
    )
    assert SETUP_BRANCH in branch_result.stdout


def test_bootstrap_commits_on_setup_branch(tmp_path):
    repo = _init_git_repo(tmp_path / "target")
    with patch("tools.agent_runner.bootstrap_agent_layout._get_remote_url", return_value=None):
        bootstrap_agent_layout(repo, "my-project")

    log = subprocess.run(
        ["git", "log", "--oneline", SETUP_BRANCH],
        cwd=repo, capture_output=True, text=True,
    )
    assert "add AI Dev Factory agent workspace" in log.stdout


def test_bootstrap_default_branch_unchanged(tmp_path):
    repo = _init_git_repo(tmp_path / "target")
    with patch("tools.agent_runner.bootstrap_agent_layout._get_remote_url", return_value=None):
        bootstrap_agent_layout(repo, "my-project")

    current = subprocess.run(
        ["git", "symbolic-ref", "--short", "HEAD"],
        cwd=repo, capture_output=True, text=True,
    )
    assert current.stdout.strip() == SETUP_BRANCH


def test_bootstrap_no_remote_returns_no_pr_url(tmp_path):
    repo = _init_git_repo(tmp_path / "target")
    with patch("tools.agent_runner.bootstrap_agent_layout._get_remote_url", return_value=None):
        result = bootstrap_agent_layout(repo, "my-project")

    assert result["pr_url"] is None
    assert result["pr_number"] is None
    assert result["error"] is None


def test_bootstrap_skips_when_ai_dir_exists(tmp_path):
    repo = _init_git_repo(tmp_path / "target")
    (repo / "ai").mkdir()

    result = bootstrap_agent_layout(repo, "my-project")

    assert result["branch"] is None
    assert result["pr_url"] is None
    assert result["error"] is None


def test_bootstrap_is_idempotent(tmp_path):
    repo = _init_git_repo(tmp_path / "target")
    with patch("tools.agent_runner.bootstrap_agent_layout._get_remote_url", return_value=None):
        r1 = bootstrap_agent_layout(repo, "my-project")
        r2 = bootstrap_agent_layout(repo, "my-project")

    assert r1["branch"] == SETUP_BRANCH
    assert r2["branch"] is None
    assert r2["error"] is None


def test_bootstrap_pr_creation_failure_captured(tmp_path):
    repo = _init_git_repo(tmp_path / "target")
    fake_url = "https://github.com/org/repo.git"

    def fake_git(args, cwd):
        if args[:2] == ["remote", "get-url"]:
            r = MagicMock()
            r.returncode = 0
            r.stdout = fake_url
            return r
        if args[:2] == ["ls-remote", "--heads"]:
            r = MagicMock()
            r.returncode = 0
            r.stdout = ""
            return r
        if args[0] == "push":
            r = MagicMock()
            r.returncode = 0
            r.stdout = ""
            r.stderr = ""
            return r
        import subprocess as _sp
        return _sp.run(["git"] + args, cwd=cwd, capture_output=True, text=True)

    gh_result = MagicMock()
    gh_result.returncode = 1
    gh_result.stdout = ""
    gh_result.stderr = "gh: not authenticated"

    with patch("tools.agent_runner.bootstrap_agent_layout._run_git", side_effect=fake_git):
        with patch(
            "tools.agent_runner.bootstrap_agent_layout._get_remote_url",
            return_value=fake_url,
        ):
            with patch("subprocess.run", return_value=gh_result):
                result = bootstrap_agent_layout(repo, "my-project")

    assert isinstance(result, dict)
    assert "error" in result
    assert "branch" in result
