#!/usr/bin/env python3
"""One-shot migration of the runtime store from SQLite to Postgres.

Copies issue_intake, ticket_runtime, workers and runtime_events from a legacy
SQLite file into the per-project Postgres database (adf_<project_id>).

Idempotent for the keyed tables (issue_intake/ticket_runtime/workers use
upserts). runtime_events is append-only, so events are migrated only when the
target events table is empty to avoid duplication on re-runs.

Usage (typically inside the API container, which has psycopg + the Postgres env):

    RUNTIME_DB_BACKEND=postgres python tools/agent_runner/migrate_sqlite_to_pg.py \
        --sqlite /runtime/.runtime/ai-dev-factory.sqlite \
        --project ai-dev-factory

If --project is omitted, PROJECT_NAME (then RUNTIME_DB_NAME) is used.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import runtime_db_pg as pg  # noqa: E402

_TICKET_FIELDS = [
    "issue_number", "branch", "state", "run_dir", "worktree_path",
    "daemon_archived", "pr_number", "pr_state", "last_transition", "last_error",
]


def _rows(conn: sqlite3.Connection, table: str) -> list[dict]:
    try:
        cur = conn.execute(f"SELECT * FROM {table}")
    except sqlite3.OperationalError:
        return []
    cols = [c[0] for c in cur.description]
    return [dict(zip(cols, r)) for r in cur.fetchall()]


def migrate(sqlite_path: Path, project_id: str | None) -> dict[str, int]:
    handle = pg.get_handle(project_id)
    pg.init_runtime_db(handle)

    src = sqlite3.connect(str(sqlite_path))
    counts = {"issue_intake": 0, "ticket_runtime": 0, "workers": 0, "runtime_events": 0}

    for row in _rows(src, "issue_intake"):
        pg.record_issue_intake(
            handle,
            issue_number=int(row["issue_number"]),
            ticket_id=row["ticket_id"],
            branch=row.get("branch"),
            status=row.get("status") or "ingested",
        )
        counts["issue_intake"] += 1

    for row in _rows(src, "ticket_runtime"):
        fields = {k: row.get(k) for k in _TICKET_FIELDS if row.get(k) is not None}
        pg.upsert_ticket_runtime(handle, row["ticket_id"], **fields)
        counts["ticket_runtime"] += 1

    for row in _rows(src, "workers"):
        pg.upsert_worker(
            handle,
            ticket_id=row["ticket_id"],
            pid=int(row.get("pid") or 0),
            branch=row.get("branch"),
            worktree_path=row.get("worktree_path") or "",
        )
        counts["workers"] += 1

    # Append-only: only migrate when the target is empty (avoid duplicates).
    if not pg.list_runtime_events(handle, limit=1):
        for row in _rows(src, "runtime_events"):
            pg.append_runtime_event(
                handle,
                ticket_id=row.get("ticket_id"),
                event_type=row.get("event_type") or "migrated",
                message=row.get("message") or "",
            )
            counts["runtime_events"] += 1

    src.close()
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sqlite", required=True, type=Path, help="legacy SQLite file")
    parser.add_argument("--project", default=None, help="project id (target adf_<project>)")
    args = parser.parse_args()

    if not args.sqlite.exists():
        print(f"error: SQLite file not found: {args.sqlite}", file=sys.stderr)
        return 1

    handle = pg.get_handle(args.project)
    print(f"migrating {args.sqlite} → Postgres database {handle.dbname}")
    counts = migrate(args.sqlite, args.project)
    for table, n in counts.items():
        print(f"  {table}: {n} rows")
    print("done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
