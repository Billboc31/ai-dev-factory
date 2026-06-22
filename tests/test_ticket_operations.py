"""Tests for the ticket_operations service (T204)."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

_TOOLS = Path(__file__).parent.parent / "tools" / "agent_runner"
sys.path.insert(0, str(_TOOLS))


def _load_sqlite_runtime_db():
    spec = importlib.util.spec_from_file_location(
        "_runtime_db_sqlite_test_operations",
        _TOOLS / "runtime_db.py",
    )
    mod = importlib.util.module_from_spec(spec)
    old = os.environ.get("RUNTIME_DB_BACKEND")
    os.environ["RUNTIME_DB_BACKEND"] = "sqlite"
    try:
        spec.loader.exec_module(mod)
    finally:
        if old is None:
            os.environ.pop("RUNTIME_DB_BACKEND", None)
        else:
            os.environ["RUNTIME_DB_BACKEND"] = old
    return mod


_db = _load_sqlite_runtime_db()


def _load_operations():
    module_name = "_ticket_operations_test_module"
    spec = importlib.util.spec_from_file_location(
        module_name,
        _TOOLS / "ticket_operations.py",
    )
    mod = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = mod
    spec.loader.exec_module(mod)
    mod.runtime_db = _db
    mod.ticket_approval_service.runtime_db = _db
    mod.ticket_diagnostics.runtime_db = _db
    if hasattr(mod.ticket_diagnostics, "ticket_approval_service"):
        mod.ticket_diagnostics.ticket_approval_service.runtime_db = _db
    return mod


_ops = _load_operations()


@pytest.fixture()
def db(tmp_path: Path) -> Path:
    db_path = tmp_path / ".runtime" / "test.sqlite"
    _db.init_runtime_db(db_path)
    return db_path


def _write_ticket(project_root: Path, ticket_id: str, state: str = "PLAN_APPROVED") -> Path:
    run_dir = project_root / "runs" / ticket_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "state.json").write_text(
        json.dumps({"ticket_id": ticket_id, "state": state, "branch": f"ticket/{ticket_id}"}),
        encoding="utf-8",
    )
    (run_dir / "ticket.md").write_text(f"# {ticket_id}\n\nSome ticket content.\n", encoding="utf-8")
    return run_dir


# ── Registry shape ───────────────────────────────────────────────────────────

def test_registry_has_exactly_twelve_operations():
    expected = {
        "rerun_intelligence",
        "rerun_readiness",
        "rerun_rules",
        "rerun_diagnostics",
        "approve_execution",
        "reject_execution",
        "mark_blocked",
        "reset_to_planning",
        "reset_to_coding",
        "clear_stuck_state",
        "delete_worktree",
        "archive_ticket",
    }
    assert set(_ops.OPERATIONS.keys()) == expected
    assert len(_ops.OPERATIONS) == 12


def test_registry_safety_levels_and_groups():
    spec = _ops.OPERATIONS
    assert spec["rerun_diagnostics"].safety_level == "low"
    assert spec["rerun_diagnostics"].group == "advisory"
    assert spec["approve_execution"].safety_level == "medium"
    assert spec["approve_execution"].group == "approval"
    assert spec["mark_blocked"].safety_level == "medium"
    assert spec["mark_blocked"].requires_reason is True
    assert spec["reset_to_planning"].safety_level == "high"
    assert spec["reset_to_planning"].requires_typed_ticket_id is True
    assert spec["delete_worktree"].safety_level == "destructive"
    assert spec["delete_worktree"].requires_typed_ticket_id is True
    assert spec["delete_worktree"].requires_double_confirmation is True


def test_forbidden_runner_states():
    assert _ops.FORBIDDEN_RUNNER_STATES == frozenset({"PLANNING", "CODING", "CANCELLED"})
    for forbidden in _ops.FORBIDDEN_RUNNER_STATES:
        assert forbidden not in _ops.VALID_RUNNER_STATES


# ── list_operations ──────────────────────────────────────────────────────────

def test_list_operations_returns_descriptors(tmp_path, db):
    _write_ticket(tmp_path, "T001")
    items = _ops.list_operations(db, tmp_path, "T001", project_id="pid")
    keys = {i["operation_key"] for i in items}
    assert keys == set(_ops.OPERATIONS.keys())
    by_key = {i["operation_key"]: i for i in items}
    assert by_key["delete_worktree"]["enabled"] is False
    assert "Worktrees root" in (by_key["delete_worktree"]["disabled_reason"] or "")
    assert by_key["clear_stuck_state"]["enabled"] is False
    assert by_key["rerun_diagnostics"]["enabled"] is True


# ── Confirmation validation ──────────────────────────────────────────────────

def test_reset_to_planning_requires_typed_ticket_id(tmp_path, db):
    _write_ticket(tmp_path, "T001")
    with pytest.raises(_ops.OperationError) as exc:
        _ops.execute_operation(
            db, tmp_path, "T001", "reset_to_planning",
            payload={"reason": "stale plan", "typed_ticket_id": "wrong"},
            requested_by="alice",
        )
    assert "typed_ticket_id" in exc.value.message


def test_mark_blocked_requires_reason(tmp_path, db):
    _write_ticket(tmp_path, "T001")
    with pytest.raises(_ops.OperationError) as exc:
        _ops.execute_operation(
            db, tmp_path, "T001", "mark_blocked",
            payload={"reason": "   "},
            requested_by="alice",
        )
    assert "reason" in exc.value.message


def test_delete_worktree_requires_confirm(tmp_path, db):
    _write_ticket(tmp_path, "T001")
    with pytest.raises(_ops.OperationError):
        _ops.execute_operation(
            db, tmp_path, "T001", "delete_worktree",
            payload={"typed_ticket_id": "T001", "confirm": False},
            requested_by="alice",
        )


# ── rerun_diagnostics ────────────────────────────────────────────────────────

def test_rerun_diagnostics_invokes_service(tmp_path, db, monkeypatch):
    _write_ticket(tmp_path, "T001")
    calls = []

    def fake_diagnose(*args, **kwargs):
        calls.append((args, kwargs))
        return {"is_stuck": False, "severity": "info"}

    monkeypatch.setattr(_ops.ticket_diagnostics, "diagnose_ticket", fake_diagnose)
    result = _ops.execute_operation(
        db, tmp_path, "T001", "rerun_diagnostics",
        payload={}, requested_by="alice",
    )
    assert result["status"] == "completed"
    assert len(calls) == 1


# ── Approval delegation ──────────────────────────────────────────────────────

def test_approve_execution_delegates(tmp_path, db, monkeypatch):
    _write_ticket(tmp_path, "T001")
    calls = []

    def fake_approve(db_path, ticket_id, approved_by, comment=None):
        calls.append((ticket_id, approved_by, comment))
        return {"id": 1}

    monkeypatch.setattr(_ops.ticket_approval_service, "approve_execution", fake_approve)
    result = _ops.execute_operation(
        db, tmp_path, "T001", "approve_execution",
        payload={"reason": "looks good"}, requested_by="alice",
    )
    assert result["status"] == "completed"
    assert calls[0] == ("T001", "alice", "looks good")


def test_reject_execution_maps_value_error_to_409(tmp_path, db, monkeypatch):
    _write_ticket(tmp_path, "T001")

    def fake_reject(*args, **kwargs):
        raise ValueError("contradictory_transition")

    monkeypatch.setattr(_ops.ticket_approval_service, "reject_execution", fake_reject)
    with pytest.raises(_ops.OperationError) as exc:
        _ops.execute_operation(
            db, tmp_path, "T001", "reject_execution",
            payload={}, requested_by="alice",
        )
    assert exc.value.status_code == 409


# ── reset_to_planning ────────────────────────────────────────────────────────

def test_reset_to_planning_archives_and_sets_state(tmp_path, db):
    run_dir = _write_ticket(tmp_path, "T001", state="PLAN_APPROVED")
    (run_dir / "plan.md").write_text("# plan", encoding="utf-8")
    (run_dir / "reviews").mkdir()
    (run_dir / "reviews" / "review.md").write_text("review", encoding="utf-8")

    result = _ops.execute_operation(
        db, tmp_path, "T001", "reset_to_planning",
        payload={"reason": "stale plan after merge", "typed_ticket_id": "T001"},
        requested_by="alice",
    )
    assert result["status"] == "completed"

    state_data = json.loads((run_dir / "state.json").read_text(encoding="utf-8"))
    assert state_data["state"] == "PLAN_FIX_REQUIRED"

    archive_root = Path(result["details"]["archive_dir"])
    assert archive_root.exists()
    assert (archive_root / "plan.md").exists()
    assert (archive_root / "reviews").exists()
    assert not (run_dir / "plan.md").exists()
    meta = json.loads((archive_root / "reset.json").read_text(encoding="utf-8"))
    assert meta["new_state"] == "PLAN_FIX_REQUIRED"
    assert meta["previous_state"] == "PLAN_APPROVED"
    assert meta["operation"] == "reset_to_planning"
    assert meta["requested_by"] == "alice"


def test_reset_to_planning_never_writes_planning_state(tmp_path, db):
    run_dir = _write_ticket(tmp_path, "T001", state="PLAN_APPROVED")
    (run_dir / "plan.md").write_text("# plan", encoding="utf-8")
    _ops.execute_operation(
        db, tmp_path, "T001", "reset_to_planning",
        payload={"reason": "needed", "typed_ticket_id": "T001"},
        requested_by="alice",
    )
    state_data = json.loads((run_dir / "state.json").read_text(encoding="utf-8"))
    assert state_data["state"] != "PLANNING"
    assert state_data["state"] in _ops.VALID_RUNNER_STATES


# ── reset_to_coding ──────────────────────────────────────────────────────────

def test_reset_to_coding_preserves_plan(tmp_path, db):
    run_dir = _write_ticket(tmp_path, "T001", state="IMPLEMENTATION_APPROVED")
    (run_dir / "plan.md").write_text("# plan", encoding="utf-8")
    (run_dir / "reviews").mkdir()
    (run_dir / "tests").mkdir()
    result = _ops.execute_operation(
        db, tmp_path, "T001", "reset_to_coding",
        payload={"reason": "regen impl", "typed_ticket_id": "T001"},
        requested_by="alice",
    )
    assert result["status"] == "completed"

    # plan.md preserved.
    assert (run_dir / "plan.md").exists()

    state_data = json.loads((run_dir / "state.json").read_text(encoding="utf-8"))
    assert state_data["state"] == "IMPLEMENTATION_FIX_REQUIRED"
    assert state_data["state"] != "CODING"

    archive_root = Path(result["details"]["archive_dir"])
    assert (archive_root / "reviews").exists()
    assert (archive_root / "tests").exists()
    assert not (archive_root / "plan.md").exists()
    meta = json.loads((archive_root / "reset.json").read_text(encoding="utf-8"))
    assert meta["new_state"] == "IMPLEMENTATION_FIX_REQUIRED"


# ── archive_ticket ───────────────────────────────────────────────────────────

def test_archive_ticket_only_sets_archive_metadata(tmp_path, db):
    run_dir = _write_ticket(tmp_path, "T001", state="PLAN_APPROVED")
    (run_dir / "plan.md").write_text("# plan", encoding="utf-8")
    (run_dir / "reviews").mkdir()
    (run_dir / "reviews" / "review.md").write_text("review", encoding="utf-8")

    result = _ops.execute_operation(
        db, tmp_path, "T001", "archive_ticket",
        payload={"reason": "no longer needed"},
        requested_by="alice",
    )
    assert result["status"] == "completed"

    # Runner state unchanged.
    state_data = json.loads((run_dir / "state.json").read_text(encoding="utf-8"))
    assert state_data["state"] == "PLAN_APPROVED"
    assert state_data["archived"] is True
    assert state_data["archived_reason"] == "no longer needed"
    assert state_data["archived_by"] == "alice"
    assert "archived_at" in state_data

    # CANCELLED never written.
    assert state_data["state"] != "CANCELLED"

    # Artifacts preserved.
    assert (run_dir / "plan.md").exists()
    assert (run_dir / "reviews" / "review.md").exists()


# ── clear_stuck_state ────────────────────────────────────────────────────────

def test_clear_stuck_state_refuses_fresh_heartbeat(tmp_path, db):
    _write_ticket(tmp_path, "T001")
    _db.upsert_worker(db, "T001", pid=1234, branch="b", worktree_path=str(tmp_path / "wt"))
    # heartbeat is fresh (just upserted, started_at = now)
    with pytest.raises(_ops.OperationError) as exc:
        _ops.execute_operation(
            db, tmp_path, "T001", "clear_stuck_state",
            payload={}, requested_by="alice",
        )
    assert exc.value.status_code == 409


def test_clear_stuck_state_clears_stale_row(tmp_path, db):
    _write_ticket(tmp_path, "T001")
    _db.upsert_worker(db, "T001", pid=1234, branch="b", worktree_path=str(tmp_path / "wt"))
    # Force heartbeat_at to an old value.
    import sqlite3
    with sqlite3.connect(str(db)) as conn:
        conn.execute(
            "UPDATE workers SET heartbeat_at = ?, started_at = ? WHERE ticket_id = ?",
            ("2020-01-01T00:00:00Z", "2020-01-01T00:00:00Z", "T001"),
        )
    result = _ops.execute_operation(
        db, tmp_path, "T001", "clear_stuck_state",
        payload={}, requested_by="alice",
    )
    assert result["status"] == "completed"
    assert result["details"]["cleared"] is True
    workers = _db.list_workers(db)
    assert not any(w["ticket_id"] == "T001" for w in workers)


# ── delete_worktree ──────────────────────────────────────────────────────────

def _make_git_worktree(tmp_path: Path, ticket_id: str) -> Path:
    """Create a small standalone git repo so 'git status' works."""
    wt = tmp_path / "wt-root" / ticket_id
    wt.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(wt)], check=True)
    subprocess.run(["git", "-C", str(wt), "config", "user.email", "t@example.com"], check=True)
    subprocess.run(["git", "-C", str(wt), "config", "user.name", "t"], check=True)
    (wt / "f.txt").write_text("hello", encoding="utf-8")
    subprocess.run(["git", "-C", str(wt), "add", "."], check=True)
    subprocess.run(["git", "-C", str(wt), "commit", "-q", "-m", "init"], check=True)
    return wt


def test_delete_worktree_refuses_outside_root(tmp_path, db):
    _write_ticket(tmp_path, "T001")
    worktrees_root = tmp_path / "wt-root"
    worktrees_root.mkdir()
    with pytest.raises(_ops.OperationError):
        _ops.execute_operation(
            db, tmp_path, "../escape", "delete_worktree",
            payload={"typed_ticket_id": "../escape", "confirm": True},
            requested_by="alice", worktrees_dir=worktrees_root,
        )


def test_delete_worktree_refuses_dirty_without_force(tmp_path, db):
    wt = _make_git_worktree(tmp_path, "T001")
    (wt / "dirty.txt").write_text("dirty", encoding="utf-8")
    _write_ticket(tmp_path, "T001")
    with pytest.raises(_ops.OperationError) as exc:
        _ops.execute_operation(
            db, tmp_path, "T001", "delete_worktree",
            payload={"typed_ticket_id": "T001", "confirm": True, "force": False},
            requested_by="alice", worktrees_dir=tmp_path / "wt-root",
        )
    assert "uncommitted" in exc.value.message


def test_delete_worktree_succeeds_with_force(tmp_path, db):
    wt = _make_git_worktree(tmp_path, "T001")
    (wt / "dirty.txt").write_text("dirty", encoding="utf-8")
    _write_ticket(tmp_path, "T001")
    result = _ops.execute_operation(
        db, tmp_path, "T001", "delete_worktree",
        payload={"typed_ticket_id": "T001", "confirm": True, "force": True},
        requested_by="alice", worktrees_dir=tmp_path / "wt-root",
    )
    assert result["status"] == "completed"
    assert not wt.exists()


def test_delete_worktree_refuses_when_heartbeat_fresh(tmp_path, db):
    _make_git_worktree(tmp_path, "T001")
    _write_ticket(tmp_path, "T001")
    _db.upsert_worker(db, "T001", pid=1234, branch="b", worktree_path=str(tmp_path / "wt-root" / "T001"))
    with pytest.raises(_ops.OperationError) as exc:
        _ops.execute_operation(
            db, tmp_path, "T001", "delete_worktree",
            payload={"typed_ticket_id": "T001", "confirm": True, "force": True},
            requested_by="alice", worktrees_dir=tmp_path / "wt-root",
        )
    assert exc.value.status_code == 409


# ── Audit log ────────────────────────────────────────────────────────────────

def test_audit_log_records_success(tmp_path, db, monkeypatch):
    _write_ticket(tmp_path, "T001")
    monkeypatch.setattr(_ops.ticket_diagnostics, "diagnose_ticket", lambda *a, **k: {"is_stuck": False, "severity": "info"})
    _ops.execute_operation(
        db, tmp_path, "T001", "rerun_diagnostics",
        payload={}, requested_by="alice",
    )
    rows = _db.list_ticket_operation_audit(db, "T001")
    assert any(r["operation_key"] == "rerun_diagnostics" and r["status"] == "completed" for r in rows)
    events = _db.list_runtime_events(db, "T001")
    assert any(e["event_type"] == "operation:rerun_diagnostics" for e in events)


def test_audit_log_records_rejection(tmp_path, db):
    _write_ticket(tmp_path, "T001")
    with pytest.raises(_ops.OperationError):
        _ops.execute_operation(
            db, tmp_path, "T001", "mark_blocked",
            payload={"reason": ""}, requested_by="alice",
        )
    rows = _db.list_ticket_operation_audit(db, "T001")
    assert any(r["operation_key"] == "mark_blocked" and r["status"] == "rejected" for r in rows)
    events = _db.list_runtime_events(db, "T001")
    assert any(e["event_type"] == "operation:mark_blocked" for e in events)


def test_unknown_operation_returns_404(tmp_path, db):
    _write_ticket(tmp_path, "T001")
    with pytest.raises(_ops.OperationError) as exc:
        _ops.execute_operation(
            db, tmp_path, "T001", "made_up_op",
            payload={}, requested_by="alice",
        )
    assert exc.value.status_code == 404


# ── Runner state guardrails (registry-level) ─────────────────────────────────

def test_no_handler_returns_forbidden_state_names_in_results(tmp_path, db, monkeypatch):
    """A defensive sweep: run every operation that can change runner state and
    verify the resulting state.json never holds a forbidden value."""
    monkeypatch.setattr(_ops.ticket_diagnostics, "diagnose_ticket", lambda *a, **k: {"is_stuck": False, "severity": "info"})
    state_setters = [
        ("reset_to_planning", {"reason": "x", "typed_ticket_id": "T001"}),
        ("reset_to_coding",   {"reason": "x", "typed_ticket_id": "T001"}),
        ("archive_ticket",    {"reason": "x"}),
    ]
    for op_key, payload in state_setters:
        run_dir = _write_ticket(tmp_path, "T001", state="PLAN_APPROVED")
        (run_dir / "plan.md").write_text("p", encoding="utf-8")
        _ops.execute_operation(
            db, tmp_path, "T001", op_key,
            payload=payload, requested_by="alice",
        )
        state_data = json.loads((run_dir / "state.json").read_text(encoding="utf-8"))
        current = state_data.get("state")
        assert current not in _ops.FORBIDDEN_RUNNER_STATES
        assert current in _ops.VALID_RUNNER_STATES
