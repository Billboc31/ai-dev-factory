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

CREATE TABLE IF NOT EXISTS ticket_intelligence (
    ticket_id                           TEXT PRIMARY KEY,
    analysis_status                     TEXT NOT NULL DEFAULT 'not_started',
    difficulty_score                    INTEGER,
    difficulty_label                    TEXT,
    risk_score                          INTEGER,
    risk_label                          TEXT,
    complexity_factors                  TEXT,
    computed_signals_json               TEXT,
    recommended_model                   TEXT,
    recommended_model_reason            TEXT,
    estimated_input_tokens              INTEGER,
    estimated_output_tokens             INTEGER,
    estimated_cost_min                  REAL,
    estimated_cost_max                  REAL,
    cost_currency                       TEXT,
    cost_estimate_status                TEXT,
    queue_rank                          INTEGER,
    queue_reason                        TEXT,
    dependency_hints                    TEXT,
    parallel_safe_candidate             INTEGER,
    requires_human_plan_review          INTEGER,
    human_plan_review_reason            TEXT,
    requires_human_code_review          INTEGER,
    human_code_review_reason            TEXT,
    autonomous_execution_recommendation TEXT,
    analysis_summary                    TEXT,
    started_at                          TEXT,
    completed_at                        TEXT,
    failed_at                           TEXT,
    failure_origin                      TEXT,
    stage                               TEXT,
    created_at                          TEXT NOT NULL,
    updated_at                          TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ticket_readiness (
    ticket_id                TEXT PRIMARY KEY,
    readiness_status         TEXT NOT NULL DEFAULT 'not_started',
    ready_candidate          INTEGER NOT NULL DEFAULT 0,
    blocking_reasons_json    TEXT,
    warnings_json            TEXT,
    dependency_check_status  TEXT,
    approval_check_status    TEXT,
    context_freshness_status TEXT,
    human_approval_required  INTEGER,
    human_approval_present   INTEGER,
    main_sha_when_evaluated  TEXT,
    evaluated_at             TEXT,
    created_at               TEXT NOT NULL,
    updated_at               TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ticket_approvals (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id        TEXT NOT NULL,
    approval_type    TEXT NOT NULL,
    approval_status  TEXT NOT NULL,
    approved_by      TEXT,
    approval_comment TEXT,
    approved_at      TEXT,
    created_at       TEXT NOT NULL,
    updated_at       TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_ticket_approvals_ticket
    ON ticket_approvals(ticket_id, approval_type, id);

CREATE TABLE IF NOT EXISTS project_execution_rules (
    project_id         TEXT NOT NULL,
    rule_key           TEXT NOT NULL,
    enabled            INTEGER NOT NULL,
    configuration_json TEXT NOT NULL DEFAULT '{}',
    created_at         TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at         TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (project_id, rule_key)
);

CREATE TABLE IF NOT EXISTS ticket_rule_evaluation (
    ticket_id          TEXT NOT NULL PRIMARY KEY,
    project_id         TEXT NOT NULL,
    eligibility_status TEXT NOT NULL,
    failed_rules_json  TEXT NOT NULL DEFAULT '[]',
    passed_rules_json  TEXT NOT NULL DEFAULT '[]',
    warnings_json      TEXT NOT NULL DEFAULT '[]',
    evaluated_at       TEXT NOT NULL,
    created_at         TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at         TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ticket_diagnostics (
    ticket_id                TEXT PRIMARY KEY,
    project_id               TEXT,
    diagnostic_status        TEXT NOT NULL DEFAULT 'completed',
    is_stuck                 INTEGER NOT NULL DEFAULT 0,
    severity                 TEXT NOT NULL DEFAULT 'info',
    summary                  TEXT,
    current_state            TEXT,
    last_known_step          TEXT,
    last_error               TEXT,
    checks_json              TEXT NOT NULL DEFAULT '[]',
    recommended_actions_json TEXT NOT NULL DEFAULT '[]',
    generated_at             TEXT NOT NULL,
    created_at               TEXT NOT NULL,
    updated_at               TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ticket_operation_audit (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id     TEXT NOT NULL,
    project_id    TEXT,
    operation_key TEXT NOT NULL,
    status        TEXT NOT NULL,
    reason        TEXT,
    requested_by  TEXT,
    details_json  TEXT,
    created_at    TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_ticket_operation_audit_ticket
    ON ticket_operation_audit(ticket_id, id);

CREATE TABLE IF NOT EXISTS runtime_settings (
    key              TEXT PRIMARY KEY,
    value            TEXT NOT NULL,
    value_type       TEXT NOT NULL,
    scope            TEXT NOT NULL DEFAULT 'global',
    description      TEXT,
    is_sensitive     INTEGER NOT NULL DEFAULT 0,
    requires_restart INTEGER NOT NULL DEFAULT 0,
    updated_at       TEXT NOT NULL,
    updated_by       TEXT
);

CREATE TABLE IF NOT EXISTS backlog_batches (
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
);

CREATE TABLE IF NOT EXISTS backlog_batch_tickets (
    batch_id   TEXT NOT NULL,
    ticket_id  TEXT NOT NULL,
    added_at   TEXT NOT NULL,
    PRIMARY KEY (batch_id, ticket_id),
    UNIQUE (ticket_id)
);

CREATE TABLE IF NOT EXISTS ticket_dependency_analysis (
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
);
"""


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def get_db_path(project_id: str | None = None) -> Path | None:
    """Resolve the SQLite DB path.

    When ``project_id`` is provided and a runtime root is configured, the DB is
    scoped to ``{root}/{project_id}/.runtime/...`` so each project owns its own
    file. RUNTIME_BASE_ROOT takes precedence when set; otherwise we honor
    AI_DEV_FACTORY_RUNTIME_ROOT as the parent directory (multi-project
    deployments register each project under its own subdirectory there).

    Without ``project_id`` the legacy resolution is preserved so single-project
    setups and existing callers keep working unchanged.
    """
    runtime_root = os.environ.get("AI_DEV_FACTORY_RUNTIME_ROOT")
    runtime_base_root = os.environ.get("RUNTIME_BASE_ROOT")
    if project_id:
        if runtime_base_root:
            return Path(runtime_base_root).expanduser() / project_id / _DB_FILENAME
        if runtime_root:
            return Path(runtime_root) / project_id / _DB_FILENAME
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


def resolve_db_path_for_project(
    project_id: str | None,
    project_runtime_root: Path | None = None,
) -> Path | None:
    """Resolve the per-project DB path, mirroring ``runtime_resolver`` precedence.

    Precedence:
      1. Explicit ``project_runtime_root`` (persisted at bootstrap) — DB is
         ``{project_runtime_root}/.runtime/ai-dev-factory.sqlite``.
      2. Env-derived per-project path via :func:`get_db_path` with ``project_id``.
      3. Legacy global path via :func:`get_db_path` (no project scoping).
    """
    if project_runtime_root is not None:
        return Path(project_runtime_root) / _DB_FILENAME
    if project_id:
        return get_db_path(project_id=project_id)
    return get_db_path()


_TICKET_INTELLIGENCE_LIFECYCLE_COLUMNS = (
    ("started_at", "TEXT"),
    ("completed_at", "TEXT"),
    ("failed_at", "TEXT"),
    ("failure_origin", "TEXT"),
    ("stage", "TEXT"),
)


def _ensure_ticket_intelligence_lifecycle_columns(conn: sqlite3.Connection) -> None:
    """Idempotent migration: add lifecycle columns to ticket_intelligence if missing.

    Pre-existing databases created before T208 lack started_at/completed_at/
    failed_at/failure_origin. Introspect PRAGMA table_info and ALTER only what's
    missing so re-running init_runtime_db never duplicates a column.
    """
    existing = {row[1] for row in conn.execute("PRAGMA table_info('ticket_intelligence')")}
    for name, sql_type in _TICKET_INTELLIGENCE_LIFECYCLE_COLUMNS:
        if name not in existing:
            conn.execute(f"ALTER TABLE ticket_intelligence ADD COLUMN {name} {sql_type}")


_BACKLOG_BATCHES_COLUMNS = (
    ("status", "TEXT NOT NULL DEFAULT 'collecting'"),
    ("created_at", "TEXT"),
    ("frozen_at", "TEXT"),
    ("last_activity_at", "TEXT"),
    ("completed_at", "TEXT"),
    ("freeze_blocked", "INTEGER NOT NULL DEFAULT 0"),
    ("freeze_blocked_reason", "TEXT"),
    ("dependency_analysis_attempts", "INTEGER NOT NULL DEFAULT 0"),
    ("last_dependency_analysis_error", "TEXT"),
    ("next_dependency_analysis_retry_at", "TEXT"),
    ("notes", "TEXT"),
)


def _ensure_backlog_batches_columns(conn: sqlite3.Connection) -> None:
    """Idempotent additive migration for backlog_batches new columns (T218).

    Pre-existing databases created before T218 don't have this table at all, so
    the CREATE TABLE IF NOT EXISTS in ``_SCHEMA`` covers them. For very old DBs
    that may have a partial version of the table, this helper introspects
    ``PRAGMA table_info`` and adds any missing columns.
    """
    rows = list(conn.execute("PRAGMA table_info('backlog_batches')"))
    if not rows:
        return
    existing = {row[1] for row in rows}
    for name, sql_type in _BACKLOG_BATCHES_COLUMNS:
        if name not in existing:
            conn.execute(f"ALTER TABLE backlog_batches ADD COLUMN {name} {sql_type}")


def _ensure_runtime_settings_table(conn: sqlite3.Connection) -> None:
    """Idempotent migration: create runtime_settings if missing.

    Pre-existing databases created before T215 lack this table. The CREATE
    statement also lives in ``_SCHEMA`` so fresh DBs are covered there; this
    helper exists so callers that bypass ``executescript`` (or run after a
    targeted PRAGMA inspection) still get the table.
    """
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runtime_settings (
            key              TEXT PRIMARY KEY,
            value            TEXT NOT NULL,
            value_type       TEXT NOT NULL,
            scope            TEXT NOT NULL DEFAULT 'global',
            description      TEXT,
            is_sensitive     INTEGER NOT NULL DEFAULT 0,
            requires_restart INTEGER NOT NULL DEFAULT 0,
            updated_at       TEXT NOT NULL,
            updated_by       TEXT
        )
        """
    )


def init_runtime_db(db_path: Path) -> None:
    """Create the DB file and tables if they don't exist. Safe to call multiple times."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA busy_timeout=5000")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.executescript(_SCHEMA)
        _ensure_ticket_intelligence_lifecycle_columns(conn)
        _ensure_runtime_settings_table(conn)
        _ensure_backlog_batches_columns(conn)


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


# ── ticket_intelligence ───────────────────────────────────────────────────────

def upsert_ticket_intelligence(db_path: Path, ticket_id: str, **fields) -> None:
    """Insert or update a ticket_intelligence row. Sets created_at only on first insert."""
    now = _now_iso()
    with _connect(db_path) as conn:
        existing = conn.execute(
            "SELECT ticket_id FROM ticket_intelligence WHERE ticket_id = ?", (ticket_id,)
        ).fetchone()
        if existing:
            if fields:
                set_clause = ", ".join(f"{k}=?" for k in fields)
                conn.execute(
                    f"UPDATE ticket_intelligence SET {set_clause}, updated_at=? WHERE ticket_id=?",
                    list(fields.values()) + [now, ticket_id],
                )
            else:
                conn.execute(
                    "UPDATE ticket_intelligence SET updated_at=? WHERE ticket_id=?",
                    (now, ticket_id),
                )
        else:
            fields.setdefault("analysis_status", "not_started")
            cols = ["ticket_id", "created_at", "updated_at"] + list(fields.keys())
            placeholders = ", ".join("?" * len(cols))
            conn.execute(
                f"INSERT INTO ticket_intelligence ({', '.join(cols)}) VALUES ({placeholders})",
                [ticket_id, now, now] + list(fields.values()),
            )


def get_ticket_intelligence(db_path: Path, ticket_id: str) -> dict | None:
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM ticket_intelligence WHERE ticket_id = ?", (ticket_id,)
        ).fetchone()
    return dict(row) if row else None


# ── ticket_readiness ──────────────────────────────────────────────────────────

_READINESS_LIST_FIELDS = ("blocking_reasons_json", "warnings_json")


def _encode_readiness_lists(fields: dict) -> dict:
    """Serialise any list-typed list-field arguments to JSON strings in place."""
    out = dict(fields)
    for key in _READINESS_LIST_FIELDS:
        val = out.get(key)
        if isinstance(val, list):
            out[key] = json.dumps(val)
    return out


def _decode_readiness_lists(row: dict) -> dict:
    """Decode JSON-list columns back into Python lists, defaulting to []."""
    out = dict(row)
    for key in _READINESS_LIST_FIELDS:
        val = out.get(key)
        if val is None or val == "":
            out[key] = []
            continue
        try:
            parsed = json.loads(val)
            out[key] = parsed if isinstance(parsed, list) else []
        except (json.JSONDecodeError, TypeError):
            out[key] = []
    return out


def upsert_ticket_readiness(db_path: Path, ticket_id: str, **fields) -> None:
    """Insert or update a ticket_readiness row. Sets created_at only on first insert."""
    fields = _encode_readiness_lists(fields)
    now = _now_iso()
    with _connect(db_path) as conn:
        existing = conn.execute(
            "SELECT ticket_id FROM ticket_readiness WHERE ticket_id = ?", (ticket_id,)
        ).fetchone()
        if existing:
            if fields:
                set_clause = ", ".join(f"{k}=?" for k in fields)
                conn.execute(
                    f"UPDATE ticket_readiness SET {set_clause}, updated_at=? WHERE ticket_id=?",
                    list(fields.values()) + [now, ticket_id],
                )
            else:
                conn.execute(
                    "UPDATE ticket_readiness SET updated_at=? WHERE ticket_id=?",
                    (now, ticket_id),
                )
        else:
            fields.setdefault("readiness_status", "not_started")
            cols = ["ticket_id", "created_at", "updated_at"] + list(fields.keys())
            placeholders = ", ".join("?" * len(cols))
            conn.execute(
                f"INSERT INTO ticket_readiness ({', '.join(cols)}) VALUES ({placeholders})",
                [ticket_id, now, now] + list(fields.values()),
            )


def get_ticket_readiness(db_path: Path, ticket_id: str) -> dict | None:
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM ticket_readiness WHERE ticket_id = ?", (ticket_id,)
        ).fetchone()
    if row is None:
        return None
    return _decode_readiness_lists(dict(row))


# ── ticket_approvals ──────────────────────────────────────────────────────────

_APPROVAL_FINAL_STATUSES = frozenset({"approved", "rejected"})


def insert_ticket_approval(
    db_path: Path,
    ticket_id: str,
    approval_type: str,
    approval_status: str,
    approved_by: str | None = None,
    approval_comment: str | None = None,
) -> int:
    """Append a row to ticket_approvals. Returns the new row id.

    ``approved_at`` is set to now for final decisions (approved/rejected);
    NULL while ``pending``.
    """
    now = _now_iso()
    approved_at = now if approval_status in _APPROVAL_FINAL_STATUSES else None
    with _connect(db_path) as conn:
        cur = conn.execute(
            """
            INSERT INTO ticket_approvals
                (ticket_id, approval_type, approval_status,
                 approved_by, approval_comment, approved_at,
                 created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ticket_id, approval_type, approval_status,
                approved_by, approval_comment, approved_at,
                now, now,
            ),
        )
        return int(cur.lastrowid)


def list_ticket_approvals(db_path: Path, ticket_id: str) -> list[dict]:
    """Append-only history for ``ticket_id``, oldest first."""
    with _connect(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM ticket_approvals WHERE ticket_id = ? ORDER BY id ASC",
            (ticket_id,),
        ).fetchall()
    return [dict(r) for r in rows]


def get_latest_ticket_approval(
    db_path: Path, ticket_id: str, approval_type: str
) -> dict | None:
    """Return the latest approval row for ``(ticket_id, approval_type)``, or None."""
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM ticket_approvals "
            "WHERE ticket_id = ? AND approval_type = ? "
            "ORDER BY id DESC LIMIT 1",
            (ticket_id, approval_type),
        ).fetchone()
    return dict(row) if row else None


# ── project_execution_rules ───────────────────────────────────────────────────

def list_project_rules(db_path: Path, project_id: str) -> list[dict]:
    """Return all persisted rule rows for ``project_id`` (configuration decoded)."""
    with _connect(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM project_execution_rules WHERE project_id = ? ORDER BY rule_key",
            (project_id,),
        ).fetchall()
    out = []
    for row in rows:
        item = dict(row)
        item["enabled"] = bool(item.get("enabled"))
        raw = item.get("configuration_json")
        try:
            item["configuration"] = json.loads(raw) if raw else {}
        except (json.JSONDecodeError, TypeError):
            item["configuration"] = {}
        out.append(item)
    return out


def upsert_project_rule(
    db_path: Path,
    project_id: str,
    rule_key: str,
    enabled: bool,
    configuration: dict | None = None,
) -> None:
    """Upsert one rule row for ``project_id``."""
    now = _now_iso()
    cfg_json = json.dumps(configuration or {})
    with _connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO project_execution_rules
                (project_id, rule_key, enabled, configuration_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(project_id, rule_key) DO UPDATE SET
                enabled            = excluded.enabled,
                configuration_json = excluded.configuration_json,
                updated_at         = excluded.updated_at
            """,
            (project_id, rule_key, 1 if enabled else 0, cfg_json, now, now),
        )


def replace_project_rules(
    db_path: Path,
    project_id: str,
    rules: list[dict],
) -> None:
    """Atomically replace the project's rule set with ``rules``.

    Each rule dict must carry ``rule_key``, ``enabled``, and ``configuration``.
    """
    now = _now_iso()
    with _connect(db_path) as conn:
        conn.execute("BEGIN")
        try:
            conn.execute(
                "DELETE FROM project_execution_rules WHERE project_id = ?",
                (project_id,),
            )
            for rule in rules:
                cfg_json = json.dumps(rule.get("configuration") or {})
                enabled = 1 if rule.get("enabled") else 0
                conn.execute(
                    """
                    INSERT INTO project_execution_rules
                        (project_id, rule_key, enabled, configuration_json,
                         created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (project_id, rule["rule_key"], enabled, cfg_json, now, now),
                )
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise


# ── ticket_rule_evaluation ────────────────────────────────────────────────────

_RULE_EVAL_LIST_FIELDS = ("failed_rules_json", "passed_rules_json", "warnings_json")


def _decode_rule_eval_lists(row: dict) -> dict:
    out = dict(row)
    for key in _RULE_EVAL_LIST_FIELDS:
        val = out.get(key)
        if val is None or val == "":
            out[key] = []
            continue
        try:
            parsed = json.loads(val)
            out[key] = parsed if isinstance(parsed, list) else []
        except (json.JSONDecodeError, TypeError):
            out[key] = []
    return out


def get_ticket_rule_evaluation(db_path: Path, ticket_id: str) -> dict | None:
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM ticket_rule_evaluation WHERE ticket_id = ?",
            (ticket_id,),
        ).fetchone()
    if row is None:
        return None
    return _decode_rule_eval_lists(dict(row))


def upsert_ticket_rule_evaluation(
    db_path: Path,
    ticket_id: str,
    project_id: str,
    eligibility_status: str,
    passed_rules: list,
    failed_rules: list,
    warnings: list,
    evaluated_at: str,
) -> None:
    """Overwrite the evaluation row for ``ticket_id``."""
    now = _now_iso()
    passed_json = json.dumps(passed_rules or [])
    failed_json = json.dumps(failed_rules or [])
    warnings_json = json.dumps(warnings or [])
    with _connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO ticket_rule_evaluation
                (ticket_id, project_id, eligibility_status,
                 failed_rules_json, passed_rules_json, warnings_json,
                 evaluated_at, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(ticket_id) DO UPDATE SET
                project_id         = excluded.project_id,
                eligibility_status = excluded.eligibility_status,
                failed_rules_json  = excluded.failed_rules_json,
                passed_rules_json  = excluded.passed_rules_json,
                warnings_json      = excluded.warnings_json,
                evaluated_at       = excluded.evaluated_at,
                updated_at         = excluded.updated_at
            """,
            (
                ticket_id,
                project_id,
                eligibility_status,
                failed_json,
                passed_json,
                warnings_json,
                evaluated_at,
                now,
                now,
            ),
        )


# ── ticket_diagnostics ────────────────────────────────────────────────────────

_DIAGNOSTICS_LIST_FIELDS = ("checks_json", "recommended_actions_json")


def _encode_diagnostics_lists(fields: dict) -> dict:
    """Serialise any list-typed JSON-list-field arguments to JSON strings."""
    out = dict(fields)
    for key in _DIAGNOSTICS_LIST_FIELDS:
        val = out.get(key)
        if isinstance(val, list):
            out[key] = json.dumps(val)
    return out


def _decode_diagnostics_lists(row: dict) -> dict:
    out = dict(row)
    for key in _DIAGNOSTICS_LIST_FIELDS:
        val = out.get(key)
        if val is None or val == "":
            out[key] = []
            continue
        try:
            parsed = json.loads(val)
            out[key] = parsed if isinstance(parsed, list) else []
        except (json.JSONDecodeError, TypeError):
            out[key] = []
    return out


def upsert_ticket_diagnostics(db_path: Path, ticket_id: str, **fields) -> None:
    """Insert or update a ticket_diagnostics row. Sets created_at only on first insert."""
    fields = _encode_diagnostics_lists(fields)
    now = _now_iso()
    fields.setdefault("generated_at", now)
    with _connect(db_path) as conn:
        existing = conn.execute(
            "SELECT ticket_id FROM ticket_diagnostics WHERE ticket_id = ?", (ticket_id,)
        ).fetchone()
        if existing:
            if fields:
                set_clause = ", ".join(f"{k}=?" for k in fields)
                conn.execute(
                    f"UPDATE ticket_diagnostics SET {set_clause}, updated_at=? WHERE ticket_id=?",
                    list(fields.values()) + [now, ticket_id],
                )
            else:
                conn.execute(
                    "UPDATE ticket_diagnostics SET updated_at=? WHERE ticket_id=?",
                    (now, ticket_id),
                )
        else:
            cols = ["ticket_id", "created_at", "updated_at"] + list(fields.keys())
            placeholders = ", ".join("?" * len(cols))
            conn.execute(
                f"INSERT INTO ticket_diagnostics ({', '.join(cols)}) VALUES ({placeholders})",
                [ticket_id, now, now] + list(fields.values()),
            )


def get_ticket_diagnostics(db_path: Path, ticket_id: str) -> dict | None:
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM ticket_diagnostics WHERE ticket_id = ?", (ticket_id,)
        ).fetchone()
    if row is None:
        return None
    return _decode_diagnostics_lists(dict(row))


# ── ticket_operation_audit ────────────────────────────────────────────────────

def append_ticket_operation_audit(
    db_path: Path,
    ticket_id: str,
    project_id: str | None,
    operation_key: str,
    status: str,
    reason: str | None = None,
    requested_by: str | None = None,
    details: dict | None = None,
) -> int:
    """Append a row to ticket_operation_audit and return its id."""
    now = _now_iso()
    details_json = json.dumps(details) if details else None
    with _connect(db_path) as conn:
        cur = conn.execute(
            """
            INSERT INTO ticket_operation_audit
                (ticket_id, project_id, operation_key, status,
                 reason, requested_by, details_json, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                ticket_id, project_id, operation_key, status,
                reason, requested_by, details_json, now,
            ),
        )
        return int(cur.lastrowid)


def list_ticket_operation_audit(
    db_path: Path,
    ticket_id: str,
    limit: int = 50,
) -> list[dict]:
    """Return audit rows for ``ticket_id`` (most recent first)."""
    with _connect(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM ticket_operation_audit "
            "WHERE ticket_id = ? ORDER BY id DESC LIMIT ?",
            (ticket_id, limit),
        ).fetchall()
    out: list[dict] = []
    for row in rows:
        item = dict(row)
        raw = item.get("details_json")
        if raw:
            try:
                item["details"] = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                item["details"] = None
        else:
            item["details"] = None
        out.append(item)
    return out


# ── runtime_settings ──────────────────────────────────────────────────────────

def _row_to_runtime_setting(row: sqlite3.Row) -> dict:
    out = dict(row)
    out["is_sensitive"] = bool(out.get("is_sensitive"))
    out["requires_restart"] = bool(out.get("requires_restart"))
    return out


def list_runtime_settings(db_path: Path) -> list[dict]:
    """Return every persisted setting row (global scope only in V1)."""
    with _connect(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM runtime_settings ORDER BY key"
        ).fetchall()
    return [_row_to_runtime_setting(r) for r in rows]


def get_runtime_setting(db_path: Path, key: str) -> dict | None:
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM runtime_settings WHERE key = ?", (key,)
        ).fetchone()
    return _row_to_runtime_setting(row) if row else None


def upsert_runtime_setting(
    db_path: Path,
    key: str,
    *,
    value: str,
    value_type: str,
    scope: str = "global",
    description: str | None = None,
    is_sensitive: bool = False,
    requires_restart: bool = False,
    updated_by: str | None = None,
) -> dict:
    """Insert or update a setting row. Returns the persisted dict."""
    now = _now_iso()
    with _connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO runtime_settings
                (key, value, value_type, scope, description,
                 is_sensitive, requires_restart, updated_at, updated_by)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value            = excluded.value,
                value_type       = excluded.value_type,
                scope            = excluded.scope,
                description      = excluded.description,
                is_sensitive     = excluded.is_sensitive,
                requires_restart = excluded.requires_restart,
                updated_at       = excluded.updated_at,
                updated_by       = excluded.updated_by
            """,
            (
                key,
                value,
                value_type,
                scope,
                description,
                1 if is_sensitive else 0,
                1 if requires_restart else 0,
                now,
                updated_by,
            ),
        )
    row = get_runtime_setting(db_path, key)
    assert row is not None
    return row


def delete_runtime_setting(db_path: Path, key: str) -> None:
    with _connect(db_path) as conn:
        conn.execute("DELETE FROM runtime_settings WHERE key = ?", (key,))


# ── backlog_batches / backlog_batch_tickets ───────────────────────────────────

def insert_backlog_batch(
    db_path: Path,
    batch_id: str,
    *,
    status: str,
    created_at: str,
    last_activity_at: str,
    freeze_blocked: bool = False,
    freeze_blocked_reason: str | None = None,
) -> None:
    with _connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO backlog_batches
                (batch_id, status, created_at, last_activity_at,
                 freeze_blocked, freeze_blocked_reason,
                 dependency_analysis_attempts)
            VALUES (?, ?, ?, ?, ?, ?, 0)
            """,
            (
                batch_id, status, created_at, last_activity_at,
                1 if freeze_blocked else 0, freeze_blocked_reason,
            ),
        )


def get_backlog_batch(db_path: Path, batch_id: str) -> dict | None:
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT * FROM backlog_batches WHERE batch_id = ?", (batch_id,)
        ).fetchone()
    return dict(row) if row else None


