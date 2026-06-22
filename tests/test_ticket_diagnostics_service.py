"""Tests for the ticket_diagnostics service (T203)."""

import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest

_TOOLS = Path(__file__).parent.parent / "tools" / "agent_runner"
sys.path.insert(0, str(_TOOLS))


def _load_sqlite_runtime_db():
    spec = importlib.util.spec_from_file_location(
        "_runtime_db_sqlite_diag_service",
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


def _load_diagnostics():
    """Load ticket_diagnostics with the test SQLite runtime_db injected."""
    spec = importlib.util.spec_from_file_location(
        "_ticket_diagnostics_test_module",
        _TOOLS / "ticket_diagnostics.py",
    )
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    mod.runtime_db = _db  # ensure module uses our SQLite-only runtime_db
    # ticket_approval_service also imports runtime_db at module level; rebind.
    if hasattr(mod, "ticket_approval_service"):
        mod.ticket_approval_service.runtime_db = _db
    return mod


_diag = _load_diagnostics()


@pytest.fixture()
def db(tmp_path: Path) -> Path:
    db_path = tmp_path / ".runtime" / "test.sqlite"
    _db.init_runtime_db(db_path)
    return db_path


def _write_ticket(project_root: Path, ticket_id: str, state: str = "PLAN_APPROVED") -> None:
    run_dir = project_root / "runs" / ticket_id
    run_dir.mkdir(parents=True)
    (run_dir / "state.json").write_text(
        json.dumps({"ticket_id": ticket_id, "state": state, "branch": f"ticket/{ticket_id}"}),
        encoding="utf-8",
    )
    (run_dir / "ticket.md").write_text(f"# {ticket_id}\n", encoding="utf-8")


def test_missing_ticket_returns_error_severity(tmp_path, db):
    result = _diag.diagnose_ticket(db, tmp_path, "T999", persist=False)
    assert result["ticket_id"] == "T999"
    assert result["is_stuck"] is True
    assert result["severity"] == "error"
    # Only the existence check + manual_investigation action.
    keys = [c["key"] for c in result["checks"]]
    assert keys == ["ticket_existence"]
    action_keys = [a["action_key"] for a in result["recommended_actions"]]
    assert "manual_investigation" in action_keys


def test_missing_intelligence_recommends_rerun(tmp_path, db):
    _write_ticket(tmp_path, "T001")
    result = _diag.diagnose_ticket(db, tmp_path, "T001", persist=False)
    action_keys = [a["action_key"] for a in result["recommended_actions"]]
    assert "rerun_intelligence" in action_keys


def test_missing_readiness_recommends_rerun(tmp_path, db):
    _write_ticket(tmp_path, "T001")
    result = _diag.diagnose_ticket(db, tmp_path, "T001", persist=False)
    action_keys = [a["action_key"] for a in result["recommended_actions"]]
    assert "rerun_readiness" in action_keys


def test_blocked_readiness_surfaces_reasons(tmp_path, db):
    _write_ticket(tmp_path, "T001")
    _db.upsert_ticket_readiness(
        db, "T001",
        readiness_status="blocked",
        ready_candidate=0,
        blocking_reasons_json=["Dependency T010 not merged"],
    )
    result = _diag.diagnose_ticket(db, tmp_path, "T001", persist=False)
    readiness_check = next(c for c in result["checks"] if c["key"] == "readiness")
    assert readiness_check["status"] == "failed"
    assert "Dependency T010 not merged" in readiness_check["details"]["blocking_reasons"]
    assert result["is_stuck"] is True


def test_ready_candidate_without_approval_recommends_both(tmp_path, db):
    _write_ticket(tmp_path, "T001")
    _db.upsert_ticket_readiness(
        db, "T001",
        readiness_status="ready_candidate",
        ready_candidate=1,
        blocking_reasons_json=[],
    )
    result = _diag.diagnose_ticket(db, tmp_path, "T001", persist=False)
    action_keys = {a["action_key"] for a in result["recommended_actions"]}
    assert "approve_execution" in action_keys
    assert "reject_execution" in action_keys


def test_blocked_rules_surfaces_failed_rules(tmp_path, db):
    _write_ticket(tmp_path, "T001")
    _db.upsert_ticket_rule_evaluation(
        db,
        "T001",
        project_id="proj-a",
        eligibility_status="blocked",
        passed_rules=[],
        failed_rules=[{"rule_key": "max_difficulty", "reason": "too hard"}],
        warnings=[],
        evaluated_at=_db._now_iso(),
    )
    result = _diag.diagnose_ticket(db, tmp_path, "T001", persist=False)
    rules_check = next(c for c in result["checks"] if c["key"] == "rules")
    assert rules_check["status"] == "failed"
    assert any(r.get("rule_key") == "max_difficulty" for r in rules_check["details"]["failed_rules"])


def test_missing_worktree_recommends_safe_recovery(tmp_path, db):
    _write_ticket(tmp_path, "T001")
    _db.upsert_ticket_runtime(
        db, "T001",
        state="CODING",
        worktree_path=str(tmp_path / "nowhere" / "T001"),
        branch="ticket/T001",
    )
    result = _diag.diagnose_ticket(db, tmp_path, "T001", persist=False)
    action_keys = {a["action_key"] for a in result["recommended_actions"]}
    assert "recreate_worktree" in action_keys
    worktree_check = next(c for c in result["checks"] if c["key"] == "worktree")
    assert worktree_check["status"] == "failed"
    assert worktree_check["details"]["worktree_status"] == "missing"


def test_merged_pr_unfinished_ticket_recommends_sync(tmp_path, db):
    _write_ticket(tmp_path, "T001")
    _db.upsert_ticket_runtime(
        db, "T001",
        state="CODING",  # not in DONE
        pr_number=42,
        pr_state="merged",
        branch="ticket/T001",
    )
    result = _diag.diagnose_ticket(db, tmp_path, "T001", persist=False)
    action_keys = {a["action_key"] for a in result["recommended_actions"]}
    assert "sync_ticket_state" in action_keys


def test_happy_path_has_no_blockers(tmp_path, db):
    _write_ticket(tmp_path, "T001")
    _db.upsert_ticket_intelligence(db, "T001", analysis_status="completed")
    _db.upsert_ticket_readiness(
        db, "T001",
        readiness_status="ready_to_take",
        ready_candidate=1,
        blocking_reasons_json=[],
    )
    _db.insert_ticket_approval(
        db, "T001",
        approval_type="execution",
        approval_status="approved",
        approved_by="alice",
    )
    _db.upsert_ticket_rule_evaluation(
        db,
        "T001",
        project_id="proj-a",
        eligibility_status="eligible",
        passed_rules=[{"rule_key": "x", "reason": "ok"}],
        failed_rules=[],
        warnings=[],
        evaluated_at=_db._now_iso(),
    )
    _db.upsert_ticket_runtime(db, "T001", state="DONE", branch="ticket/T001")
    result = _diag.diagnose_ticket(db, tmp_path, "T001", persist=False)
    assert result["is_stuck"] is False
    assert result["severity"] == "info"


def test_idempotent_repeat_call(tmp_path, db):
    _write_ticket(tmp_path, "T001")
    r1 = _diag.diagnose_ticket(db, tmp_path, "T001", persist=False)
    r2 = _diag.diagnose_ticket(db, tmp_path, "T001", persist=False)
    # generated_at can differ; the rest of the structure is stable.
    r1_copy = {k: v for k, v in r1.items() if k != "generated_at"}
    r2_copy = {k: v for k, v in r2.items() if k != "generated_at"}
    assert r1_copy == r2_copy


def test_persist_writes_to_db(tmp_path, db):
    _write_ticket(tmp_path, "T001")
    _diag.diagnose_ticket(db, tmp_path, "T001", persist=True, project_id="proj-a")
    row = _db.get_ticket_diagnostics(db, "T001")
    assert row is not None
    assert row["project_id"] == "proj-a"
    assert row["diagnostic_status"] == "completed"
    assert isinstance(row["checks_json"], list)


def test_dedupe_actions():
    actions = [
        {"action_key": "rerun_readiness", "label": "x", "risk": "low", "reason": "a"},
        {"action_key": "rerun_readiness", "label": "x", "risk": "low", "reason": "b"},
        {"action_key": "approve_execution", "label": "y", "risk": "low", "reason": "c"},
    ]
    out = _diag._dedupe_actions(actions)
    assert [a["action_key"] for a in out] == ["rerun_readiness", "approve_execution"]
    # Preserves first occurrence's reason.
    assert out[0]["reason"] == "a"


def test_build_diagnostic_assembles_structure():
    checks = [
        {"key": "ticket_existence", "status": "passed", "message": "ok", "details": {}},
        {"key": "readiness", "status": "failed", "message": "blocked", "details": {}},
    ]
    actions = [{"action_key": "rerun_readiness", "label": "x", "risk": "low", "reason": "r"}]
    runtime_row = {"state": "PLAN_APPROVED", "last_transition": "plan", "last_error": None}
    result = _diag.build_diagnostic("T001", checks, actions, runtime_row)
    assert result["ticket_id"] == "T001"
    assert result["is_stuck"] is True
    assert result["severity"] == "warning"
    assert result["current_state"] == "PLAN_APPROVED"
    assert result["last_known_step"] == "plan"
    assert result["recommended_actions"] == actions
    assert "generated_at" in result
