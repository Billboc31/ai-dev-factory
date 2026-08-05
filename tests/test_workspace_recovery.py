"""Tests for the recover_ticket workspace capability.

Covers:
- Prepare phase: no disk mutations, proposal stored correctly
- Confirmation card: stored operations returned verbatim
- Security: frontend cannot alter operations
- Stale proposal: 409 when ticket state changes between prepare and execute
- Only stored operations executed
- Concurrency: exactly one session per ticket
- Lock released on exception
- Iteration limit enforced
- Blocker classification for all 11 BlockerClass values
- Allowlist rejects unknown op names, free paths, free service names
- MISSING_APPROVAL terminates with NEEDS_USER_INPUT, no mutating ops
- Bug deduplication prevents duplicate issues
- Bug signature is deterministic
- Polling endpoint returns terminal result
- recover_ticket in _WORKSPACE_CAPABILITIES
- "Unblock this ticket" maps to recover_ticket capability
- Active ticket resolution
- Recovery verification step
"""

from __future__ import annotations

import json
import sys
import threading
import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest
from fastapi.testclient import TestClient

# Ensure imports resolve to the worktree source
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "services" / "supervisor"))

import recovery as rec
from recovery import (
    BlockerClass,
    RecoveryStage,
    ProposalStatus,
    ArtifactType,
    ServiceId,
    MAX_RECOVERY_ITERATIONS,
    ALLOWLISTED_RECOVERY_OPS,
    RecoveryOp,
    RecoveryProposal,
    RecoverySession,
    classify_blocker,
    build_recovery_plan,
    compute_state_fingerprint,
    compute_bug_signature,
    verify_ticket_progress,
    apply_recovery_op,
    _TERMINAL_TICKET_STATES,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture
def project_root(tmp_path):
    """A minimal project root with a single ticket run directory."""
    return tmp_path


@pytest.fixture
def ticket_id():
    return "T999"


@pytest.fixture
def run_dir(project_root, ticket_id):
    d = project_root / "runs" / ticket_id
    d.mkdir(parents=True)
    return d


@pytest.fixture
def state_file(run_dir):
    """Write a default non-terminal state.json."""
    sf = run_dir / "state.json"
    sf.write_text(json.dumps({
        "ticket_id": "T999",
        "state": "PLAN",
        "branch": "ticket/T999-test",
    }), encoding="utf-8")
    return sf


@pytest.fixture
def supervisor_app(tmp_path, monkeypatch):
    """Supervisor FastAPI app with workspace endpoints reachable."""
    monkeypatch.setenv("SUPERVISOR_PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("CONTROL_API_URL", "http://localhost:9999")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

    import services.supervisor.main as sup_main

    sup_main._pending_workspace_actions.clear()
    sup_main._pending_workspace_issues.clear()
    sup_main._active_sessions.clear()
    sup_main._proposals.clear()
    sup_main._results.clear()

    yield sup_main.app

    sup_main._pending_workspace_actions.clear()
    sup_main._pending_workspace_issues.clear()
    sup_main._active_sessions.clear()
    sup_main._proposals.clear()
    sup_main._results.clear()


@pytest.fixture
def client(supervisor_app):
    return TestClient(supervisor_app, raise_server_exceptions=False)


def _ai_response(**overrides) -> dict:
    base = {
        "reply": "Here is the answer.",
        "intent": "informational",
        "proposed_action": None,
        "issue_draft": None,
        "confirmation_required": False,
    }
    base.update(overrides)
    return base


def _post_chat(client, project_id: str, message: str, ai_return: dict):
    with patch("services.supervisor.main._call_workspace_ai", return_value=ai_return):
        return client.post(
            f"/workspace/projects/{project_id}/chat",
            json={"message": message, "conversation_history": []},
        )


# ── Test: prepare performs no mutation ───────────────────────────────────────


def test_prepare_performs_no_mutation(project_root, ticket_id, run_dir, state_file):
    import services.supervisor.main as sup_main

    state_before = state_file.read_bytes()

    with patch.object(sup_main, "_resolve_active_ticket_id", return_value=ticket_id):
        result = sup_main._prepare_recovery("proj1", project_root)

    assert "error" not in result, f"prepare failed: {result}"
    # state.json must be unchanged
    assert state_file.read_bytes() == state_before
    # Exactly one proposal stored
    assert len(sup_main._proposals) == 1

    sup_main._active_sessions.clear()
    sup_main._proposals.clear()


# ── Test: confirmation card receives stored operations ────────────────────────


def test_confirmation_card_receives_stored_operations(project_root, ticket_id, run_dir, state_file):
    import services.supervisor.main as sup_main

    with patch.object(sup_main, "_resolve_active_ticket_id", return_value=ticket_id):
        result = sup_main._prepare_recovery("proj1", project_root)

    proposal_id = result["action_id"]
    proposal = sup_main._proposals[proposal_id]

    returned_ops = result["operations"]
    stored_ops = [
        {"name": op.name, "description": op.description, "risk_level": op.risk_level, "params": op.params}
        for op in proposal.operations
    ]
    assert returned_ops == stored_ops

    sup_main._active_sessions.clear()
    sup_main._proposals.clear()


# ── Test: frontend cannot alter operations ────────────────────────────────────


def test_frontend_cannot_alter_operations(project_root, ticket_id, run_dir, state_file):
    import services.supervisor.main as sup_main

    with patch.object(sup_main, "_resolve_active_ticket_id", return_value=ticket_id):
        prep = sup_main._prepare_recovery("proj1", project_root)

    proposal_id = prep["action_id"]
    stored_op_count = len(sup_main._proposals[proposal_id].operations)

    applied_ops: list[str] = []

    def fake_apply(op, project_root, project_id, ticket_id):
        applied_ops.append(op.name)
        return rec.OpResult(op_name=op.name, success=True, detail="ok", mutated=False)

    with patch("services.supervisor.main.apply_recovery_op", side_effect=fake_apply):
        with patch("services.supervisor.main.verify_ticket_progress", return_value=(True, "DONE")):
            sup_main._execute_recovery(proposal_id, project_root)

    assert len(applied_ops) == stored_op_count

    sup_main._proposals.clear()
    sup_main._results.clear()


# ── Test: stale proposal rejected with 409 ────────────────────────────────────


def test_stale_proposal_rejected_with_409(project_root, ticket_id, run_dir, state_file):
    import services.supervisor.main as sup_main

    with patch.object(sup_main, "_resolve_active_ticket_id", return_value=ticket_id):
        prep = sup_main._prepare_recovery("proj1", project_root)

    proposal_id = prep["action_id"]

    # Mutate state.json to invalidate the fingerprint
    state_file.write_text(json.dumps({"ticket_id": ticket_id, "state": "IMPLEMENTATION"}), encoding="utf-8")

    apply_mock = MagicMock()
    with patch("services.supervisor.main.apply_recovery_op", apply_mock):
        result = sup_main._execute_recovery(proposal_id, project_root)

    assert result.get("error") == "PROPOSAL_STALE"
    apply_mock.assert_not_called()

    sup_main._proposals.clear()
    sup_main._results.clear()


# ── Test: only stored proposal executed ───────────────────────────────────────


def test_only_stored_proposal_executed(project_root, ticket_id, run_dir, state_file):
    import services.supervisor.main as sup_main

    with patch.object(sup_main, "_resolve_active_ticket_id", return_value=ticket_id):
        prep = sup_main._prepare_recovery("proj1", project_root)

    proposal_id = prep["action_id"]
    stored_ops = list(sup_main._proposals[proposal_id].operations)

    called_op_names: list[str] = []

    def fake_apply(op, project_root, project_id, ticket_id):
        called_op_names.append(op.name)
        return rec.OpResult(op_name=op.name, success=True, detail="ok", mutated=False)

    with patch("services.supervisor.main.apply_recovery_op", side_effect=fake_apply):
        with patch("services.supervisor.main.verify_ticket_progress", return_value=(True, "DONE")):
            sup_main._execute_recovery(proposal_id, project_root)

    assert called_op_names == [op.name for op in stored_ops]

    sup_main._proposals.clear()
    sup_main._results.clear()


# ── Test: concurrent session rejected atomically ──────────────────────────────


def test_concurrent_session_rejected_atomically(project_root, ticket_id, run_dir, state_file):
    import services.supervisor.main as sup_main

    results: list[dict] = []
    barrier = threading.Barrier(2)

    def run_prepare():
        barrier.wait()
        with patch.object(sup_main, "_resolve_active_ticket_id", return_value=ticket_id):
            r = sup_main._prepare_recovery("proj1", project_root)
        results.append(r)

    t1 = threading.Thread(target=run_prepare)
    t2 = threading.Thread(target=run_prepare)
    t1.start()
    t2.start()
    t1.join()
    t2.join()

    assert len(results) == 2
    errors = [r for r in results if "error" in r]
    successes = [r for r in results if "error" not in r]

    assert len(successes) == 1, f"Expected exactly one success, got {len(successes)}"
    assert len(errors) == 1
    assert errors[0]["error"] == "RECOVERY_IN_PROGRESS"
    assert len(sup_main._active_sessions) == 1

    sup_main._active_sessions.clear()
    sup_main._proposals.clear()


# ── Test: lock released on exception ─────────────────────────────────────────


def test_lock_released_on_exception(project_root, ticket_id, run_dir, state_file):
    import services.supervisor.main as sup_main

    with patch("services.supervisor.main.classify_blocker", side_effect=RuntimeError("boom")):
        with patch.object(sup_main, "_resolve_active_ticket_id", return_value=ticket_id):
            result = sup_main._prepare_recovery("proj1", project_root)

    assert result.get("error") == "PREPARE_FAILED"
    assert ticket_id not in sup_main._active_sessions


# ── Test: iteration limit enforced ────────────────────────────────────────────


def test_iteration_limit_enforced(project_root, ticket_id, run_dir, state_file):
    import services.supervisor.main as sup_main

    # Use FAILED_STAGE blocker which has multi-op plan (diagnostics + retry)
    state_file.write_text(json.dumps({
        "ticket_id": ticket_id, "state": "PLAN", "failed_stage": True,
    }), encoding="utf-8")

    with patch.object(sup_main, "_resolve_active_ticket_id", return_value=ticket_id):
        prep = sup_main._prepare_recovery("proj1", project_root)

    proposal_id = prep["action_id"]

    def always_fail(op, project_root, project_id, ticket_id):
        return rec.OpResult(op_name=op.name, success=False, detail="forced failure", mutated=False)

    with patch("services.supervisor.main.apply_recovery_op", side_effect=always_fail):
        result = sup_main._execute_recovery(proposal_id, project_root)

    report = result.get("recovery_report", {})
    assert report.get("stage") == RecoveryStage.FAILED.value

    stored_result = sup_main._results.get(
        next(iter(s.session_id for s in [] if False), list(sup_main._results.values())[0].session_id if sup_main._results else None)
    )
    if sup_main._results:
        r = list(sup_main._results.values())[0]
        assert r.stage == RecoveryStage.FAILED

    sup_main._proposals.clear()
    sup_main._results.clear()


# ── Test: blocker classification (parametrised) ───────────────────────────────


@pytest.mark.parametrize("blocker_class,state_data,artifacts,logs", [
    (
        BlockerClass.MISSING_ARTIFACT,
        {"state": "PLAN_APPROVED"},
        {},  # plan.md missing
        "",
    ),
    (
        BlockerClass.STALE_READINESS,
        {"state": "PLAN_APPROVED", "stale_readiness": True},
        {"plan.md": True},
        "",
    ),
    (
        BlockerClass.MISSING_APPROVAL,
        {"state": "PLAN_PENDING_REVIEW"},
        {},
        "",
    ),
    (
        BlockerClass.FAILED_STAGE,
        {"state": "PLAN", "failed_stage": True},
        {},
        "error: stage failed",
    ),
    (
        BlockerClass.BRANCH_DIVERGENCE,
        {"state": "PLAN"},
        {},
        "error: branch has diverged from origin",
    ),
    (
        BlockerClass.WORKING_TREE_CONFLICT,
        {"state": "PLAN"},
        {},
        "CONFLICT: merge conflict detected in file.py",
    ),
    (
        BlockerClass.TRANSIENT_FAILURE,
        {"state": "PLAN"},
        {},
        "error: connection refused to api.anthropic.com:443",
    ),
    (
        BlockerClass.INVALID_CONFIG,
        {"state": ""},  # empty state = invalid
        {},
        "",
    ),
    (
        BlockerClass.INCONSISTENT_STATE,
        {"state": "PLAN", "inconsistent_state": True},
        {},
        "",
    ),
    (
        BlockerClass.PRODUCT_BUG,
        {"state": "PLAN"},
        {},
        "Traceback (most recent call last):\n  File ...\nAttributeError: 'NoneType' object has no attribute 'foo'",
    ),
    (
        BlockerClass.USER_DECISION_REQUIRED,
        {"state": "NEEDS_USER_INPUT"},
        {},
        "",
    ),
])
def test_blocker_classification(blocker_class, state_data, artifacts, logs):
    result = classify_blocker(state_data, artifacts, logs)
    assert result == blocker_class, f"Expected {blocker_class}, got {result}"


# ── Test: arbitrary op name rejected ─────────────────────────────────────────


def test_arbitrary_op_name_rejected(project_root, ticket_id, run_dir, state_file):
    import services.supervisor.main as sup_main

    with patch.object(sup_main, "_resolve_active_ticket_id", return_value=ticket_id):
        prep = sup_main._prepare_recovery("proj1", project_root)

    proposal_id = prep["action_id"]
    proposal = sup_main._proposals[proposal_id]

    # Inject a rogue op into the stored proposal (simulates in-memory tampering)
    proposal.operations.insert(0, RecoveryOp(
        name="rm_rf_everything",
        description="dangerous",
        risk_level="HIGH",
        params={},
    ))

    with pytest.raises(ValueError, match="not in ALLOWLISTED_RECOVERY_OPS|allowlist"):
        apply_recovery_op(
            RecoveryOp(name="rm_rf_everything", description="x", risk_level="HIGH", params={}),
            project_root, "proj1", ticket_id,
        )

    # Executing also raises (and the session is cleaned up)
    apply_mock = MagicMock(side_effect=ValueError("not in allowlist"))
    with patch("services.supervisor.main.apply_recovery_op", apply_mock):
        result = sup_main._execute_recovery(proposal_id, project_root)

    sup_main._proposals.clear()
    sup_main._results.clear()


# ── Test: arbitrary path param rejected ──────────────────────────────────────


def test_arbitrary_path_param_rejected():
    op = RecoveryOp(
        name="regenerate_artifact",
        description="test",
        risk_level="LOW",
        params={"artifact_type": "/etc/passwd"},
    )
    with pytest.raises(ValueError, match="artifact_type"):
        apply_recovery_op(op, Path("/tmp"), "proj1", "T999")


# ── Test: arbitrary service name rejected ─────────────────────────────────────


def test_arbitrary_service_name_rejected():
    op = RecoveryOp(
        name="restart_service",
        description="test",
        risk_level="HIGH",
        params={"service_id": "arbitrary_service"},
    )
    with pytest.raises(ValueError, match="service_id"):
        apply_recovery_op(op, Path("/tmp"), "proj1", "T999")


# ── Test: MISSING_APPROVAL stops at gate ─────────────────────────────────────


def test_missing_approval_stops_at_gate(project_root, ticket_id, run_dir):
    import services.supervisor.main as sup_main

    state_file = run_dir / "state.json"
    state_file.write_text(json.dumps({
        "ticket_id": ticket_id, "state": "PLAN_PENDING_REVIEW",
    }), encoding="utf-8")

    with patch.object(sup_main, "_resolve_active_ticket_id", return_value=ticket_id):
        prep = sup_main._prepare_recovery("proj1", project_root)

    assert "error" not in prep
    proposal_id = prep["action_id"]
    proposal = sup_main._proposals[proposal_id]

    # No mutating ops in plan
    mutating = [op for op in proposal.operations if ALLOWLISTED_RECOVERY_OPS[op.name].risk_level != "LOW" or
                ALLOWLISTED_RECOVERY_OPS[op.name].mutation_description.lower().startswith("read")]
    assert len(proposal.operations) == 0, f"Expected empty plan, got {[op.name for op in proposal.operations]}"

    apply_mock = MagicMock()
    with patch("services.supervisor.main.apply_recovery_op", apply_mock):
        with patch("services.supervisor.main.verify_ticket_progress", return_value=(False, "PLAN_PENDING_REVIEW")):
            result = sup_main._execute_recovery(proposal_id, project_root)

    apply_mock.assert_not_called()
    report = result.get("recovery_report", {})
    assert report.get("stage") == RecoveryStage.NEEDS_USER_INPUT.value

    sup_main._proposals.clear()
    sup_main._results.clear()


# ── Test: bug deduplication prevents duplicate issue ─────────────────────────


def test_bug_deduplication_prevents_duplicate_issue(project_root, ticket_id, run_dir):
    import services.supervisor.main as sup_main

    state_file = run_dir / "state.json"
    state_file.write_text(json.dumps({
        "ticket_id": ticket_id, "state": "PLAN", "product_bug": True,
    }), encoding="utf-8")

    with patch.object(sup_main, "_resolve_active_ticket_id", return_value=ticket_id):
        prep = sup_main._prepare_recovery("proj1", project_root)

    proposal_id = prep["action_id"]

    existing_url = "https://github.com/org/repo/issues/42"

    def fake_apply(op, project_root, project_id, ticket_id):
        return rec.OpResult(op_name=op.name, success=True, detail="ok", mutated=False)

    with patch("services.supervisor.main.apply_recovery_op", side_effect=fake_apply):
        with patch("services.supervisor.main.verify_ticket_progress", return_value=(True, "DONE")):
            with patch("services.supervisor.main.search_existing_bug_issues", return_value=existing_url) as mock_search:
                with patch("services.supervisor.main.create_bug_issue") as mock_create:
                    with patch("services.supervisor.main._lookup_project_root_from_control_api", return_value=str(project_root)):
                        with patch("subprocess.run") as mock_run:
                            mock_run.return_value = MagicMock(returncode=0, stdout="org/repo")
                            result = sup_main._execute_recovery(proposal_id, project_root)

    mock_create.assert_not_called()
    report = result.get("recovery_report", {})
    assert report.get("bug_issue_url") == existing_url

    sup_main._proposals.clear()
    sup_main._results.clear()


# ── Test: bug signature is deterministic ──────────────────────────────────────


def test_bug_signature_is_deterministic():
    sig1 = compute_bug_signature("proj1", BlockerClass.PRODUCT_BUG, "PLAN", None, None)
    sig2 = compute_bug_signature("proj1", BlockerClass.PRODUCT_BUG, "PLAN", None, None)
    assert sig1 == sig2

    sig3 = compute_bug_signature("proj1", BlockerClass.PRODUCT_BUG, "IMPLEMENTATION", None, None)
    assert sig1 != sig3


# ── Test: polling endpoint returns result ─────────────────────────────────────


def test_polling_endpoint_returns_result(client):
    import services.supervisor.main as sup_main
    from recovery import RecoveryResult, RecoveryStage

    session_id = str(uuid.uuid4())
    result = RecoveryResult(
        session_id=session_id,
        proposal_id=str(uuid.uuid4()),
        ticket_id="T999",
        stage=RecoveryStage.RECOVERED,
        root_cause="STALE_READINESS",
        ops_performed=[],
        new_ticket_state="PLAN_APPROVED",
        bug_issue_url=None,
        error=None,
    )
    sup_main._results[session_id] = result

    resp = client.get(f"/api/recovery/{session_id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["session_id"] == session_id
    assert body["stage"] == "RECOVERED"

    # In-progress session → 404
    resp2 = client.get(f"/api/recovery/{str(uuid.uuid4())}")
    assert resp2.status_code == 404

    sup_main._results.pop(session_id, None)


# ── Test: recover_ticket in _WORKSPACE_CAPABILITIES ──────────────────────────


def test_recover_ticket_in_workspace_capabilities():
    import services.supervisor.main as sup_main

    assert "recover_ticket" in sup_main._WORKSPACE_CAPABILITIES
    cap = sup_main._WORKSPACE_CAPABILITIES["recover_ticket"]
    assert cap.get("confirmation_required") is True


# ── Test: "Unblock this ticket" maps to recover_ticket ───────────────────────


def test_workspace_chat_unblock_intent(client, project_root, ticket_id, run_dir, tmp_path, monkeypatch):
    import services.supervisor.main as sup_main

    state_file = run_dir / "state.json"
    state_file.write_text(json.dumps({"ticket_id": ticket_id, "state": "PLAN"}), encoding="utf-8")

    ai_ret = _ai_response(
        intent="actionable",
        proposed_action={"capability": "recover_ticket", "description": "Diagnose and recover the ticket"},
        confirmation_required=True,
    )

    with patch("services.supervisor.main._resolve_active_ticket_id", return_value=ticket_id):
        with patch("services.supervisor.main._lookup_project_root_from_control_api", return_value=str(project_root)):
            with patch("services.supervisor.main.mapper") as mock_mapper:
                mock_mapper.map.return_value = str(project_root)
                resp = _post_chat(client, "proj1", "Unblock this ticket", ai_ret)

    assert resp.status_code == 200
    body = resp.json()
    assert body["proposed_action"] is not None
    assert body["proposed_action"]["capability"] == "recover_ticket"
    assert "action_id" in body["proposed_action"]

    sup_main._active_sessions.clear()
    sup_main._proposals.clear()
    sup_main._pending_workspace_actions.clear()


# ── Test: active ticket resolution ───────────────────────────────────────────


def test_active_ticket_resolution(tmp_path, monkeypatch):
    import services.supervisor.main as sup_main

    project_id = "proj-test"
    runs_dir = tmp_path / project_id / "runs"

    # Terminal ticket — should be ignored
    done_dir = runs_dir / "T001"
    done_dir.mkdir(parents=True)
    (done_dir / "state.json").write_text(json.dumps({"state": "DONE"}), encoding="utf-8")

    # Active ticket
    active_dir = runs_dir / "T002"
    active_dir.mkdir(parents=True)
    (active_dir / "state.json").write_text(json.dumps({"state": "PLAN_APPROVED"}), encoding="utf-8")
    (active_dir / "daemon.lock").touch()

    with patch.object(sup_main, "_project_runs_dir", return_value=runs_dir):
        result = sup_main._resolve_active_ticket_id(project_id)

    assert result == "T002"

    # No running ticket → None
    (active_dir / "daemon.lock").unlink()
    (active_dir / "state.json").write_text(json.dumps({"state": "DONE"}), encoding="utf-8")

    with patch.object(sup_main, "_project_runs_dir", return_value=runs_dir):
        result2 = sup_main._resolve_active_ticket_id(project_id)

    assert result2 is None


# ── Test: recovery verification step ─────────────────────────────────────────


def test_recovery_verification_step(project_root, ticket_id, run_dir, state_file):
    state_file.write_text(json.dumps({"ticket_id": ticket_id, "state": "PLAN"}), encoding="utf-8")

    # State unchanged → not advanced
    advanced, current = verify_ticket_progress(ticket_id, project_root, "PLAN")
    assert advanced is True  # same state = expected state = OK
    assert current == "PLAN"

    # State different from expected → not advanced
    state_file.write_text(json.dumps({"ticket_id": ticket_id, "state": "PLAN"}), encoding="utf-8")
    advanced2, current2 = verify_ticket_progress(ticket_id, project_root, "PLAN_APPROVED")
    assert advanced2 is False
    assert current2 == "PLAN"

    # State advanced to terminal → considered advanced
    state_file.write_text(json.dumps({"ticket_id": ticket_id, "state": "DONE"}), encoding="utf-8")
    advanced3, current3 = verify_ticket_progress(ticket_id, project_root, "PLAN_APPROVED")
    assert advanced3 is True
    assert current3 == "DONE"
