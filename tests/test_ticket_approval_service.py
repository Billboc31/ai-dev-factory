"""Tests for ticket_approval_service (T199)."""

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
        "_runtime_db_sqlite_test_approvals_service",
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


def _load_service(db_module):
    mod_name = "_approval_service_under_test"
    spec = importlib.util.spec_from_file_location(
        mod_name,
        _TOOLS / "ticket_approval_service.py",
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


def _load_evaluator(db_module):
    mod_name = "_readiness_evaluator_under_test_for_approvals"
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
def service():
    return _load_service(_db)


@pytest.fixture()
def db(tmp_path: Path) -> Path:
    db_path = tmp_path / ".runtime" / "test.sqlite"
    _db.init_runtime_db(db_path)
    return db_path


def _seed_ready_candidate(db_path: Path, ticket_id: str) -> None:
    _db.upsert_ticket_readiness(
        db_path,
        ticket_id,
        readiness_status="ready_candidate",
        ready_candidate=1,
        blocking_reasons_json=[],
    )


def _seed_not_started(db_path: Path, ticket_id: str) -> None:
    _db.upsert_ticket_readiness(
        db_path,
        ticket_id,
        readiness_status="not_started",
        ready_candidate=0,
    )


# ── request_execution_approval ────────────────────────────────────────────────

def test_request_creates_pending_row(service, db):
    row = service.request_execution_approval(db, "T001")
    assert row["approval_status"] == "pending"
    assert row["approval_type"] == "execution"
    rows = service.get_ticket_approvals(db, "T001")
    assert len(rows) == 1


def test_request_idempotent_when_pending_exists(service, db):
    first = service.request_execution_approval(db, "T001")
    second = service.request_execution_approval(db, "T001")
    assert first["id"] == second["id"]
    rows = service.get_ticket_approvals(db, "T001")
    assert len(rows) == 1


# ── approve_execution ─────────────────────────────────────────────────────────

def test_approve_on_ready_candidate_promotes_to_ready_to_take(service, db):
    _seed_ready_candidate(db, "T010")
    row = service.approve_execution(db, "T010", approved_by="pierre", comment="safe")
    assert row["approval_status"] == "approved"
    assert row["approved_by"] == "pierre"

    readiness = _db.get_ticket_readiness(db, "T010")
    assert readiness["readiness_status"] == "ready_to_take"

    history = service.get_ticket_approvals(db, "T010")
    assert len(history) == 1


def test_approve_idempotent_returns_same_row(service, db):
    _seed_ready_candidate(db, "T011")
    first = service.approve_execution(db, "T011", approved_by="pierre")
    second = service.approve_execution(db, "T011", approved_by="pierre")
    assert first["id"] == second["id"]
    history = service.get_ticket_approvals(db, "T011")
    assert len(history) == 1
    readiness = _db.get_ticket_readiness(db, "T011")
    assert readiness["readiness_status"] == "ready_to_take"


def test_approve_after_reject_raises_contradictory(service, db):
    _seed_ready_candidate(db, "T012")
    service.reject_execution(db, "T012", approved_by="pierre")
    with pytest.raises(ValueError, match="contradictory_transition"):
        service.approve_execution(db, "T012", approved_by="pierre")


def test_approve_without_ready_candidate_raises_invalid_state(service, db):
    _seed_not_started(db, "T013")
    with pytest.raises(ValueError, match="invalid_state"):
        service.approve_execution(db, "T013", approved_by="pierre")


def test_approve_with_no_readiness_row_raises_invalid_state(service, db):
    with pytest.raises(ValueError, match="invalid_state"):
        service.approve_execution(db, "T014", approved_by="pierre")


# ── reject_execution ──────────────────────────────────────────────────────────

def test_reject_on_ready_candidate_blocks_with_reason(service, db):
    _seed_ready_candidate(db, "T020")
    row = service.reject_execution(db, "T020", approved_by="pierre", comment="risky")
    assert row["approval_status"] == "rejected"

    readiness = _db.get_ticket_readiness(db, "T020")
    assert readiness["readiness_status"] == "blocked"
    reasons = readiness["blocking_reasons_json"]
    assert "Execution approval rejected by pierre" in reasons


def test_reject_idempotent_does_not_duplicate_reason(service, db):
    _seed_ready_candidate(db, "T021")
    first = service.reject_execution(db, "T021", approved_by="pierre")
    second = service.reject_execution(db, "T021", approved_by="pierre")
    assert first["id"] == second["id"]
    history = service.get_ticket_approvals(db, "T021")
    assert len(history) == 1
    readiness = _db.get_ticket_readiness(db, "T021")
    reasons = readiness["blocking_reasons_json"]
    assert reasons.count("Execution approval rejected by pierre") == 1


def test_reject_after_approve_raises_contradictory(service, db):
    _seed_ready_candidate(db, "T022")
    service.approve_execution(db, "T022", approved_by="pierre")
    with pytest.raises(ValueError, match="contradictory_transition"):
        service.reject_execution(db, "T022", approved_by="pierre")


def test_reject_without_ready_candidate_raises_invalid_state(service, db):
    _seed_not_started(db, "T023")
    with pytest.raises(ValueError, match="invalid_state"):
        service.reject_execution(db, "T023", approved_by="pierre")


# ── compute_execution_eligibility ────────────────────────────────────────────

def test_eligibility_promotes_to_ready_to_take_when_approved(service, db):
    _seed_ready_candidate(db, "T030")
    service.approve_execution(db, "T030", approved_by="pierre")
    assert service.compute_execution_eligibility(db, "T030") == "ready_to_take"


def test_eligibility_reports_blocked_when_rejected(service, db):
    _seed_ready_candidate(db, "T031")
    service.reject_execution(db, "T031", approved_by="pierre")
    assert service.compute_execution_eligibility(db, "T031") == "blocked"


def test_eligibility_passes_through_when_no_decision(service, db):
    _seed_ready_candidate(db, "T032")
    assert service.compute_execution_eligibility(db, "T032") == "ready_candidate"


# ── auto_approve_plan ────────────────────────────────────────────────────────

def test_auto_approve_plan_inserts_expected_audit_row(service, db):
    row = service.auto_approve_plan(db, "T050")
    assert row["approval_type"] == "plan"
    assert row["approval_status"] == "approved"
    assert row["approved_by"] == "SYSTEM"
    assert row["approval_comment"] == "PROJECT_SETTING"
    assert row["approved_at"] is not None
    history = service.get_ticket_approvals(db, "T050")
    plan_rows = [r for r in history if r["approval_type"] == "plan"]
    assert len(plan_rows) == 1


def test_auto_approve_plan_is_idempotent(service, db):
    first = service.auto_approve_plan(db, "T051")
    second = service.auto_approve_plan(db, "T051")
    assert first["id"] == second["id"]
    plan_rows = [
        r for r in service.get_ticket_approvals(db, "T051") if r["approval_type"] == "plan"
    ]
    assert len(plan_rows) == 1


def test_auto_approve_plan_accepts_custom_reason(service, db):
    row = service.auto_approve_plan(db, "T052", reason="DEMO_MODE")
    assert row["approval_comment"] == "DEMO_MODE"


def test_auto_approve_plan_does_not_touch_execution_row(service, db):
    _seed_ready_candidate(db, "T053")
    service.approve_execution(db, "T053", approved_by="pierre")
    service.auto_approve_plan(db, "T053")

    history = service.get_ticket_approvals(db, "T053")
    plan_rows = [r for r in history if r["approval_type"] == "plan"]
    exec_rows = [r for r in history if r["approval_type"] == "execution"]
    assert len(plan_rows) == 1
    assert len(exec_rows) == 1
    assert exec_rows[0]["approved_by"] == "pierre"


# ── re-evaluation preserves ready_to_take ────────────────────────────────────

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


def test_reevaluation_preserves_ready_to_take_after_approval(service, db, git_repo):
    _db.upsert_ticket_intelligence(db, "T040", analysis_status="completed")
    _seed_ready_candidate(db, "T040")
    service.approve_execution(db, "T040", approved_by="pierre")

    evaluator = _load_evaluator(_db)
    evaluator.run_evaluation(db, "T040", "no dependencies here", git_repo)

    row = _db.get_ticket_readiness(db, "T040")
    assert row["readiness_status"] == "ready_to_take"
