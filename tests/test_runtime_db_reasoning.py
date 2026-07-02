"""T222 — round-trip tests for reasoning fields and batch analysis summary."""

from __future__ import annotations

import importlib.util
import os
import sqlite3
import sys
from pathlib import Path

import pytest

_TOOLS = Path(__file__).parent.parent / "tools" / "agent_runner"
sys.path.insert(0, str(_TOOLS))


def _load_sqlite_runtime_db():
    spec = importlib.util.spec_from_file_location(
        "_runtime_db_sqlite_t222", _TOOLS / "runtime_db.py"
    )
    mod = importlib.util.module_from_spec(spec)
    saved = os.environ.get("RUNTIME_DB_BACKEND")
    os.environ["RUNTIME_DB_BACKEND"] = "sqlite"
    try:
        spec.loader.exec_module(mod)
    finally:
        if saved is None:
            os.environ.pop("RUNTIME_DB_BACKEND", None)
        else:
            os.environ["RUNTIME_DB_BACKEND"] = saved
    return mod


_db = _load_sqlite_runtime_db()


@pytest.fixture()
def db_path(tmp_path: Path) -> Path:
    path = tmp_path / ".runtime" / "t222.sqlite"
    _db.init_runtime_db(path)
    return path


def _seed_batch(db_path: Path, batch_id: str) -> None:
    _db.insert_backlog_batch(
        db_path,
        batch_id,
        status="collecting",
        created_at="2026-07-02T10:00:00Z",
        last_activity_at="2026-07-02T10:00:00Z",
    )


# ── migrations are idempotent ────────────────────────────────────────────────

def test_new_columns_added_by_init(db_path: Path) -> None:
    with sqlite3.connect(str(db_path)) as conn:
        batches_cols = {
            row[1] for row in conn.execute("PRAGMA table_info('backlog_batches')")
        }
        dep_cols = {
            row[1]
            for row in conn.execute("PRAGMA table_info('ticket_dependency_analysis')")
        }
    for col in (
        "analysis_summary_json",
        "raw_analyzer_output_json",
        "analysis_summary_generated_at",
    ):
        assert col in batches_cols
    for col in (
        "why_this_phase",
        "dependencies_inferred_json",
        "reasoning",
        "confidence",
    ):
        assert col in dep_cols


def test_migration_is_idempotent_on_pre_migration_db(tmp_path: Path) -> None:
    """Build a schema that predates T222 and confirm init_runtime_db upgrades it."""
    path = tmp_path / "legacy.sqlite"
    with sqlite3.connect(str(path)) as conn:
        # Pre-T222 shape (missing all new columns).
        conn.execute(
            """
            CREATE TABLE backlog_batches (
                batch_id                          TEXT PRIMARY KEY,
                status                            TEXT NOT NULL,
                created_at                        TEXT NOT NULL,
                frozen_at                         TEXT,
                last_activity_at                  TEXT NOT NULL,
                completed_at                      TEXT,
                freeze_blocked                    INTEGER NOT NULL DEFAULT 0,
                freeze_blocked_reason             TEXT,
                dependency_analysis_attempts      INTEGER NOT NULL DEFAULT 0,
                last_dependency_analysis_error    TEXT,
                next_dependency_analysis_retry_at TEXT,
                notes                             TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE ticket_dependency_analysis (
                ticket_id                          TEXT NOT NULL,
                batch_id                           TEXT NOT NULL,
                depends_on_json                    TEXT NOT NULL,
                blocks_json                        TEXT NOT NULL,
                parallel_group                     TEXT,
                conflicting_tickets_json           TEXT NOT NULL,
                execution_phase                    TEXT,
                relationship_classifications_json  TEXT NOT NULL,
                analyzed_at                        TEXT NOT NULL,
                PRIMARY KEY (ticket_id, batch_id)
            )
            """
        )

    _db.init_runtime_db(path)
    # Running init twice must still be a no-op.
    _db.init_runtime_db(path)

    with sqlite3.connect(str(path)) as conn:
        batches_cols = {
            row[1] for row in conn.execute("PRAGMA table_info('backlog_batches')")
        }
        dep_cols = {
            row[1]
            for row in conn.execute("PRAGMA table_info('ticket_dependency_analysis')")
        }
    assert "analysis_summary_json" in batches_cols
    assert "raw_analyzer_output_json" in batches_cols
    assert "analysis_summary_generated_at" in batches_cols
    assert "why_this_phase" in dep_cols
    assert "dependencies_inferred_json" in dep_cols
    assert "reasoning" in dep_cols
    assert "confidence" in dep_cols


# ── upsert / get round-trip ──────────────────────────────────────────────────

def test_upsert_dependency_analysis_persists_reasoning(db_path: Path) -> None:
    _seed_batch(db_path, "B0001")
    _db.upsert_dependency_analysis(
        db_path,
        ticket_id="T011",
        batch_id="B0001",
        depends_on=["T010"],
        blocks=[],
        parallel_group=None,
        conflicting_tickets=[],
        execution_phase="2",
        relationship_classifications=[
            {"from": "T011", "to": "T010", "type": "HARD_DEPENDENCY"},
        ],
        analyzed_at="2026-07-02T10:00:00Z",
        why_this_phase="Builds on T010.",
        dependencies_inferred=["T010 — foundation."],
        reasoning="Backend consumer.",
        confidence="high",
    )
    row = _db.get_dependency_analysis(db_path, "T011", "B0001")
    assert row["why_this_phase"] == "Builds on T010."
    assert row["dependencies_inferred"] == ["T010 — foundation."]
    assert row["reasoning"] == "Backend consumer."
    assert row["confidence"] == "high"


def test_upsert_dependency_analysis_defaults_when_reasoning_omitted(db_path: Path) -> None:
    _seed_batch(db_path, "B0002")
    _db.upsert_dependency_analysis(
        db_path,
        ticket_id="T010",
        batch_id="B0002",
        depends_on=[],
        blocks=[],
        parallel_group=None,
        conflicting_tickets=[],
        execution_phase="1",
        relationship_classifications=[],
        analyzed_at="2026-07-02T10:00:00Z",
    )
    row = _db.get_dependency_analysis(db_path, "T010", "B0002")
    assert row["why_this_phase"] is None
    assert row["dependencies_inferred"] == []
    assert row["reasoning"] is None
    assert row["confidence"] is None


# ── batch summary + raw output round-trip ────────────────────────────────────

def test_update_and_get_batch_analysis_summary(db_path: Path) -> None:
    _seed_batch(db_path, "B0003")
    summary = {
        "strategy": "Foundation first",
        "foundation_tickets": ["T001"],
        "warnings": ["T002 is thin"],
    }
    raw = {"stdout_excerpt": "…", "parsed": {"tickets": []}}
    _db.update_batch_analysis_summary(
        db_path,
        "B0003",
        analysis_summary=summary,
        raw_analyzer_output=raw,
        generated_at="2026-07-02T10:00:05Z",
    )
    fetched = _db.get_batch_analysis_summary(db_path, "B0003")
    assert fetched is not None
    assert fetched["analysis_summary"] == summary
    assert fetched["raw_analyzer_output"] == raw
    assert fetched["generated_at"] == "2026-07-02T10:00:05Z"


def test_get_batch_analysis_summary_returns_none_when_not_persisted(db_path: Path) -> None:
    _seed_batch(db_path, "B0004")
    assert _db.get_batch_analysis_summary(db_path, "B0004") is None


def test_get_batch_analysis_summary_unknown_batch_returns_none(db_path: Path) -> None:
    assert _db.get_batch_analysis_summary(db_path, "B_UNKNOWN") is None
