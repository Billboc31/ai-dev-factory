#!/usr/bin/env python3
"""Postgres backend for the ai-dev-factory runtime store.

Mirrors the public API of ``runtime_db`` (the SQLite store) but talks to a
networked Postgres server. Selected when ``RUNTIME_DB_BACKEND=postgres``.

Why Postgres: the SQLite file lives under the runtime root, which on macOS is a
Docker bind-mount shared between the container (control API) and the host
(supervisor/daemon). SQLite's file locking is unreliable across that boundary →
recurring corruption. A networked server removes the shared-file problem and
gives one database per project.

Connection comes from the environment:
    RUNTIME_DB_HOST       (default 127.0.0.1; the container overrides to "db")
    RUNTIME_DB_PORT       (default 5432)
    RUNTIME_DB_USER       (default adf)
    RUNTIME_DB_PASSWORD   (default adf)
    RUNTIME_DB_NAME       (maintenance DB, default adf)

Each project gets its own database ``adf_<project_id>``; ``get_handle`` resolves
it. Tables are created lazily by ``init_runtime_db``.
"""

from __future__ import annotations

import datetime
import json
import os
import re

# psycopg is imported lazily inside the connection helpers so that the pure
# helpers (db_name_for, PgHandle, get_handle) remain importable/testable even
# when the optional dependency is not installed.

_DDL = """
CREATE TABLE IF NOT EXISTS issue_intake (
    issue_number INTEGER PRIMARY KEY,
    ticket_id    TEXT NOT NULL,
    branch       TEXT,
    status       TEXT NOT NULL DEFAULT 'ingested',
    ingested_at  TEXT NOT NULL,
    updated_at   TEXT NOT NULL,
    last_error   TEXT
);

CREATE TABLE IF NOT EXISTS ticket_runtime (
    ticket_id       TEXT PRIMARY KEY,
    issue_number    INTEGER,
    branch          TEXT,
    state           TEXT NOT NULL DEFAULT 'INIT',
    run_dir         TEXT,
    worktree_path   TEXT,
    daemon_archived INTEGER DEFAULT 0,
    pr_number       INTEGER,
    pr_state        TEXT,
    last_transition TEXT,
    last_error      TEXT,
    updated_at      TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS workers (
    ticket_id     TEXT PRIMARY KEY,
    pid           INTEGER,
    branch        TEXT,
    worktree_path TEXT,
    status        TEXT NOT NULL DEFAULT 'running',
    started_at    TEXT,
    heartbeat_at  TEXT,
    updated_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS runtime_events (
    id            BIGSERIAL PRIMARY KEY,
    ticket_id     TEXT,
    event_type    TEXT NOT NULL,
    message       TEXT NOT NULL,
    metadata_json TEXT,
    created_at    TEXT NOT NULL
);
"""

_DEFAULT_DBNAME = "adf"


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _maintenance_dbname() -> str:
    return os.environ.get("RUNTIME_DB_NAME", _DEFAULT_DBNAME)


def db_name_for(project_id: str | None) -> str:
    """Return the per-project database name, e.g. ``adf_ai_dev_factory``.

    When *project_id* is omitted, falls back to the current project (PROJECT_NAME
    env) so writers (daemon/run_ticket) and readers (board) target the same DB
    without threading a project_id everywhere. As a last resort uses the
    maintenance database (RUNTIME_DB_NAME).
    """
    pid = project_id or os.environ.get("PROJECT_NAME")
    if not pid:
        return _maintenance_dbname()
    safe = re.sub(r"[^a-zA-Z0-9_]", "_", pid).lower().strip("_")
    return f"adf_{safe}" if safe else _maintenance_dbname()


class PgHandle:
    """Opaque DB handle for the Postgres backend.

    Quacks like the ``Path`` returned by the SQLite backend's ``get_db_path`` so
    existing callers (e.g. ``if handle is None or not handle.exists()``) keep
    working unchanged.
    """

    def __init__(self, dbname: str) -> None:
        self.dbname = dbname

    def exists(self) -> bool:
        # Server-backed store: presence is established lazily via init_runtime_db.
        return True

    def __str__(self) -> str:
        return f"postgres:{self.dbname}"

    def __repr__(self) -> str:
        return f"PgHandle({self.dbname!r})"


def get_handle(project_id: str | None = None) -> PgHandle:
    return PgHandle(db_name_for(project_id))


def _conn_kwargs(dbname: str) -> dict:
    return {
        "host": os.environ.get("RUNTIME_DB_HOST", "127.0.0.1"),
        "port": int(os.environ.get("RUNTIME_DB_PORT", "5432")),
        "user": os.environ.get("RUNTIME_DB_USER", "adf"),
        "password": os.environ.get("RUNTIME_DB_PASSWORD", "adf"),
        "dbname": dbname,
    }


def _connect(handle: PgHandle):
    import psycopg
    from psycopg.rows import dict_row

    conn = psycopg.connect(**_conn_kwargs(handle.dbname), autocommit=True)
    conn.row_factory = dict_row
    return conn


def ensure_database(dbname: str) -> None:
    """Create the project database if it does not exist (idempotent)."""
    import psycopg

    maint = _maintenance_dbname()
    kwargs = _conn_kwargs(maint)
    with psycopg.connect(**kwargs, autocommit=True) as conn:
        exists = conn.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s", (dbname,)
        ).fetchone()
        if not exists:
            # Identifier can't be parameterised; dbname is sanitised by db_name_for.
            conn.execute(f'CREATE DATABASE "{dbname}"')


def init_runtime_db(handle: PgHandle) -> None:
    """Ensure the database and tables exist. Safe to call repeatedly."""
    if handle.dbname != _maintenance_dbname():
        ensure_database(handle.dbname)
    with _connect(handle) as conn:
        conn.execute(_DDL)


