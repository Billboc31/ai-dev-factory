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
        lambda root, dep, **_kw: _MergeResult(status="not_merged", source="runtime_db"),
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
        lambda root, dep, **_kw: _MergeResult(status="unknown", source="unknown"),
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
        lambda root, dep, **_kw: _MergeResult(status="not_merged", source="runtime_db"),
    )
    evaluator.run_evaluation(
        db, "T010",
        "depends on T100 before we can ship.",
        git_repo,
    )
    row = _db.get_ticket_readiness(db, "T010")
    assert row["readiness_status"] == "blocked"
    assert "Dependency T100 not merged" in row["blocking_reasons_json"]


def test_dependency_markdown_section_blocks(evaluator, db, git_repo, monkeypatch):
    _set_completed_intelligence(db, "T012")
    monkeypatch.setattr(
        evaluator,
        "is_ticket_merged",
        lambda root, dep, **_kw: _MergeResult(status="not_merged", source="runtime_db"),
    )
    content = """# T012

## Depends on
- T010 - foundation ticket
"""
    evaluator.run_evaluation(db, "T012", content, git_repo)
    row = _db.get_ticket_readiness(db, "T012")
    assert row["readiness_status"] == "blocked"
    assert "Dependency T010 not merged" in row["blocking_reasons_json"]


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


# ── T213 entry-prerequisite contract guarantees ──────────────────────────────


_FORBIDDEN_BLOCKER_TOKENS = ("approval", "plan review", "execution rule", "ready_to_take")


def _assert_no_forbidden_blocker_tokens(blocking_reasons: list[str]) -> None:
    """Assert that every blocker passes the entry-prerequisite contract."""
    for reason in blocking_reasons:
        lowered = reason.lower()
        for token in _FORBIDDEN_BLOCKER_TOKENS:
            assert token not in lowered, (
                f"blocker {reason!r} contains forbidden token {token!r} — "
                "it belongs to a later workflow stage"
            )


def test_missing_human_execution_approval_does_not_block(
    evaluator, db, git_repo, monkeypatch
):
    """A pending future execution approval is a warning, not a blocker."""
    _set_completed_intelligence(db, "T020")

    original_get = evaluator.runtime_db.get_ticket_intelligence

    def _fake_get(db_path, ticket_id):
        row = original_get(db_path, ticket_id)
        if row is not None and ticket_id == "T020":
            row = dict(row)
            row["requires_human_execution_approval"] = 1
        return row

    monkeypatch.setattr(evaluator.runtime_db, "get_ticket_intelligence", _fake_get)

    evaluator.run_evaluation(db, "T020", "no deps", git_repo)
    row = _db.get_ticket_readiness(db, "T020")
    assert row["readiness_status"] == "ready_candidate"
    assert row["ready_candidate"] == 1
    assert row["blocking_reasons_json"] == []
    assert "Human execution approval may be required later" in row["warnings_json"]
    assert row["approval_check_status"] == "advisory"


@pytest.mark.parametrize(
    "downstream_state",
    ["PLAN_REVIEW_NEEDED", "PLAN_FIX_REQUIRED", "PLAN_APPROVED"],
)
def test_planner_review_states_do_not_block_readiness(
    evaluator, db, git_repo, downstream_state
):
    """Planner-review states never produce readiness blockers."""
    _set_completed_intelligence(db, "T021", requires_human_plan_review=1)

    run_dir = git_repo / "runs" / "T021"
    run_dir.mkdir(parents=True)
    (run_dir / "state.json").write_text(
        f'{{"ticket_id": "T021", "state": "{downstream_state}"}}',
        encoding="utf-8",
    )

    evaluator.run_evaluation(db, "T021", "no deps", git_repo)
    row = _db.get_ticket_readiness(db, "T021")
    assert row["readiness_status"] in {"ready_candidate", "ready_to_take"}
    _assert_no_forbidden_blocker_tokens(row["blocking_reasons_json"])