def list_backlog_batches(db_path: Path, *, status: str | None = None) -> list[dict]:
    with _connect(db_path) as conn:
        if status is None:
            rows = conn.execute(
                "SELECT * FROM backlog_batches ORDER BY created_at, batch_id"
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM backlog_batches WHERE status = ? "
                "ORDER BY created_at, batch_id",
                (status,),
            ).fetchall()
    return [dict(r) for r in rows]


def update_backlog_batch(db_path: Path, batch_id: str, **fields) -> None:
    if not fields:
        return
    with _connect(db_path) as conn:
        set_clause = ", ".join(f"{k}=?" for k in fields)
        conn.execute(
            f"UPDATE backlog_batches SET {set_clause} WHERE batch_id = ?",
            list(fields.values()) + [batch_id],
        )


def insert_backlog_batch_ticket(
    db_path: Path,
    batch_id: str,
    ticket_id: str,
    added_at: str,
) -> bool:
    """Insert one membership row. Returns False on UNIQUE violation (already in a batch)."""
    try:
        with _connect(db_path) as conn:
            conn.execute(
                "INSERT INTO backlog_batch_tickets (batch_id, ticket_id, added_at) "
                "VALUES (?, ?, ?)",
                (batch_id, ticket_id, added_at),
            )
        return True
    except sqlite3.IntegrityError:
        return False


