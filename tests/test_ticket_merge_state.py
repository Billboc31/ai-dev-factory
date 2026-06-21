"""Tests for ticket_merge_state.is_ticket_merged (T198)."""

import importlib.util
import os
import subprocess
import sys
from pathlib import Path

import pytest

_TOOLS = Path(__file__).parent.parent / "tools" / "agent_runner"
sys.path.insert(0, str(_TOOLS))


def _load_sqlite_runtime_db():
    spec = importlib.util.spec_from_file_location(
        "_runtime_db_sqlite_test_merge",
        _TOOLS / "runtime_db.py",
    )
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    old = os.environ.get("RUNTIME_DB_BACKEND")
    os.environ["RUNTIME_DB_BACKEND"] = "sqlite"
    try:
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
    finally:
        if old is None:
            os.environ.pop("RUNTIME_DB_BACKEND", None)
        else:
            os.environ["RUNTIME_DB_BACKEND"] = old
    return mod


_db = _load_sqlite_runtime_db()


def _init_git_repo_with_main(tmp_path: Path) -> Path:
    """Create a small git repo with a ``main`` branch and one initial commit."""
    repo = tmp_path / "repo"
    repo.mkdir()
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True, env=env)
    (repo / "README.md").write_text("initial\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, env=env)
    subprocess.run(
        ["git", "commit", "-q", "-m", "initial"],
        cwd=repo, check=True, env=env,
    )
    return repo


def _git_commit(repo: Path, message: str) -> None:
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    sentinel = repo / f"{abs(hash(message)) % 10_000_000}.txt"
    sentinel.write_text(message + "\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, env=env)
    subprocess.run(
        ["git", "commit", "-q", "-m", message],
        cwd=repo, check=True, env=env,
    )


@pytest.fixture()
def merge_state_module(tmp_path, monkeypatch):
    """Load ticket_merge_state with a SQLite-backed runtime_db isolated under tmp_path."""
    db_path = tmp_path / ".runtime" / "test.sqlite"
    _db.init_runtime_db(db_path)

    # Force runtime_db.get_db_path to return our isolated test DB.
    monkeypatch.setattr(_db, "get_db_path", lambda: db_path)

    # Import (or reload) the module so it picks up the patched runtime_db.
    mod_name = "_merge_state_under_test"
    spec = importlib.util.spec_from_file_location(
        mod_name,
        _TOOLS / "ticket_merge_state.py",
    )
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    # Register in sys.modules so __future__-annotation dataclasses resolve names.
    sys.modules[mod_name] = mod
    try:
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
    except Exception:
        sys.modules.pop(mod_name, None)
        raise
    # Rebind its private runtime_db reference to the SQLite-mode module.
    mod.runtime_db = _db
    return mod, db_path


def test_runtime_db_hit_returns_runtime_db_source(merge_state_module, tmp_path):
    mod, db_path = merge_state_module
    _db.upsert_ticket_runtime(db_path, "T010", pr_state="MERGED")
    project_root = tmp_path
    result = mod.is_ticket_merged(project_root, "T010")
    assert result.status == "merged"
    assert result.source == "runtime_db"


def test_runtime_db_closed_pr_returns_not_merged(merge_state_module, tmp_path):
    mod, db_path = merge_state_module
    _db.upsert_ticket_runtime(db_path, "T011", pr_state="CLOSED")
    result = mod.is_ticket_merged(tmp_path, "T011")
    assert result.status == "not_merged"
    assert result.source == "runtime_db"


def test_git_fallback_hit_returns_merged(merge_state_module, tmp_path):
    mod, _db_path = merge_state_module
    repo = _init_git_repo_with_main(tmp_path)
    _git_commit(repo, "T042: implement feature")
    # No runtime DB entry, no GitHub metadata → falls through to git log.
    result = mod.is_ticket_merged(repo, "T042")
    assert result.status == "merged"
    assert result.source == "git_fallback"


def test_git_fallback_miss_returns_not_merged(merge_state_module, tmp_path):
    mod, _db_path = merge_state_module
    repo = _init_git_repo_with_main(tmp_path)
    _git_commit(repo, "unrelated commit")
    result = mod.is_ticket_merged(repo, "T099")
    assert result.status == "not_merged"
    assert result.source == "git_fallback"


def test_unknown_source_when_nothing_resolves(merge_state_module, tmp_path):
    mod, _db_path = merge_state_module
    # No DB row, no PR number, and the project_root is not a git repo.
    project_root = tmp_path / "not-a-repo"
    project_root.mkdir()
    result = mod.is_ticket_merged(project_root, "T999")
    assert result.status == "unknown"
    assert result.source == "unknown"
