#!/usr/bin/env python3
"""SQLite runtime state store for ai-dev-factory daemon.

Single-file module — stdlib only (sqlite3, subprocess, json, datetime).
DB path: RUNTIME_ROOT/.runtime/... when AI_DEV_FACTORY_RUNTIME_ROOT is set;
otherwise resolved via git rev-parse --git-common-dir so all worktrees share one DB.
"""

from __future__ import annotations

import datetime
import fcntl
import json
import os
import sqlite3
import subprocess
from pathlib import Path

_DB_FILENAME = ".runtime/ai-dev-factory.sqlite"

_SCHEMA = """
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
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id     TEXT,
    event_type    TEXT NOT NULL,
    message       TEXT NOT NULL,
    metadata_json TEXT,
    created_at    TEXT NOT NULL
);
"""


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def get_db_path() -> Path | None:
    """Resolve the SQLite DB path.

    When AI_DEV_FACTORY_RUNTIME_ROOT is set (Docker/runtime), returns RUNTIME_ROOT/.runtime/...
    Dev fallback: use git rev-parse --git-common-dir so all worktrees share one DB even when
    this module is loaded from a worktree copy (where __file__-based paths point to the worktree).
    """
    runtime_root = os.environ.get("AI_DEV_FACTORY_RUNTIME_ROOT")
    if runtime_root:
        return Path(runtime_root) / _DB_FILENAME
    # Dev fallback: git common-dir points to the main repo's .git regardless of which
    # worktree this module was loaded from, ensuring a single shared DB in dev mode.
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            capture_output=True,
            text=True,
            check=False,
            cwd=str(Path(__file__).parent),
        )
        if result.returncode == 0:
            common_dir = result.stdout.strip()
            common_path = Path(common_dir)
            if not common_path.is_absolute():
                common_path = (Path(__file__).parent / common_path).resolve()
            return common_path.parent / _DB_FILENAME
    except FileNotFoundError:
        pass
    # Last resort: module-location path (valid only when invoked from the main clone).
    return Path(__file__).resolve().parent.parent.parent / _DB_FILENAME


def init_runtime_db(db_path: Path) -> None:
    """Create the DB file and tables if they don't exist. Safe to call multiple times."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.executescript(_SCHEMA)


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=5000")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def check_and_recover_db(db_path: Path) -> bool:
    """Integrity-check the DB and recover if corrupt.

    Entire sequence runs inside LOCK_EX on <db_path>.recovery.lock so
    concurrent callers are serialized — only one process performs recovery.
    Returns True when the DB is healthy or was recovered successfully.
    Returns False only when quarantine itself fails.
    """
    lock_path = Path(str(db_path) + ".recovery.lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with open(lock_path, "w") as lock_fh:
        fcntl.flock(lock_fh, fcntl.LOCK_EX)
        try:
            return _check_and_recover_locked(db_path)
        finally:
            fcntl.flock(lock_fh, fcntl.LOCK_UN)


def _check_and_recover_locked(db_path: Path) -> bool:
    """Internal: runs inside LOCK_EX. Check integrity → quarantine → recover/recreate."""
    if not db_path.exists():
        return True

    # integrity_check
    try:
        with sqlite3.connect(str(db_path), timeout=5) as conn:
            row = conn.execute("PRAGMA integrity_check").fetchone()
            if row and row[0] == "ok":
                return True
    except Exception as exc:
        print(f"[runtime_db] integrity_check error: {exc}", flush=True)

    # quarantine corrupt DB
    ts = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    quarantine = db_path.with_name(db_path.name + f".corrupt.{ts}")
    print(f"[runtime_db] DB corrupt — entering degraded mode", flush=True)
    print(f"[runtime_db] quarantining {db_path.name} -> {quarantine.name}", flush=True)
    try:
        db_path.rename(quarantine)
    except OSError as exc:
        print(f"[runtime_db] quarantine rename failed: {exc}", flush=True)
        return False

    # attempt recovery via sqlite3 CLI .recover (best-effort, not always available)
    try:
        result = subprocess.run(
            ["sqlite3", str(quarantine), ".recover"],
            capture_output=True, text=True, check=False, timeout=30,
        )
        if result.returncode == 0 and result.stdout.strip():
            with sqlite3.connect(str(db_path), timeout=5) as conn:
                conn.executescript(result.stdout)
            print(f"[runtime_db] recovery succeeded from {quarantine.name}", flush=True)
            return True
    except Exception as exc:
        print(f"[runtime_db] .recover attempt failed: {exc}", flush=True)

    # recreate empty DB
    print(f"[runtime_db] recovery impossible — creating empty DB", flush=True)
    try:
        init_runtime_db(db_path)
        return True
    except Exception as exc:
        print(f"[runtime_db] empty DB creation failed: {exc}", flush=True)
        return False


# ── issue_intake ──────────────────────────────────────────────────────────────

def record_issue_intake(
    db_path: Path,
    issue_number: int,
    ticket_id: str,
    branch: str | None = None,
    status: str = "ingested",
) -> None:
    """Upsert one row in issue_intake. On conflict, updates ticket_id/branch/status."""
    now = _now_iso()
    with _connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO issue_intake
                (issue_number, ticket_id, branch, status, ingested_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(issue_number) DO UPDATE SET
                ticket_id  = excluded.ticket_id,
                branch     = excluded.branch,
                status     = excluded.status,
                updated_at = excluded.updated_at
            """,
            (issue_number, ticket_id, branch, status, now, now),
        )