def list_backlog_batch_ticket_ids(db_path: Path, batch_id: str) -> list[str]:
    with _connect(db_path) as conn:
        rows = conn.execute(
            "SELECT ticket_id FROM backlog_batch_tickets WHERE batch_id = ? "
            "ORDER BY added_at, ticket_id",
            (batch_id,),
        ).fetchall()
    return [r["ticket_id"] for r in rows]


def get_batch_for_ticket(db_path: Path, ticket_id: str) -> str | None:
    with _connect(db_path) as conn:
        row = conn.execute(
            "SELECT batch_id FROM backlog_batch_tickets WHERE ticket_id = ?",
            (ticket_id,),
        ).fetchone()
    return row["batch_id"] if row else None


# ── ticket_dependency_analysis ────────────────────────────────────────────────

def upsert_dependency_analysis(
    db_path: Path,
    *,
    ticket_id: str,
    batch_id: str,
    depends_on: list[str],
    blocks: list[str],
    parallel_group: str | None,
    conflicting_tickets: list[str],
    execution_phase: str | None,
    relationship_classifications: list[dict],
    analyzed_at: str,
) -> None:
    depends_on_json = json.dumps(depends_on or [])
    blocks_json = json.dumps(blocks or [])
    conflicting_json = json.dumps(conflicting_tickets or [])
    rels_json = json.dumps(relationship_classifications or [])
    with _connect(db_path) as conn:
        conn.execute(
            """
            INSERT INTO ticket_dependency_analysis
                (ticket_id, batch_id, depends_on_json, blocks_json,
                 parallel_group, conflicting_tickets_json, execution_phase,
                 relationship_classifications_json, analyzed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(ticket_id, batch_id) DO UPDATE SET
                depends_on_json                   = excluded.depends_on_json,
                blocks_json                       = excluded.blocks_json,
                parallel_group                    = excluded.parallel_group,
                conflicting_tickets_json          = excluded.conflicting_tickets_json,
                execution_phase                   = excluded.execution_phase,
                relationship_classifications_json = excluded.relationship_classifications_json,
                analyzed_at                       = excluded.analyzed_at
            """,
            (
                ticket_id,
                batch_id,
                depends_on_json,
                blocks_json,
                parallel_group,
                conflicting_json,
                execution_phase,
                rels_json,
                analyzed_at,
            ),
        )


