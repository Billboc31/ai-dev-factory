"""Tests for ticket_readiness_evaluator.run_evaluation (T198)."""

import importlib.util
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import pytest

_TOOLS = Path(__file__).parent.parent / "tools" / "agent_runner"
sys.path.insert(0, str(_TOOLS))


def _load_sqlite_runtime_db():
    spec = importlib.util.spec_from_file_location(
        "_runtime_db_sqlite_test_evaluator",
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


def _load_evaluator(db_module):
    """Load the evaluator module and rebind its runtime_db to the SQLite test module."""
    mod_name = "_readiness_evaluator_under_test"
    spec = importlib.util.spec_from_file_location(
        mod_name,
        _TOOLS / "ticket_readiness_evaluator.py",
    )
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    sys.modules[mod_name] = mod
    try:
        spec.loader.exec_module(mod)  # type: ignore[union-attr]
    except Exception:
        sys.modules.pop(mod_name, None)
        raise
    mod.runtime_db = db_module
    return mod


@dataclass
class _MergeResult:
    status: str
    source: str = "runtime_db"
    reason: str = ""


@pytest.fixture()
def evaluator(monkeypatch, tmp_path):
    mod = _load_evaluator(_db)
    return mod


@pytest.fixture()
def db(tmp_path: Path) -> Path:
    db_path = tmp_path / ".runtime" / "test.sqlite"
    _db.init_runtime_db(db_path)
    return db_path


@pytest.fixture()
def git_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    subprocess.run(["git", "init", "-q", "-b", "main"], cwd=repo, check=True, env=env)
    (repo / "README.md").write_text("initial\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True, env=env)
    subprocess.run(["git", "commit", "-q", "-m", "initial"], cwd=repo, check=True, env=env)
    return repo


def _set_completed_intelligence(db_path: Path, ticket_id: str, **fields) -> None:
    _db.upsert_ticket_intelligence(db_path, ticket_id, analysis_status="completed", **fields)


def test_missing_intelligence_blocks(evaluator, db, git_repo):
    evaluator.run_evaluation(db, "T001", "ticket body without dependencies", git_repo)
    row = _db.get_ticket_readiness(db, "T001")
    assert row is not None
    assert row["readiness_status"] == "blocked"
    assert "Missing Ticket Intelligence analysis" in row["blocking_reasons_json"]


def test_dependency_not_merged_blocks(evaluator, db, git_repo, monkeypatch):
    _set_completed_intelligence(db, "T002")

    monkeypatch.setattr(
        evaluator,
        "is_ticket_merged",
        lambda root, dep: _MergeResult(status="not_merged", source="runtime_db"),
    )

    evaluator.run_evaluation(
        db, "T002",
        "This ticket depends on T010 — needs it merged first.",
        git_repo,
    )
    row = _db.get_ticket_readiness(db, "T002")
    assert row["readiness_status"] == "blocked"
    assert "Dependency T010 not merged" in row["blocking_reasons_json"]
    assert row["dependency_check_status"] == "failed"


def test_dependency_unknown_blocks(evaluator, db, git_repo, monkeypatch):
    _set_completed_intelligence(db, "T003")

    monkeypatch.setattr(
        evaluator,
        "is_ticket_merged",
        lambda root, dep: _MergeResult(status="unknown", source="unknown"),
    )

    evaluator.run_evaluation(
        db, "T003",
        "After T020 we can ship.",
        git_repo,
    )
    row = _db.get_ticket_readiness(db, "T003")
    assert row["readiness_status"] == "blocked"
    assert "Dependency T020 merge state unknown" in row["blocking_reasons_json"]
    assert row["dependency_check_status"] == "failed"


def test_missing_human_approval_emits_warning_not_block(evaluator, db, git_repo):
    """Readiness must not block on a future human plan approval.

    A ticket whose intelligence flags ``requires_human_plan_review`` but has
    no approval marker yet is still ``ready_candidate``. The pending review is
    surfaced as a non-blocking advisory warning only.
    """
    _set_completed_intelligence(db, "T004", requires_human_plan_review=1)
    evaluator.run_evaluation(db, "T004", "no dependencies", git_repo)
    row = _db.get_ticket_readiness(db, "T004")
    assert row["readiness_status"] == "ready_candidate"
    assert row["ready_candidate"] == 1
    assert "Human plan approval missing" not in row["blocking_reasons_json"]
    assert "Human plan review may be required later" in row["warnings_json"]
    assert row["approval_check_status"] == "advisory"
    assert row["human_approval_required"] == 1
    assert row["human_approval_present"] == 0


def test_human_approval_present_via_marker_file_passes(evaluator, db, git_repo):
    _set_completed_intelligence(db, "T005", requires_human_plan_review=1)
    run_dir = git_repo / "runs" / "T005"
    run_dir.mkdir(parents=True)
    (run_dir / "plan-approved.md").write_text("approved by human", encoding="utf-8")

    evaluator.run_evaluation(db, "T005", "no dependencies", git_repo)
    row = _db.get_ticket_readiness(db, "T005")
    assert row["readiness_status"] == "ready_candidate"
    assert row["approval_check_status"] == "passed"
    assert row["human_approval_present"] == 1
    assert "Human plan review may be required later" not in row["warnings_json"]


def test_intelligence_missing_still_blocks(evaluator, db, git_repo):
    """Regression guard: missing intelligence is a workflow-entry blocker."""
    evaluator.run_evaluation(db, "T009", "no deps", git_repo)
    row = _db.get_ticket_readiness(db, "T009")
    assert row["readiness_status"] == "blocked"
    assert "Missing Ticket Intelligence analysis" in row["blocking_reasons_json"]
    assert row["ready_candidate"] == 0


def test_dependency_missing_still_blocks(evaluator, db, git_repo, monkeypatch):
    """Regression guard: an unmerged dependency is a workflow-entry blocker."""
    _set_completed_intelligence(db, "T010")
    monkeypatch.setattr(
        evaluator,
        "is_ticket_merged",
        lambda root, dep: _MergeResult(status="not_merged", source="runtime_db"),
    )
    evaluator.run_evaluation(
        db, "T010",
        "depends on T100 before we can ship.",
        git_repo,
    )
    row = _db.get_ticket_readiness(db, "T010")
    assert row["readiness_status"] == "blocked"
    assert "Dependency T100 not merged" in row["blocking_reasons_json"]


def test_warnings_persist_alongside_ready_candidate(evaluator, db, git_repo):
    """A ticket can be ready_candidate AND carry advisory warnings."""
    _set_completed_intelligence(db, "T011", requires_human_plan_review=1)
    evaluator.run_evaluation(db, "T011", "no deps", git_repo)
    row = _db.get_ticket_readiness(db, "T011")
    assert row["readiness_status"] == "ready_candidate"
    assert row["ready_candidate"] == 1
    assert row["warnings_json"]
    assert "Human plan review may be required later" in row["warnings_json"]


def test_all_checks_pass_yields_ready_candidate(evaluator, db, git_repo, monkeypatch):
    _set_completed_intelligence(db, "T006")
    # No declared deps in the ticket → dependency check trivially passes.
    evaluator.run_evaluation(
        db, "T006",
        "Simple ticket with no prerequisites.",
        git_repo,
    )
    row = _db.get_ticket_readiness(db, "T006")
    assert row["readiness_status"] == "ready_candidate"
    assert row["ready_candidate"] == 1
    assert row["blocking_reasons_json"] == []
    assert row["evaluated_at"] is not None
    assert row["context_freshness_status"] == "fresh"
    # main_sha_when_evaluated populated by `git rev-parse main`.
    assert row["main_sha_when_evaluated"]
    assert len(row["main_sha_when_evaluated"]) >= 7


def test_context_freshness_unknown_when_no_git(evaluator, db, tmp_path):
    _set_completed_intelligence(db, "T007")
    not_a_repo = tmp_path / "no-git"
    not_a_repo.mkdir()
    evaluator.run_evaluation(db, "T007", "no deps", not_a_repo)
    row = _db.get_ticket_readiness(db, "T007")
    assert row["context_freshness_status"] == "unknown"
    assert row["main_sha_when_evaluated"] in (None, "")


def test_evaluator_persists_failed_on_unexpected_error(evaluator, db, git_repo, monkeypatch):
    """If a low-level helper unexpectedly raises, the evaluator persists failed."""
    _set_completed_intelligence(db, "T008")

    def _boom(*args, **kwargs):
        raise RuntimeError("simulated crash")

    monkeypatch.setattr(evaluator, "_check_context_freshness", _boom)

    evaluator.run_evaluation(db, "T008", "no deps", git_repo)
    row = _db.get_ticket_readiness(db, "T008")
    assert row["readiness_status"] == "failed"
    assert any("simulated crash" in w for w in row["warnings_json"])
