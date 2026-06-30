"""Tests for ticket_merge_state.is_ticket_merged (T198)."""

import importlib.util
import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

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


@pytest.fixture()
def merge_state_module(tmp_path, monkeypatch):
    """Load ticket_merge_state with a SQLite-backed runtime_db isolated under tmp_path."""
    db_path = tmp_path / ".runtime" / "test.sqlite"
    _db.init_runtime_db(db_path)

    monkeypatch.setattr(_db, "get_db_path", lambda project_id=None: db_path)

    mod_name = "_merge_state_under_test"
    spec = importlib.util.spec_from_file_location(
        mod_name,
        _TOOLS / "ticket_merge_state.py",
    )
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    sys.modules[mod_name] = mod
    try:
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
    except Exception:
        sys.modules.pop(mod_name, None)
        raise
    mod.runtime_db = _db
    return mod, db_path


def test_runtime_db_hit_returns_runtime_db_source(merge_state_module, tmp_path):
    mod, db_path = merge_state_module
    _db.upsert_ticket_runtime(db_path, "T010", pr_state="MERGED")
    result = mod.is_ticket_merged(tmp_path, "T010")
    assert result.status == "merged"
    assert result.source == "runtime_db"


def test_runtime_db_closed_pr_returns_not_merged(merge_state_module, tmp_path):
    mod, db_path = merge_state_module
    _db.upsert_ticket_runtime(db_path, "T011", pr_state="CLOSED")
    result = mod.is_ticket_merged(tmp_path, "T011")
    assert result.status == "not_merged"
    assert result.source == "runtime_db"


def test_runtime_db_open_pr_returns_not_merged(merge_state_module, tmp_path):
    mod, db_path = merge_state_module
    _db.upsert_ticket_runtime(db_path, "T012", pr_state="open")
    result = mod.is_ticket_merged(tmp_path, "T012")
    assert result.status == "not_merged"
    assert result.source == "runtime_db"


def test_github_merged_returns_merged(merge_state_module, tmp_path, monkeypatch):
    mod, db_path = merge_state_module
    _db.upsert_ticket_runtime(db_path, "T042", pr_number=9)
    monkeypatch.setattr(
        mod,
        "_gh_pr_view",
        lambda _root, pr, repo=None: {"state": "MERGED", "mergedAt": "2026-01-01"},
    )
    result = mod.is_ticket_merged(tmp_path, "T042")
    assert result.status == "merged"
    assert result.source == "github_metadata"


def test_github_open_returns_not_merged(merge_state_module, tmp_path, monkeypatch):
    mod, db_path = merge_state_module
    _db.upsert_ticket_runtime(db_path, "T043", pr_number=10)
    monkeypatch.setattr(
        mod,
        "_gh_pr_view",
        lambda _root, pr, repo=None: {"state": "OPEN", "mergedAt": None},
    )
    result = mod.is_ticket_merged(tmp_path, "T043")
    assert result.status == "not_merged"
    assert result.source == "github_metadata"


def test_ticket_without_pr_returns_not_merged(merge_state_module, tmp_path):
    mod, db_path = merge_state_module
    _db.upsert_ticket_runtime(db_path, "T001", state="PLAN_REVIEW_NEEDED")
    result = mod.is_ticket_merged(tmp_path, "T001")
    assert result.status == "not_merged"
    assert "no PR recorded" in result.reason


def test_git_history_is_not_used(merge_state_module, tmp_path, monkeypatch):
    """Commits mentioning a ticket on main must not count as merged without a PR."""
    mod, db_path = merge_state_module
    _db.upsert_ticket_runtime(db_path, "T001", state="INIT")
    monkeypatch.setattr(mod, "_gh_pr_view", MagicMock(return_value=None))
    result = mod.is_ticket_merged(tmp_path, "T001")
    assert result.status == "not_merged"
    assert result.source == "github_metadata"


def test_unknown_when_ticket_not_found(merge_state_module, tmp_path, monkeypatch):
    mod, _db_path = merge_state_module
    monkeypatch.setattr(mod, "_gh_pr_view", MagicMock(return_value=None))
    project_root = tmp_path / "not-a-repo"
    project_root.mkdir()
    result = mod.is_ticket_merged(project_root, "T999")
    assert result.status == "unknown"
    assert result.source == "unknown"


def test_pr_number_from_state_json_when_missing_in_db(merge_state_module, tmp_path, monkeypatch):
    mod, _db_path = merge_state_module
    run_dir = tmp_path / "runs" / "T050"
    run_dir.mkdir(parents=True)
    (run_dir / "state.json").write_text(
        json.dumps({"ticket_id": "T050", "pr_number": 77}),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        mod,
        "_gh_pr_view",
        lambda _root, pr, repo=None: {"state": "MERGED", "mergedAt": "2026-01-01"},
    )
    result = mod.is_ticket_merged(tmp_path, "T050")
    assert result.status == "merged"
    assert result.source == "github_metadata"