def get_dependency_analysis(
    db_path: Path,
    ticket_id: str,
    batch_id: str | None = None,
) -> dict | None:
    """Return the most recent analysis row for ``ticket_id`` (filtered by batch when given)."""
    with _connect(db_path) as conn:
        if batch_id is None:
            row = conn.execute(
                "SELECT * FROM ticket_dependency_analysis WHERE ticket_id = ? "
                "ORDER BY analyzed_at DESC LIMIT 1",
                (ticket_id,),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT * FROM ticket_dependency_analysis "
                "WHERE ticket_id = ? AND batch_id = ?",
                (ticket_id, batch_id),
            ).fetchone()
    if row is None:
        return None
    out = dict(row)
    for key in (
        "depends_on_json",
        "blocks_json",
        "conflicting_tickets_json",
        "relationship_classifications_json",
    ):
        raw = out.get(key)
        if raw is None or raw == "":
            out[key.removesuffix("_json")] = []
            continue
        try:
            out[key.removesuffix("_json")] = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            out[key.removesuffix("_json")] = []
    return out


# ── Backend selection ─────────────────────────────────────────────────────────
# Everything above is the SQLite backend (the default). When
# RUNTIME_DB_BACKEND=postgres the public API is rebound to the networked
# Postgres backend (runtime_db_pg) so all callers keep using the same names
# (get_db_path, upsert_ticket_runtime, …) without changes. The Postgres handle
# returned by get_db_path() quacks like a Path (.exists()) for compatibility.
#
# IMPORTANT: Postgres mode NEVER falls back to SQLite. A backend mismatch
# between the API, the supervisor and the daemon is a configuration error: a
# silent downgrade would create an invisible split-brain where some components
# read/write Postgres and others read/write a local SQLite file. We therefore
# fail fast (raise) instead of swallowing errors. Backend selection is
# deterministic: it is decided once, here, from RUNTIME_DB_BACKEND.