def check_and_recover_db(handle: PgHandle) -> bool:
    """No-op for Postgres (the server guarantees durability). Always healthy."""
    return True


# ── issue_intake ──────────────────────────────────────────────────────────────

def record_issue_intake(
    handle: PgHandle,
    issue_number: int,
    ticket_id: str,
    branch: str | None = None,
    status: str = "ingested",
) -> None:
    now = _now_iso()
    with _connect(handle) as conn:
        conn.execute(
            """
            INSERT INTO issue_intake
                (issue_number, ticket_id, branch, status, ingested_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT (issue_number) DO UPDATE SET
                ticket_id  = EXCLUDED.ticket_id,
                branch     = EXCLUDED.branch,
                status     = EXCLUDED.status,
                updated_at = EXCLUDED.updated_at
            """,
            (issue_number, ticket_id, branch, status, now, now),
        )


def get_issue_intake(handle: PgHandle, issue_number: int) -> dict | None:
    with _connect(handle) as conn:
        row = conn.execute(
            "SELECT * FROM issue_intake WHERE issue_number = %s", (issue_number,)
        ).fetchone()
    return dict(row) if row else None


def list_issue_intake(handle: PgHandle) -> list[dict]:
    with _connect(handle) as conn:
        rows = conn.execute("SELECT * FROM issue_intake ORDER BY issue_number").fetchall()
    return [dict(r) for r in rows]


# ── ticket_runtime ────────────────────────────────────────────────────────────

def upsert_ticket_runtime(handle: PgHandle, ticket_id: str, **fields) -> None:
    now = _now_iso()
    with _connect(handle) as conn:
        existing = conn.execute(
            "SELECT ticket_id FROM ticket_runtime WHERE ticket_id = %s", (ticket_id,)
        ).fetchone()
        if existing:
            if fields:
                set_clause = ", ".join(f"{k}=%s" for k in fields)
                conn.execute(
                    f"UPDATE ticket_runtime SET {set_clause}, updated_at=%s WHERE ticket_id=%s",
                    list(fields.values()) + [now, ticket_id],
                )
            else:
                conn.execute(
                    "UPDATE ticket_runtime SET updated_at=%s WHERE ticket_id=%s",
                    (now, ticket_id),
                )
        else:
            fields.setdefault("state", "INIT")
            cols = ["ticket_id", "updated_at"] + list(fields.keys())
            placeholders = ", ".join(["%s"] * len(cols))
            conn.execute(
                f"INSERT INTO ticket_runtime ({', '.join(cols)}) VALUES ({placeholders})",
                [ticket_id, now] + list(fields.values()),
            )


def get_ticket_runtime(handle: PgHandle, ticket_id: str) -> dict | None:
    with _connect(handle) as conn:
        row = conn.execute(
            "SELECT * FROM ticket_runtime WHERE ticket_id = %s", (ticket_id,)
        ).fetchone()
    return dict(row) if row else None


def list_ticket_runtime(handle: PgHandle) -> list[dict]:
    with _connect(handle) as conn:
        rows = conn.execute("SELECT * FROM ticket_runtime ORDER BY ticket_id").fetchall()
    return [dict(r) for r in rows]


# ── workers ───────────────────────────────────────────────────────────────────

def upsert_worker(
    handle: PgHandle,
    ticket_id: str,
    pid: int,
    branch: str | None,
    worktree_path: str,
) -> None:
    now = _now_iso()
    with _connect(handle) as conn:
        conn.execute(
            """
            INSERT INTO workers
                (ticket_id, pid, branch, worktree_path, status, started_at, updated_at)
            VALUES (%s, %s, %s, %s, 'running', %s, %s)
            ON CONFLICT (ticket_id) DO UPDATE SET
                pid           = EXCLUDED.pid,
                branch        = EXCLUDED.branch,
                worktree_path = EXCLUDED.worktree_path,
                status        = 'running',
                started_at    = EXCLUDED.started_at,
                updated_at    = EXCLUDED.updated_at
            """,
            (ticket_id, pid, branch, worktree_path, now, now),
        )


def remove_worker(handle: PgHandle, ticket_id: str) -> None:
    with _connect(handle) as conn:
        conn.execute("DELETE FROM workers WHERE ticket_id = %s", (ticket_id,))


def list_workers(handle: PgHandle) -> list[dict]:
    with _connect(handle) as conn:
        rows = conn.execute("SELECT * FROM workers ORDER BY ticket_id").fetchall()
    return [dict(r) for r in rows]


# ── runtime_events ──────────────────────────────────────────────────────────────

def append_runtime_event(
    handle: PgHandle,
    ticket_id: str | None,
    event_type: str,
    message: str,
    metadata: dict | None = None,
) -> None:
    now = _now_iso()
    meta_json = json.dumps(metadata) if metadata else None
    with _connect(handle) as conn:
        conn.execute(
            """
            INSERT INTO runtime_events (ticket_id, event_type, message, metadata_json, created_at)
            VALUES (%s, %s, %s, %s, %s)
            """,
            (ticket_id, event_type, message, meta_json, now),
        )


def list_runtime_events(
    handle: PgHandle,
    ticket_id: str | None = None,
    limit: int = 100,
) -> list[dict]:
    with _connect(handle) as conn:
        if ticket_id:
            rows = conn.execute(
                "SELECT * FROM runtime_events WHERE ticket_id = %s ORDER BY id DESC LIMIT %s",
                (ticket_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM runtime_events ORDER BY id DESC LIMIT %s", (limit,)
            ).fetchall()
    return [dict(r) for r in rows]
