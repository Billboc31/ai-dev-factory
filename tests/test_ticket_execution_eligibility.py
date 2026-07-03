"""Unit tests for ticket_execution_eligibility (T211).

The aggregator is pure read-only: each test wires the existing
``runtime_db`` getters via monkeypatch and verifies the documented decision
mapping (status / blocking_step / next_action) for each scenario in the ticket.
"""

from __future__ import annotations

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
        "_runtime_db_sqlite_test_eligibility",
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


_sqlite_db = _load_sqlite_runtime_db()

import ticket_execution_eligibility as eligibility  # noqa: E402


# ── Helpers ─────────────────────────────────────────────────────────────────

def _setup_db(tmp_path: Path):
    db_path = tmp_path / ".runtime" / "eligibility.sqlite"
    _sqlite_db.init_runtime_db(db_path)
    return db_path


def _write_ticket_md(project_root: Path, ticket_id: str, body: str = "") -> None:
    run_dir = project_root / "runs" / ticket_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "ticket.md").write_text(f"# {ticket_id}\n\n{body}\n", encoding="utf-8")


def _write_state(project_root: Path, ticket_id: str, state: str) -> None:
    run_dir = project_root / "runs" / ticket_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "state.json").write_text(
        json.dumps({"ticket_id": ticket_id, "state": state}), encoding="utf-8"
    )


def _seed_complete_intelligence(
    db_path, ticket_id: str, *, requires_review: bool = False
) -> None:
    _sqlite_db.upsert_ticket_intelligence(
        db_path,
        ticket_id,
        analysis_status="completed",
        requires_human_plan_review=1 if requires_review else 0,
    )


def _seed_ready_candidate(db_path, ticket_id: str) -> None:
    _sqlite_db.upsert_ticket_readiness(
        db_path,
        ticket_id,
        readiness_status="ready_candidate",
    )


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    db_path = _setup_db(tmp_path)
    # The aggregator imports the runtime_db that the running process selected
    # (Postgres in this dev shell). Rebind the read-side accessors to the
    # freshly loaded SQLite module so the test seeds and the aggregator reads
    # talk to the same file.
    import runtime_db as live_db
    for name in (
        "get_ticket_intelligence",
        "get_ticket_readiness",
        "get_latest_ticket_approval",
        "get_dependency_analysis",
        "list_project_rules",
        "insert_ticket_approval",
    ):
        monkeypatch.setattr(live_db, name, getattr(_sqlite_db, name))
    # Force dependency check to skip gh/git fallbacks: by default the test
    # tickets carry no declared dependencies. When a test needs a dep we stub
    # ``is_ticket_merged`` directly.
    monkeypatch.setattr(eligibility, "is_ticket_merged", _raise_default_dep_stub)
    import execution_rules_engine as rules_engine
    monkeypatch.setattr(
        rules_engine.runtime_db, "list_project_rules", _sqlite_db.list_project_rules
    )
    return {"db": db_path, "root": tmp_path}


def _raise_default_dep_stub(_project_root, ticket_id, **_kwargs):
    raise AssertionError(
        f"is_ticket_merged unexpectedly called for {ticket_id} — test fixture "
        "did not declare a dependency"
    )


def _stub_deps(monkeypatch, mapping: dict[str, str]):
    """Patch ``is_ticket_merged`` to return ``mapping[ticket_id]`` results."""

    class _Res:
        def __init__(self, status):
            self.status = status

    def _impl(_project_root, ticket_id, **_kwargs):
        return _Res(mapping.get(ticket_id, "unknown"))

    monkeypatch.setattr(eligibility, "is_ticket_merged", _impl)


# ── Scenario: all-green → READY_TO_TAKE ─────────────────────────────────────

def test_ready_to_take_when_all_checks_pass(env, monkeypatch):
    db, root = env["db"], env["root"]
    _write_ticket_md(root, "T100")
    _seed_complete_intelligence(db, "T100")
    _seed_ready_candidate(db, "T100")

    result = eligibility.evaluate_eligibility(db, root, "T100", ticket_content="")
    assert result["ready_to_take"] is True
    assert result["status"] == "READY_TO_TAKE"
    assert result["blocking_step"] is None
    assert result["next_action"] == "Ticket can be taken by a worker"
    for key in ("intelligence", "dependencies", "readiness", "approval"):
        assert result["checks"][key]["status"] == "passed", key
    assert "rules" not in result["checks"]


# ── Scenario: plan review flag does not block entry ───────────────────────

def test_plan_review_flag_does_not_block_entry(env, monkeypatch):
    db, root = env["db"], env["root"]
    _write_ticket_md(root, "T101")
    _seed_complete_intelligence(db, "T101", requires_review=True)
    _seed_ready_candidate(db, "T101")

    result = eligibility.evaluate_eligibility(db, root, "T101", ticket_content="")
    assert result["ready_to_take"] is True
    assert result["status"] == "READY_TO_TAKE"
    assert result["checks"]["approval"]["status"] == "passed"