def _load_pg_backend():
    import importlib.util
    pg_path = Path(__file__).resolve().parent / "runtime_db_pg.py"
    spec = importlib.util.spec_from_file_location("runtime_db_pg", pg_path)
    mod = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(mod)  # type: ignore[union-attr]
    return mod


def verify_backend_available() -> None:
    """SQLite is always available (stdlib). No-op; rebound for Postgres."""
    return None


def healthcheck(db_path) -> None:
    """Validate the SQLite backend (ensure the schema can be created).

    Rebound to the Postgres healthcheck (psycopg + reachability + schema) when
    RUNTIME_DB_BACKEND=postgres. Raises on failure; never degrades silently.
    """
    init_runtime_db(db_path)


def describe_backend():
    """Unambiguous, multi-line description of the ACTIVE backend for logs.

    Returns a list of `runtime_db ...` lines so startup diagnostics make the
    selected backend (and where it points) completely explicit.
    """
    backend = os.environ.get("RUNTIME_DB_BACKEND", "sqlite").strip().lower()
    if backend == "postgres":
        handle = get_db_path()
        return [
            "runtime_db backend=postgres",
            f"runtime_db host={os.environ.get('RUNTIME_DB_HOST', '127.0.0.1')}",
            f"runtime_db database={os.environ.get('RUNTIME_DB_NAME', 'adf')}",
            f"runtime_db project_id={getattr(handle, 'project_id', '?')}",
        ]
    return ["runtime_db backend=sqlite", f"runtime_db path={get_db_path()}"]