def test_execution_rules_state_does_not_block_readiness(
    evaluator, db, git_repo, monkeypatch
):
    """Even if execution rules would deny later, readiness ignores them."""
    _set_completed_intelligence(db, "T022")

    # Force a synthetic rule-evaluation row that, if consulted, would
    # forbid execution. Readiness must remain ready_candidate.
    def _denied_rule_evaluation(*_args, **_kwargs):
        return {
            "eligibility_status": "blocked",
            "failed_rules_json": [{"rule_key": "deny-all", "reason": "denied"}],
        }

    if hasattr(evaluator.runtime_db, "get_ticket_rule_evaluation"):
        monkeypatch.setattr(
            evaluator.runtime_db, "get_ticket_rule_evaluation", _denied_rule_evaluation
        )

    evaluator.run_evaluation(db, "T022", "no deps", git_repo)
    row = _db.get_ticket_readiness(db, "T022")
    assert row["readiness_status"] == "ready_candidate"
    _assert_no_forbidden_blocker_tokens(row["blocking_reasons_json"])


def test_blocking_reasons_only_from_entry_prerequisites(
    evaluator, db, git_repo, monkeypatch
):
    """Every blocker passes ``_is_entry_prerequisite_reason``."""
    # Force a forbidden blocker to slip in upstream and verify the guard
    # drops it rather than letting it block readiness.
    monkeypatch.setattr(
        evaluator,
        "_check_intelligence",
        lambda *_a, **_k: ("failed", "Human plan approval missing"),
    )
    monkeypatch.setattr(
        evaluator,
        "_check_dependencies",
        lambda *_a, **_k: ("passed", []),
    )

    evaluator.run_evaluation(db, "T023", "no deps", git_repo)
    row = _db.get_ticket_readiness(db, "T023")
    # The forbidden blocker is dropped, so nothing remains in blockers.
    assert row["blocking_reasons_json"] == []
    _assert_no_forbidden_blocker_tokens(row["blocking_reasons_json"])


def test_is_entry_prerequisite_reason_accepts_valid_blockers(evaluator):
    assert evaluator._is_entry_prerequisite_reason("Missing Ticket Intelligence analysis")
    assert evaluator._is_entry_prerequisite_reason("Dependency T010 not merged")
    assert evaluator._is_entry_prerequisite_reason("Dependency T010 merge state unknown")


def test_is_entry_prerequisite_reason_rejects_later_stage_blockers(evaluator):
    assert not evaluator._is_entry_prerequisite_reason("Human plan approval missing")
    assert not evaluator._is_entry_prerequisite_reason("Human execution approval required")
    assert not evaluator._is_entry_prerequisite_reason("Plan review pending")
    assert not evaluator._is_entry_prerequisite_reason("Blocked by execution rule deny-all")
    assert not evaluator._is_entry_prerequisite_reason("Awaiting ready_to_take promotion")


# ── T218 dependency union with global dependency analyzer ────────────────────


def test_dependency_analysis_dep_included_in_union(evaluator, db, git_repo, monkeypatch):
    """A dep only present in ticket_dependency_analysis is still enforced."""
    _set_completed_intelligence(db, "T030")
    # Pre-populate a global dependency analysis row that adds T999 — a dep
    # absent from both the markdown body AND the intelligence hints.
    _db.upsert_dependency_analysis(
        db,
        ticket_id="T030",
        batch_id="B0001",
        depends_on=["T999"],
        blocks=[],
        parallel_group=None,
        conflicting_tickets=[],
        execution_phase=None,
        relationship_classifications=[],
        analyzed_at="2026-06-30T12:00:00Z",
    )

    monkeypatch.setattr(
        evaluator,
        "is_ticket_merged",
        lambda root, dep, **_kw: _MergeResult(status="not_merged", source="runtime_db"),
    )

    evaluator.run_evaluation(db, "T030", "no markdown deps", git_repo)
    row = _db.get_ticket_readiness(db, "T030")
    assert row["readiness_status"] == "blocked"
    assert "Dependency T999 not merged" in row["blocking_reasons_json"]
