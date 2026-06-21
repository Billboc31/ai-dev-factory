"""Tests for ticket_approvals DB persistence (T199)."""

import importlib.util
import os
import sqlite3
import sys
from pathlib import Path

import pytest

_TOOLS = Path(__file__).parent.parent / "tools" / "agent_runner"
sys.path.insert(0, str(_TOOLS))


def _load_sqlite_runtime_db():
    """Load runtime_db as a fresh SQLite-mode module, bypassing any env rebinding."""
    spec = importlib.util.spec_from_file_location(
        "_runtime_db_sqlite_test_approvals",
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
init_runtime_db = _db.init_runtime_db
insert_ticket_approval = _db.insert_ticket_approval
list_ticket_approvals = _db.list_ticket_approvals
get_latest_ticket_approval = _db.get_latest_ticket_approval


@pytest.fixture()
def db(tmp_path: Path) -> Path:
    db_path = tmp_path / ".runtime" / "test.sqlite"
    init_runtime_db(db_path)
    return db_path


def test_schema_created(db: Path) -> None:
    with sqlite3.connect(str(db)) as conn:
        row = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='ticket_approvals'"
        ).fetchone()
    assert row is not None


def test_index_created(db: Path) -> None:
    with sqlite3.connect(str(db)) as conn:
        row = conn.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='index' AND name='ix_ticket_approvals_ticket'"
        ).fetchone()
    assert row is not None


def test_insert_returns_row_id_and_persists(db: Path) -> None:
    row_id = insert_ticket_approval(
        db, "T001",
        approval_type="execution",
        approval_status="approved",
        approved_by="pierre",
        approval_comment="ok",
    )
    assert isinstance(row_id, int) and row_id > 0
    rows = list_ticket_approvals(db, "T001")
    assert len(rows) == 1
    row = rows[0]
    assert row["id"] == row_id
    assert row["ticket_id"] == "T001"
    assert row["approval_type"] == "execution"
    assert row["approval_status"] == "approved"
    assert row["approved_by"] == "pierre"
    assert row["approval_comment"] == "ok"
    assert row["approved_at"]  # final decisions stamp approved_at
    assert row["created_at"] == row["updated_at"]


def test_pending_row_has_null_approved_at(db: Path) -> None:
    insert_ticket_approval(
        db, "T002",
        approval_type="execution",
        approval_status="pending",
    )
    row = get_latest_ticket_approval(db, "T002", "execution")
    assert row is not None
    assert row["approval_status"] == "pending"
    assert row["approved_at"] is None


def test_list_ordered_by_id_ascending(db: Path) -> None:
    id1 = insert_ticket_approval(db, "T003", "execution", "pending")
    id2 = insert_ticket_approval(db, "T003", "execution", "approved", approved_by="alice")
    id3 = insert_ticket_approval(db, "T003", "execution", "rejected", approved_by="bob")
    rows = list_ticket_approvals(db, "T003")
    assert [r["id"] for r in rows] == [id1, id2, id3]


def test_get_latest_returns_most_recent_for_type(db: Path) -> None:
    insert_ticket_approval(db, "T004", "execution", "pending")
    insert_ticket_approval(db, "T004", "execution", "approved", approved_by="alice")
    latest = get_latest_ticket_approval(db, "T004", "execution")
    assert latest is not None
    assert latest["approval_status"] == "approved"
    assert latest["approved_by"] == "alice"


def test_get_latest_returns_none_when_absent(db: Path) -> None:
    assert get_latest_ticket_approval(db, "T999", "execution") is None


def test_latest_scoped_by_approval_type(db: Path) -> None:
    insert_ticket_approval(db, "T005", "plan", "approved", approved_by="planner")
    insert_ticket_approval(db, "T005", "execution", "pending")
    plan_latest = get_latest_ticket_approval(db, "T005", "plan")
    exec_latest = get_latest_ticket_approval(db, "T005", "execution")
    assert plan_latest["approval_status"] == "approved"
    assert exec_latest["approval_status"] == "pending"


def test_history_is_append_only_never_overwritten(db: Path) -> None:
    insert_ticket_approval(db, "T006", "execution", "approved", approved_by="a")
    insert_ticket_approval(db, "T006", "execution", "approved", approved_by="b")
    rows = list_ticket_approvals(db, "T006")
    assert len(rows) == 2
    assert rows[0]["approved_by"] == "a"
    assert rows[1]["approved_by"] == "b"
