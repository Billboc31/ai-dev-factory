"""Item 5: migration tool idempotency + project scoping + safe duplicate handling.

Uses a real temporary SQLite source and a fake Postgres backend (the keyed
tables behave like upserts; runtime_events is append-only) to prove that
re-running the migration does not duplicate rows or corrupt existing ones.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest

_AGENT_RUNNER = Path(__file__).parent.parent / "tools" / "agent_runner"
sys.path.insert(0, str(_AGENT_RUNNER))

import runtime_db_pg as pg  # noqa: E402
import migrate_sqlite_to_pg as mig  # noqa: E402


def _make_legacy_sqlite(path: Path) -> None:
    conn = sqlite3.connect(str(path))
    conn.executescript(
        """
        CREATE TABLE issue_intake (issue_number INTEGER PRIMARY KEY, ticket_id TEXT,
            branch TEXT, status TEXT, ingested_at TEXT, updated_at TEXT, last_error TEXT);
        CREATE TABLE ticket_runtime (ticket_id TEXT PRIMARY KEY, issue_number INTEGER,
            branch TEXT, state TEXT, run_dir TEXT, worktree_path TEXT, daemon_archived INTEGER,
            pr_number INTEGER, pr_state TEXT, last_transition TEXT, last_error TEXT, updated_at TEXT);
        CREATE TABLE workers (ticket_id TEXT PRIMARY KEY, pid INTEGER, branch TEXT,
            worktree_path TEXT, status TEXT, started_at TEXT, heartbeat_at TEXT, updated_at TEXT);
        CREATE TABLE runtime_events (id INTEGER PRIMARY KEY AUTOINCREMENT, ticket_id TEXT,
            event_type TEXT, message TEXT, metadata_json TEXT, created_at TEXT);
        INSERT INTO issue_intake VALUES (10, 'T010', 'b', 'ingested', 'x', 'x', NULL);
        INSERT INTO ticket_runtime (ticket_id, issue_number, state, daemon_archived) VALUES ('T010', 10, 'TEST_COMPLETE', 1);
        INSERT INTO ticket_runtime (ticket_id, issue_number, state, daemon_archived) VALUES ('T011', 11, 'CODING', 0);
        INSERT INTO runtime_events (ticket_id, event_type, message) VALUES ('T010', 'merged', 'done');
        """
    )
    conn.commit()
    conn.close()


@pytest.fixture()
def fake_pg(monkeypatch):
    """A minimal in-memory Postgres double that mirrors the real semantics."""
    store = {"tickets": {}, "intake": {}, "workers": {}, "events": []}

    class _H:
        def __init__(self, project_id):
            self.project_id = project_id
            self.dbname = "adf"

    monkeypatch.setattr(pg, "get_handle", lambda pid=None: _H(pid or "ai-dev-factory"))
    monkeypatch.setattr(pg, "init_runtime_db", lambda h: None)

    def record_intake(h, issue_number, ticket_id, branch=None, status="ingested"):
        store["intake"][(h.project_id, issue_number)] = ticket_id

    def upsert_ticket(h, ticket_id, **fields):
        store["tickets"][(h.project_id, ticket_id)] = dict(fields)

    def upsert_worker(h, ticket_id, pid, branch, worktree_path):
        store["workers"][(h.project_id, ticket_id)] = pid

    def append_event(h, ticket_id, event_type, message, metadata=None):
        store["events"].append((h.project_id, ticket_id, event_type))

    def list_events(h, ticket_id=None, limit=100):
        return [e for e in store["events"] if e[0] == h.project_id]

    monkeypatch.setattr(pg, "record_issue_intake", record_intake)
    monkeypatch.setattr(pg, "upsert_ticket_runtime", upsert_ticket)
    monkeypatch.setattr(pg, "upsert_worker", upsert_worker)
    monkeypatch.setattr(pg, "append_runtime_event", append_event)
    monkeypatch.setattr(pg, "list_runtime_events", list_events)
    return store


def test_migration_is_idempotent_and_project_scoped(tmp_path, fake_pg):
    src = tmp_path / "legacy.sqlite"
    _make_legacy_sqlite(src)

    first = mig.migrate(src, "ai-dev-factory")
    assert first == {"issue_intake": 1, "ticket_runtime": 2, "workers": 0, "runtime_events": 1}

    # Keyed tables landed exactly once, tagged with the project_id.
    assert set(fake_pg["tickets"]) == {("ai-dev-factory", "T010"), ("ai-dev-factory", "T011")}
    assert len(fake_pg["events"]) == 1

    # Re-run: upserts overwrite (no duplication) and events are NOT re-appended
    # (the per-project guard sees existing events).
    second = mig.migrate(src, "ai-dev-factory")
    assert second["ticket_runtime"] == 2
    assert second["runtime_events"] == 0
    assert len(fake_pg["tickets"]) == 2
    assert len(fake_pg["events"]) == 1


def test_migration_scopes_to_requested_project(tmp_path, fake_pg):
    src = tmp_path / "legacy.sqlite"
    _make_legacy_sqlite(src)
    mig.migrate(src, "test-ai-dev")
    assert all(key[0] == "test-ai-dev" for key in fake_pg["tickets"])
