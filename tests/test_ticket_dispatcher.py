"""Unit tests for ticket_dispatcher (T212).

The dispatcher is read-only: each test wires the runtime_db getters via
monkeypatch to a freshly loaded SQLite module, seeds tickets / intelligence /
readiness / rules rows, and verifies that recommendations are computed
without writing back to the DB.
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
        "_runtime_db_sqlite_test_dispatcher",
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

import ticket_dispatcher as dispatcher  # noqa: E402
import ticket_execution_eligibility as eligibility  # noqa: E402


# ── Helpers ─────────────────────────────────────────────────────────────────

def _setup_db(tmp_path: Path):
    db_path = tmp_path / ".runtime" / "dispatcher.sqlite"
    _sqlite_db.init_runtime_db(db_path)
    return db_path


def _write_ticket_md(project_root: Path, ticket_id: str, body: str = "") -> None:
    run_dir = project_root / "runs" / ticket_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "ticket.md").write_text(
        f"# {ticket_id}\n\n{body}\n", encoding="utf-8"
    )


def _write_state(project_root: Path, ticket_id: str, state: str) -> None:
    run_dir = project_root / "runs" / ticket_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "state.json").write_text(
        json.dumps({"ticket_id": ticket_id, "state": state}),
        encoding="utf-8",
    )


def _seed_ticket_runtime(db_path, ticket_id: str, *, state: str = "INIT") -> None:
    _sqlite_db.upsert_ticket_runtime(
        db_path,
        ticket_id,
        state=state,
        branch=f"ticket/{ticket_id}",
    )


def _seed_intelligence(
    db_path,
    ticket_id: str,
    *,
    queue_rank: int | None = None,
    difficulty_label: str | None = None,
    difficulty_score: int | None = None,
    requires_review: bool = False,
) -> None:
    fields: dict = {
        "analysis_status": "completed",
        "requires_human_plan_review": 1 if requires_review else 0,
    }
    if queue_rank is not None:
        fields["queue_rank"] = queue_rank
    if difficulty_label is not None:
        fields["difficulty_label"] = difficulty_label
    if difficulty_score is not None:
        fields["difficulty_score"] = difficulty_score
    _sqlite_db.upsert_ticket_intelligence(db_path, ticket_id, **fields)


def _seed_ready_candidate(db_path, ticket_id: str) -> None:
    _sqlite_db.upsert_ticket_readiness(
        db_path, ticket_id, readiness_status="ready_candidate"
    )


def _seed_rules_eligible(db_path, ticket_id: str, project_id: str = "proj-a") -> None:
    _sqlite_db.upsert_ticket_rule_evaluation(
        db_path,
        ticket_id=ticket_id,
        project_id=project_id,
        eligibility_status="eligible",
        passed_rules=[],
        failed_rules=[],
        warnings=[],
        evaluated_at="2026-06-24T00:00:00Z",
    )


def _seed_full_ready(
    db_path,
    project_root: Path,
    ticket_id: str,
    *,
    queue_rank: int | None = None,
    difficulty_label: str | None = None,
    difficulty_score: int | None = None,
) -> None:
    _write_ticket_md(project_root, ticket_id)
    _seed_ticket_runtime(db_path, ticket_id)
    _seed_intelligence(
        db_path,
        ticket_id,
        queue_rank=queue_rank,
        difficulty_label=difficulty_label,
        difficulty_score=difficulty_score,
    )
    _seed_ready_candidate(db_path, ticket_id)
    _seed_rules_eligible(db_path, ticket_id)


def _raise_default_dep_stub(_project_root, ticket_id, **_kwargs):
    raise AssertionError(
        f"is_ticket_merged unexpectedly called for {ticket_id} — test fixture "
        "did not declare a dependency"
    )


@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)
    monkeypatch.delenv("AI_DEV_FACTORY_DISPATCHER_MODE", raising=False)
    db_path = _setup_db(tmp_path)

    import runtime_db as live_db
    for name in (
        "get_ticket_intelligence",
        "get_ticket_readiness",
        "get_ticket_rule_evaluation",
        "get_latest_ticket_approval",
        "list_ticket_runtime",
    ):
        monkeypatch.setattr(live_db, name, getattr(_sqlite_db, name))
    monkeypatch.setattr(eligibility, "is_ticket_merged", _raise_default_dep_stub)
    return {"db": db_path, "root": tmp_path}


# ── Mode resolution ─────────────────────────────────────────────────────────

def test_default_mode_is_off(env, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_DISPATCHER_MODE", raising=False)
    assert dispatcher.get_dispatcher_mode() == "off"


def test_unknown_mode_falls_back_to_off(env, monkeypatch):
    monkeypatch.setenv("AI_DEV_FACTORY_DISPATCHER_MODE", "bogus")
    assert dispatcher.get_dispatcher_mode() == "off"


def test_advisory_mode_resolved(env, monkeypatch):
    monkeypatch.setenv("AI_DEV_FACTORY_DISPATCHER_MODE", "advisory")
    assert dispatcher.get_dispatcher_mode() == "advisory"


# ── off mode short-circuits ────────────────────────────────────────────────

def test_off_mode_returns_empty_and_skips_eligibility(env, monkeypatch):
    db, root = env["db"], env["root"]
    _seed_full_ready(db, root, "T010", queue_rank=1)

    called: list[str] = []

    def _spy(*args, **kwargs):  # noqa: ARG001
        called.append("called")
        return {"ready_to_take": True}

    monkeypatch.setattr(eligibility, "evaluate_eligibility", _spy)

    result = dispatcher.get_recommended_tickets(db, root, mode="off")
    assert result["mode"] == "off"
    assert result["recommendations"] == []
    assert result["blocked"] == []
    assert called == []  # eligibility was never invoked


def test_default_mode_off_via_env(env, monkeypatch):
    db, root = env["db"], env["root"]
    monkeypatch.delenv("AI_DEV_FACTORY_DISPATCHER_MODE", raising=False)
    _seed_full_ready(db, root, "T011")
    result = dispatcher.get_recommended_tickets(db, root)
    assert result["mode"] == "off"
    assert result["recommendations"] == []


# ── advisory mode ranks READY_TO_TAKE tickets ─────────────────────────────

def test_advisory_returns_ranked_ready_tickets(env):
    db, root = env["db"], env["root"]
    _seed_full_ready(db, root, "T020", queue_rank=10, difficulty_label="moderate")
    _seed_full_ready(db, root, "T021", queue_rank=1, difficulty_label="simple")
    _seed_full_ready(db, root, "T022", queue_rank=5, difficulty_label="hard")

    result = dispatcher.get_recommended_tickets(db, root, mode="advisory")
    assert result["mode"] == "advisory"
    recs = result["recommendations"]
    assert len(recs) == 3
    # T021 should rank first (queue_rank=1 + difficulty bonus).
    assert recs[0]["ticket_id"] == "T021"
    assert recs[0]["rank"] == 1
    assert recs[0]["score"] > 50
    assert "READY_TO_TAKE" in recs[0]["reason"]
    for index, rec in enumerate(recs, start=1):
        assert rec["rank"] == index
        assert rec["ready_to_take"] is True
        assert "intelligence" in rec


# ── Blocked tickets land in `blocked` with blocking_step / reason ─────────

def test_blocked_tickets_are_reported(env):
    db, root = env["db"], env["root"]
    # Missing intelligence → ticket is blocked at the intelligence step.
    _write_ticket_md(root, "T030")
    _seed_ticket_runtime(db, "T030")

    result = dispatcher.get_recommended_tickets(db, root, mode="advisory")
    assert result["recommendations"] == []
    assert len(result["blocked"]) == 1
    entry = result["blocked"][0]
    assert entry["ticket_id"] == "T030"
    assert entry["ready_to_take"] is False
    assert entry["blocking_step"] == "intelligence"
    assert entry["reason"]


def test_dependency_blocked_from_markdown_section_in_worktree(env, monkeypatch):
    db, root = env["db"], env["root"]
    worktrees_dir = root / "worktrees"
    wt_run = worktrees_dir / "T070" / "runs" / "T070"
    wt_run.mkdir(parents=True)
    (wt_run / "ticket.md").write_text(
        "# T070\n\n## Depends on\n- T010 - prerequisite\n",
        encoding="utf-8",
    )
    _seed_ticket_runtime(db, "T070")
    _seed_intelligence(db, "T070", queue_rank=1)
    _seed_ready_candidate(db, "T070")
    _seed_rules_eligible(db, "T070")

    def _dep_status(_project_root, dep_id, **_kwargs):
        from ticket_merge_state import MergeCheckResult

        return MergeCheckResult(status="not_merged", source="test")

    monkeypatch.setattr(eligibility, "is_ticket_merged", _dep_status)

    result = dispatcher.get_recommended_tickets(
        db, root, mode="advisory", worktrees_dir=worktrees_dir,
    )
    assert result["recommendations"] == []
    assert len(result["blocked"]) == 1
    entry = result["blocked"][0]
    assert entry["ticket_id"] == "T070"
    assert entry["blocking_step"] == "dependencies"
    assert "T010" in entry["reason"]


# ── Deterministic ordering on ties ────────────────────────────────────────

def test_ranking_is_deterministic_on_ties(env):
    db, root = env["db"], env["root"]
    # Same queue_rank and same difficulty → tie should fall back to
    # updated_at then ticket_id.
    _seed_full_ready(db, root, "T040", queue_rank=5, difficulty_label="moderate")
    _seed_full_ready(db, root, "T041", queue_rank=5, difficulty_label="moderate")
    _seed_full_ready(db, root, "T042", queue_rank=5, difficulty_label="moderate")

    result_a = dispatcher.get_recommended_tickets(db, root, mode="advisory")
    result_b = dispatcher.get_recommended_tickets(db, root, mode="advisory")
    ids_a = [r["ticket_id"] for r in result_a["recommendations"]]
    ids_b = [r["ticket_id"] for r in result_b["recommendations"]]
    assert ids_a == ids_b
    # Stable tiebreak by ticket_id once updated_at is identical.
    assert ids_a == sorted(ids_a)


# ── auto mode is reserved ─────────────────────────────────────────────────

def test_auto_mode_returns_not_implemented(env):
    db, root = env["db"], env["root"]
    _seed_full_ready(db, root, "T050")
    result = dispatcher.get_recommended_tickets(db, root, mode="auto")
    assert result["mode"] == "auto"
    assert result.get("not_implemented") is True
    assert result["recommendations"] == []


# ── Pure-read contract: DB is unchanged ──────────────────────────────────

def test_dispatcher_does_not_write_to_db(env):
    db, root = env["db"], env["root"]
    _seed_full_ready(db, root, "T060", queue_rank=2, difficulty_label="simple")
    _seed_full_ready(db, root, "T061", queue_rank=4)

    before = db.read_bytes()
    before_intel = _sqlite_db.get_ticket_intelligence(db, "T060")
    before_readiness = _sqlite_db.get_ticket_readiness(db, "T060")
    before_rules = _sqlite_db.get_ticket_rule_evaluation(db, "T060")

    dispatcher.get_recommended_tickets(db, root, mode="advisory")
    dispatcher.get_recommended_tickets(db, root, mode="manual")

    after = db.read_bytes()
    assert before == after, "dispatcher must not write to the runtime DB"
    assert _sqlite_db.get_ticket_intelligence(db, "T060") == before_intel
    assert _sqlite_db.get_ticket_readiness(db, "T060") == before_readiness
    assert _sqlite_db.get_ticket_rule_evaluation(db, "T060") == before_rules


# ── Excluded states never appear in recommendations ──────────────────────

def test_excluded_states_are_skipped(env):
    db, root = env["db"], env["root"]
    _seed_full_ready(db, root, "T070")
    # Override the runtime state to an excluded one.
    _sqlite_db.upsert_ticket_runtime(db, "T070", state="CODING")

    result = dispatcher.get_recommended_tickets(db, root, mode="advisory")
    assert all(r["ticket_id"] != "T070" for r in result["recommendations"])
    assert all(b["ticket_id"] != "T070" for b in result["blocked"])


# ── is_dispatcher_enabled mirrors the resolved mode ─────────────────────

def test_is_dispatcher_enabled_off(env, monkeypatch):
    monkeypatch.delenv("AI_DEV_FACTORY_DISPATCHER_MODE", raising=False)
    assert dispatcher.is_dispatcher_enabled() is False


def test_is_dispatcher_enabled_unknown_falls_back_to_off(env, monkeypatch):
    monkeypatch.setenv("AI_DEV_FACTORY_DISPATCHER_MODE", "bogus")
    assert dispatcher.is_dispatcher_enabled() is False


@pytest.mark.parametrize("mode", ["advisory", "manual", "auto"])
def test_is_dispatcher_enabled_true_for_non_off_modes(env, monkeypatch, mode):
    monkeypatch.setenv("AI_DEV_FACTORY_DISPATCHER_MODE", mode)
    assert dispatcher.is_dispatcher_enabled() is True


# ── manual returns same recommendations as advisory ──────────────────────

def test_manual_mode_recommendations_match_advisory(env):
    db, root = env["db"], env["root"]
    _seed_full_ready(db, root, "T080", queue_rank=3, difficulty_label="simple")
    _seed_full_ready(db, root, "T081", queue_rank=7)
    advisory = dispatcher.get_recommended_tickets(db, root, mode="advisory")
    manual = dispatcher.get_recommended_tickets(db, root, mode="manual")
    assert [r["ticket_id"] for r in advisory["recommendations"]] == [
        r["ticket_id"] for r in manual["recommendations"]
    ]
    assert manual["mode"] == "manual"