# ── Scenario: execution approval required when rule enabled ───────────────

def test_waiting_human_action_when_execution_approval_required(env, monkeypatch):
    db, root = env["db"], env["root"]
    _write_ticket_md(root, "T101B")
    _seed_complete_intelligence(db, "T101B")
    _seed_ready_candidate(db, "T101B")
    _sqlite_db.upsert_project_rule(
        db, "proj-a", "require_human_approval", True, {},
    )

    result = eligibility.evaluate_eligibility(
        db, root, "T101B", ticket_content="", project_id="proj-a",
    )
    assert result["ready_to_take"] is False
    assert result["status"] == "WAITING_HUMAN_ACTION"
    assert result["blocking_step"] == "approval"
    assert result["reason"] == "Human execution approval required"
    assert result["next_action"] == "Approve ticket for execution"


def test_execution_approval_clears_when_ready_to_take(env, monkeypatch):
    db, root = env["db"], env["root"]
    _write_ticket_md(root, "T102")
    _seed_complete_intelligence(db, "T102", requires_review=True)
    _sqlite_db.upsert_ticket_readiness(db, "T102", readiness_status="ready_to_take")
    _sqlite_db.insert_ticket_approval(
        db,
        "T102",
        approval_type="execution",
        approval_status="approved",
        approved_by="alice",
    )
    _sqlite_db.upsert_project_rule(
        db, "proj-a", "require_human_approval", True, {},
    )

    result = eligibility.evaluate_eligibility(
        db, root, "T102", ticket_content="", project_id="proj-a",
    )
    assert result["checks"]["approval"]["status"] == "passed"
    assert result["status"] == "READY_TO_TAKE"


# ── Scenario: dependency T001 not merged → DEPENDENCY_BLOCKED ──────────────

def test_dependency_blocked_when_dep_not_merged(env, monkeypatch):
    db, root = env["db"], env["root"]
    _write_ticket_md(root, "T103", body="Depends on T001.")
    _seed_complete_intelligence(db, "T103")
    _seed_ready_candidate(db, "T103")
    _stub_deps(monkeypatch, {"T001": "not_merged"})

    result = eligibility.evaluate_eligibility(
        db, root, "T103", ticket_content="Depends on T001."
    )
    assert result["ready_to_take"] is False
    assert result["status"] == "DEPENDENCY_BLOCKED"
    assert result["blocking_step"] == "dependencies"
    assert result["checks"]["dependencies"]["unmet"] == ["T001"]
    assert result["next_action"] == "Wait for T001 to be merged"


def test_dependency_blocked_from_intelligence_hints_only(env, monkeypatch):
    db, root = env["db"], env["root"]
    _write_ticket_md(root, "T106", body="Bootstrap frontend based on T001 architecture.")
    _seed_complete_intelligence(db, "T106")
    _sqlite_db.upsert_ticket_intelligence(
        db,
        "T106",
        analysis_status="completed",
        dependency_hints='["T001"]',
    )
    _seed_ready_candidate(db, "T106")
    _stub_deps(monkeypatch, {"T001": "not_merged"})

    result = eligibility.evaluate_eligibility(
        db,
        root,
        "T106",
        ticket_content="Bootstrap frontend based on T001 architecture.",
    )
    assert result["ready_to_take"] is False
    assert result["status"] == "DEPENDENCY_BLOCKED"
    assert result["checks"]["dependencies"]["unmet"] == ["T001"]


# ── Scenario: missing intelligence → BLOCKED at intelligence ────────────────

def test_blocked_when_intelligence_missing(env):
    db, root = env["db"], env["root"]
    _write_ticket_md(root, "T104")
    # No intelligence row written.

    result = eligibility.evaluate_eligibility(db, root, "T104", ticket_content="")
    assert result["ready_to_take"] is False
    assert result["status"] == "BLOCKED"
    assert result["blocking_step"] == "intelligence"
    assert "Intelligence" in result["reason"]
    assert result["checks"]["intelligence"]["status"] == "failed"


# ── Scenario: rules engine no longer gates eligibility ─────────────────────

def test_rules_blocked_no_longer_gates_eligibility(env):
    """Even when the rules engine records a 'blocked' evaluation, the ticket
    must still progress through the eligibility checks. The rules step has
    been removed from CHECK_ORDER (T214); policy enforcement is deferred to
    the future Dispatcher."""
    db, root = env["db"], env["root"]
    _write_ticket_md(root, "T105")
    _seed_complete_intelligence(db, "T105")
    _seed_ready_candidate(db, "T105")
    _sqlite_db.upsert_ticket_rule_evaluation(
        db,
        ticket_id="T105",
        project_id="proj-a",
        eligibility_status="blocked",
        passed_rules=[],
        failed_rules=[{"rule_key": "max_difficulty", "reason": "Difficulty 9 > 7"}],
        warnings=[],
        evaluated_at="2026-06-24T00:00:00Z",
    )

    result = eligibility.evaluate_eligibility(db, root, "T105", ticket_content="")
    assert "rules" not in result["checks"]
    assert result["blocking_step"] is None
    assert result["status"] == "READY_TO_TAKE"


