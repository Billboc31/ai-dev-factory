"""Tests for ticket_intelligence DB persistence (T197)."""

import importlib
import importlib.util
import sys
from pathlib import Path

import pytest

_TOOLS = Path(__file__).parent.parent / "tools" / "agent_runner"
sys.path.insert(0, str(_TOOLS))


def _load_sqlite_runtime_db():
    """Load runtime_db as a fresh SQLite-mode module, bypassing any env rebinding."""
    spec = importlib.util.spec_from_file_location(
        "_runtime_db_sqlite_test",
        _TOOLS / "runtime_db.py",
    )
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    import os
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
init_runtime_db = _db.init_runtime_db
upsert_ticket_intelligence = _db.upsert_ticket_intelligence
get_ticket_intelligence = _db.get_ticket_intelligence


@pytest.fixture()
def db(tmp_path: Path) -> Path:
    db_path = tmp_path / ".runtime" / "test.sqlite"
    init_runtime_db(db_path)
    return db_path


def test_upsert_insert(db: Path) -> None:
    upsert_ticket_intelligence(db, "T001", analysis_status="queued")
    row = get_ticket_intelligence(db, "T001")
    assert row is not None
    assert row["ticket_id"] == "T001"
    assert row["analysis_status"] == "queued"


def test_upsert_update_does_not_duplicate(db: Path) -> None:
    upsert_ticket_intelligence(db, "T001", analysis_status="queued")
    upsert_ticket_intelligence(db, "T001", analysis_status="completed", difficulty_score=5)
    row = get_ticket_intelligence(db, "T001")
    assert row is not None
    assert row["analysis_status"] == "completed"
    assert row["difficulty_score"] == 5
    # created_at unchanged, updated_at may differ
    import sqlite3
    with sqlite3.connect(str(db)) as conn:
        rows = conn.execute("SELECT * FROM ticket_intelligence WHERE ticket_id = 'T001'").fetchall()
    assert len(rows) == 1


def test_get_returns_none_when_absent(db: Path) -> None:
    assert get_ticket_intelligence(db, "T999") is None


def test_upsert_created_at_preserved(db: Path) -> None:
    upsert_ticket_intelligence(db, "T001", analysis_status="queued")
    row1 = get_ticket_intelligence(db, "T001")
    created_at_1 = row1["created_at"]

    upsert_ticket_intelligence(db, "T001", analysis_status="running")
    row2 = get_ticket_intelligence(db, "T001")
    assert row2["created_at"] == created_at_1


def test_upsert_all_fields(db: Path) -> None:
    upsert_ticket_intelligence(
        db, "T001",
        analysis_status="completed",
        difficulty_score=6,
        difficulty_label="medium",
        risk_score=5,
        risk_label="moderate",
        complexity_factors='["backend", "database"]',
        computed_signals_json='{"text_length": 1000}',
        recommended_model="advanced-reasoning-model",
        recommended_model_reason="needs reasoning",
        estimated_input_tokens=10000,
        estimated_output_tokens=5000,
        estimated_cost_min=0.05,
        estimated_cost_max=0.25,
        cost_currency="USD",
        cost_estimate_status="estimated",
        queue_rank=20,
        queue_reason="foundational ticket",
        dependency_hints='["T001"]',
        parallel_safe_candidate=0,
        requires_human_plan_review=1,
        human_plan_review_reason="schema change",
        requires_human_code_review=0,
        human_code_review_reason=None,
        autonomous_execution_recommendation="plan_review_required",
        analysis_summary="medium difficulty ticket",
    )
    row = get_ticket_intelligence(db, "T001")
    assert row is not None
    assert row["difficulty_score"] == 6
    assert row["difficulty_label"] == "medium"
    assert row["risk_score"] == 5
    assert row["recommended_model"] == "advanced-reasoning-model"
    assert row["estimated_cost_min"] == pytest.approx(0.05)
    assert row["requires_human_plan_review"] == 1
    assert row["autonomous_execution_recommendation"] == "plan_review_required"


def test_default_status_on_insert(db: Path) -> None:
    upsert_ticket_intelligence(db, "T002")
    row = get_ticket_intelligence(db, "T002")
    assert row is not None
    assert row["analysis_status"] == "not_started"


def test_multiple_tickets_isolated(db: Path) -> None:
    upsert_ticket_intelligence(db, "T001", analysis_status="completed", difficulty_score=3)
    upsert_ticket_intelligence(db, "T002", analysis_status="failed", difficulty_score=8)
    row1 = get_ticket_intelligence(db, "T001")
    row2 = get_ticket_intelligence(db, "T002")
    assert row1["difficulty_score"] == 3
    assert row2["difficulty_score"] == 8


# ── T210: stage column ────────────────────────────────────────────────────────


def test_upsert_persists_stage(db: Path) -> None:
    upsert_ticket_intelligence(db, "T001", analysis_status="running", stage="waiting_ai")
    row = get_ticket_intelligence(db, "T001")
    assert row is not None
    assert row["stage"] == "waiting_ai"

    upsert_ticket_intelligence(db, "T001", analysis_status="completed", stage="completed")
    row = get_ticket_intelligence(db, "T001")
    assert row["stage"] == "completed"


def test_migration_adds_stage_column_to_existing_db(tmp_path: Path) -> None:
    """An older DB without the stage column gets it on the next init_runtime_db()."""
    import sqlite3
    db_path = tmp_path / ".runtime" / "legacy.sqlite"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    # Create the pre-T210 schema (no stage column).
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(
            """
            CREATE TABLE ticket_intelligence (
                ticket_id           TEXT PRIMARY KEY,
                analysis_status     TEXT NOT NULL DEFAULT 'not_started',
                created_at          TEXT NOT NULL,
                updated_at          TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "INSERT INTO ticket_intelligence (ticket_id, analysis_status, created_at, updated_at) "
            "VALUES ('T_legacy', 'completed', '2026-01-01T00:00:00Z', '2026-01-01T00:00:00Z')"
        )

    _db.init_runtime_db(db_path)

    with sqlite3.connect(str(db_path)) as conn:
        cols = {row[1] for row in conn.execute("PRAGMA table_info('ticket_intelligence')")}
    assert "stage" in cols

    row = get_ticket_intelligence(db_path, "T_legacy")
    assert row is not None
    assert row["analysis_status"] == "completed"
    assert row["stage"] is None