def get_issue_intake(db_path: Path, issue_number: int) -> dict | None:
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM issue_intake WHERE issue_number = ?", (issue_number,)
        ).fetchone()
    return dict(row) if row else None


def list_issue_intake(db_path: Path) -> list[dict]:
    with _connect(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM issue_intake ORDER BY issue_number"
        ).fetchall()
    return [dict(r) for r in rows]


# ── ticket_runtime ────────────────────────────────────────────────────────────

def upsert_ticket_runtime(db_path: Path, ticket_id: str, **fields) -> None:
    """Insert or update a ticket_runtime row. Pass only the fields you want to set."""
    now = _now_iso()
    with _connect(db_path) as conn:
        existing = conn.execute(
            "SELECT ticket_id FROM ticket_runtime WHERE ticket_id = ?", (ticket_id,)
        ).fetchone()
        if existing:
            if fields:
                set_clause = ", ".join(f"{k}=?" for k in fields)
                conn.execute(
                    f"UPDATE ticket_runtime SET {set_clause}, updated_at=? WHERE ticket_id=?",
                    list(fields.values()) + [now, ticket_id],
                )
            else:
                conn.execute(
                    "UPDATE ticket_runtime SET updated_at=? WHERE ticket_id=?",
                    (now, ticket_id),
                )
        else:
            fields.setdefault("state", "INIT")
            cols = ["ticket_id", "updated_at"] + list(fields.keys())
            placeholders = ", ".join("?" * len(cols))
            conn.execute(
                f"INSERT INTO ticket_runtime ({', '.join(cols)}) VALUES ({placeholders})",
                [ticket_id, now] + list(fields.values()),
            )


def get_ticket_runtime(db_path: Path, ticket_id: str) -> dict | None:
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM ticket_runtime WHERE ticket_id = ?", (ticket_id,)
        ).fetchone()
    return dict(row) if row else None


def list_ticket_runtime(db_path: Path) -> list[dict]:
    with _connect(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM ticket_runtime ORDER BY ticket_id"
        ).fetchall()
    return [dict(r) for r in rows]


# ── workers ───────────────────────────────────────────────────────────────────

def upsert_worker(
    db_path: Path,
    ticket_id: str,
    pid: int,
    branch: str | None,
    worktree_path: str,
) -> None:
    now = _now_iso()
    with _connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO workers
                (ticket_id, pid, branch, worktree_path, status, started_at, updated_at)
            VALUES (?, ?, ?, ?, 'running', ?, ?)
            ON CONFLICT(ticket_id) DO UPDATE SET
                pid           = excluded.pid,
                branch        = excluded.branch,
                worktree_path = excluded.worktree_path,
                status        = 'running',
                started_at    = excluded.started_at,
                updated_at    = excluded.updated_at
            """,
            (ticket_id, pid, branch, worktree_path, now, now),
        )


def remove_worker(db_path: Path, ticket_id: str) -> None:
    with _connect(db_path) as conn:
        conn.execute("DELETE FROM workers WHERE ticket_id = ?", (ticket_id,))


def list_workers(db_path: Path) -> list[dict]:
    with _connect(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM workers ORDER BY ticket_id"
        ).fetchall()
    return [dict(r) for r in rows]


# ── runtime_events ────────────────────────────────────────────────────────────

def append_runtime_event(
    db_path: Path,
    ticket_id: str | None,
    event_type: str,
    message: str,
    metadata: dict | None = None,
) -> None:
    now = _now_iso()
    meta_json = json.dumps(metadata) if metadata else None
    with _connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO runtime_events (ticket_id, event_type, message, metadata_json, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (ticket_id, event_type, message, meta_json, now),
        )


def list_runtime_events(
    db_path: Path,
    ticket_id: str | None = None,
    limit: int = 100,
) -> list[dict]:
    with _connect(db_path) as conn:
        if ticket_id:
            rows = conn.execute(
                "SELECT * FROM runtime_events WHERE ticket_id = ? ORDER BY id DESC LIMIT ?",
                (ticket_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM runtime_events ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
    return [dict(r) for r in rows]