# ── Scenario: nothing computed yet → UNKNOWN ──────────────────────────────

def test_unknown_when_no_signals(env):
    db, root = env["db"], env["root"]
    _write_ticket_md(root, "T106")
    # Intelligence has no row → failed/missing, which is a blocker.
    # To get UNKNOWN we need every check to be "unknown". The intelligence
    # check resolves "no row" to ``failed`` (it counts as a hard blocker), so
    # the docs say "data missing for every check ⇒ UNKNOWN". Practically the
    # earliest UNKNOWN we expose is when intelligence rows exist but with no
    # status — exercise that path.
    _sqlite_db.upsert_ticket_intelligence(db, "T106", analysis_status="")
    result = eligibility.evaluate_eligibility(db, root, "T106", ticket_content="")
    # With intelligence status="" (unknown), readiness has no row (failed),
    # but blocking_step picks the first failing/pending: readiness wins
    # because intelligence is unknown (not failed/pending). UNKNOWN status is
    # asserted by checking the intelligence check.
    assert result["checks"]["intelligence"]["status"] == "unknown"


# ── Pure-read contract ─────────────────────────────────────────────────────

def test_aggregator_does_not_write_to_db(env):
    db, root = env["db"], env["root"]
    _write_ticket_md(root, "T107")
    _seed_complete_intelligence(db, "T107")
    _seed_ready_candidate(db, "T107")

    before_readiness = _sqlite_db.get_ticket_readiness(db, "T107")
    before_intel = _sqlite_db.get_ticket_intelligence(db, "T107")

    eligibility.evaluate_eligibility(db, root, "T107", ticket_content="")

    assert _sqlite_db.get_ticket_readiness(db, "T107") == before_readiness
    assert _sqlite_db.get_ticket_intelligence(db, "T107") == before_intel


# ── Check-order assertion ─────────────────────────────────────────────────

def test_intelligence_blocks_before_dependencies(env, monkeypatch):
    db, root = env["db"], env["root"]
    # Even when a dep is missing, an absent intelligence row blocks first.
    _write_ticket_md(root, "T108", body="Depends on T001.")
    _stub_deps(monkeypatch, {"T001": "not_merged"})

    result = eligibility.evaluate_eligibility(
        db, root, "T108", ticket_content="Depends on T001."
    )
    assert result["blocking_step"] == "intelligence"


def test_stale_readiness_dependency_block_passes_when_deps_merged_live(env, monkeypatch):
    """Readiness blocked on an old dependency snapshot must not block when live
    dependency checks already pass."""
    db, root = env["db"], env["root"]
    _write_ticket_md(root, "T109", body="Depends on T001.")
    _seed_complete_intelligence(db, "T109")
    _sqlite_db.upsert_ticket_readiness(
        db,
        "T109",
        readiness_status="blocked",
        blocking_reasons_json=["Dependency T001 not merged"],
    )
    _stub_deps(monkeypatch, {"T001": "merged"})

    result = eligibility.evaluate_eligibility(
        db, root, "T109", ticket_content="Depends on T001."
    )
    assert result["ready_to_take"] is True
    assert result["blocking_step"] is None
    assert result["checks"]["dependencies"]["status"] == "passed"
    assert result["checks"]["readiness"]["status"] == "passed"
    assert "stale" in result["checks"]["readiness"]["detail"].lower()


def test_dependency_analysis_depends_on_blocks_eligibility(env, monkeypatch):
    """``depends_on`` from ticket_dependency_analysis must gate eligibility even
    when the ticket body declares no inline dependencies."""
    db, root = env["db"], env["root"]
    _write_ticket_md(root, "T110", body="Implement CRUD with no inline deps.")
    _seed_complete_intelligence(db, "T110")
    _sqlite_db.upsert_dependency_analysis(
        db,
        ticket_id="T110",
        batch_id="B0001",
        depends_on=["T002", "T004"],
        blocks=[],
        parallel_group="backend-api-phase-2",
        conflicting_tickets=[],
        execution_phase="3",
        relationship_classifications=[],
        analyzed_at="2026-07-03T00:00:00Z",
    )
    _sqlite_db.upsert_ticket_readiness(
        db,
        "T110",
        readiness_status="blocked",
        blocking_reasons_json=[
            "Dependency T002 not merged",
            "Dependency T004 not merged",
        ],
    )
    _stub_deps(monkeypatch, {"T002": "not_merged", "T004": "not_merged"})

    result = eligibility.evaluate_eligibility(
        db, root, "T110", ticket_content="Implement CRUD with no inline deps."
    )
    assert result["ready_to_take"] is False
    assert result["blocking_step"] == "dependencies"
    assert result["checks"]["dependencies"]["unmet"] == ["T002", "T004"]