_RUNTIME_DB_BACKEND = os.environ.get("RUNTIME_DB_BACKEND", "sqlite").strip().lower()

if _RUNTIME_DB_BACKEND == "postgres":
    # Fail fast on load failure — do NOT fall back to SQLite.
    try:
        _pg = _load_pg_backend()
    except Exception as exc:
        raise RuntimeError(
            "RUNTIME_DB_BACKEND=postgres but the Postgres backend failed to load "
            f"({exc!r}). Postgres mode never falls back to SQLite — fix the "
            "configuration (RUNTIME_DB_* / psycopg). A backend mismatch between "
            "API, supervisor and daemon is a configuration error."
        ) from exc
    # get_db_path(project_id=None) → Postgres handle (single 'adf' DB, project-scoped rows).
    get_db_path = _pg.get_handle  # type: ignore[assignment]

    def _resolve_pg_handle(project_id, project_runtime_root=None):  # noqa: ARG001
        # Postgres ignores per-project filesystem roots — the project_id alone
        # picks the right row scope. ``project_runtime_root`` is accepted for
        # API symmetry with SQLite and is intentionally ignored here.
        return _pg.get_handle(project_id)

    resolve_db_path_for_project = _resolve_pg_handle  # type: ignore[assignment]
    init_runtime_db = _pg.init_runtime_db  # type: ignore[assignment]
    check_and_recover_db = _pg.check_and_recover_db  # type: ignore[assignment]
    verify_backend_available = _pg.verify_backend_available  # type: ignore[assignment]
    healthcheck = _pg.healthcheck  # type: ignore[assignment]
    record_issue_intake = _pg.record_issue_intake  # type: ignore[assignment]
    get_issue_intake = _pg.get_issue_intake  # type: ignore[assignment]
    list_issue_intake = _pg.list_issue_intake  # type: ignore[assignment]
    upsert_ticket_runtime = _pg.upsert_ticket_runtime  # type: ignore[assignment]
    get_ticket_runtime = _pg.get_ticket_runtime  # type: ignore[assignment]
    list_ticket_runtime = _pg.list_ticket_runtime  # type: ignore[assignment]
    upsert_worker = _pg.upsert_worker  # type: ignore[assignment]
    remove_worker = _pg.remove_worker  # type: ignore[assignment]
    list_workers = _pg.list_workers  # type: ignore[assignment]
    append_runtime_event = _pg.append_runtime_event  # type: ignore[assignment]
    list_runtime_events = _pg.list_runtime_events  # type: ignore[assignment]
    upsert_ticket_intelligence = _pg.upsert_ticket_intelligence  # type: ignore[assignment]
    get_ticket_intelligence = _pg.get_ticket_intelligence  # type: ignore[assignment]
    upsert_ticket_readiness = _pg.upsert_ticket_readiness  # type: ignore[assignment]
    get_ticket_readiness = _pg.get_ticket_readiness  # type: ignore[assignment]
    insert_ticket_approval = _pg.insert_ticket_approval  # type: ignore[assignment]
    list_ticket_approvals = _pg.list_ticket_approvals  # type: ignore[assignment]
    get_latest_ticket_approval = _pg.get_latest_ticket_approval  # type: ignore[assignment]
    list_project_rules = _pg.list_project_rules  # type: ignore[assignment]
    upsert_project_rule = _pg.upsert_project_rule  # type: ignore[assignment]
    replace_project_rules = _pg.replace_project_rules  # type: ignore[assignment]
    get_ticket_rule_evaluation = _pg.get_ticket_rule_evaluation  # type: ignore[assignment]
    upsert_ticket_rule_evaluation = _pg.upsert_ticket_rule_evaluation  # type: ignore[assignment]
    upsert_ticket_diagnostics = _pg.upsert_ticket_diagnostics  # type: ignore[assignment]
    get_ticket_diagnostics = _pg.get_ticket_diagnostics  # type: ignore[assignment]
    append_ticket_operation_audit = _pg.append_ticket_operation_audit  # type: ignore[assignment]
    list_ticket_operation_audit = _pg.list_ticket_operation_audit  # type: ignore[assignment]
    list_runtime_settings = _pg.list_runtime_settings  # type: ignore[assignment]
    get_runtime_setting = _pg.get_runtime_setting  # type: ignore[assignment]
    upsert_runtime_setting = _pg.upsert_runtime_setting  # type: ignore[assignment]
    delete_runtime_setting = _pg.delete_runtime_setting  # type: ignore[assignment]
elif _RUNTIME_DB_BACKEND not in ("", "sqlite"):
    raise RuntimeError(
        f"unknown RUNTIME_DB_BACKEND={_RUNTIME_DB_BACKEND!r} "
        "(expected 'sqlite' or 'postgres')"
    )
