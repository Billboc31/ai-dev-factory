#!/usr/bin/env python3
"""Postgres backend for the ai-dev-factory runtime store.

Mirrors the public API of ``runtime_db`` (the SQLite store) but talks to a
networked Postgres server. Selected when ``RUNTIME_DB_BACKEND=postgres``.

Why Postgres: the SQLite file lives under the runtime root, which on macOS is a
Docker bind-mount shared between the container (control API) and the host
(supervisor/daemon). SQLite's file locking is unreliable across that boundary →
recurring corruption. A networked server removes the shared-file problem.

Data model — ONE logical database, project-scoped rows
------------------------------------------------------
A single database (``RUNTIME_DB_NAME``, default ``adf``) holds every project's
state. Every table carries a ``project_id`` column and every query filters by
it, so projects are isolated by row, not by database. This was chosen over
"one database per project" because it is far easier to back up, migrate, query,
monitor and reason about, and it avoids unbounded ``CREATE DATABASE`` growth and
the privileges/round-trips that requires. Isolation is enforced by composite
primary keys ``(project_id, <natural key>)`` and ``WHERE project_id = %s``.

Connection comes from the environment:
    RUNTIME_DB_HOST       (default 127.0.0.1; the API container overrides to "db")
    RUNTIME_DB_PORT       (default 5432)
    RUNTIME_DB_USER       (default adf)
    RUNTIME_DB_PASSWORD   (default adf)
    RUNTIME_DB_NAME       (the single database, default adf)

psycopg is imported lazily inside the connection helpers so the pure helpers
(resolve_project_id, PgHandle, get_handle) stay importable without the optional
dependency.
"""

from __future__ import annotations

import datetime
import json
import os

_DEFAULT_DBNAME = "adf"
_DEFAULT_PROJECT_ID = "ai-dev-factory"

_DDL = """
CREATE TABLE IF NOT EXISTS issue_intake (
    project_id   TEXT NOT NULL,
    issue_number INTEGER NOT NULL,
    ticket_id    TEXT NOT NULL,
    branch       TEXT,
    status       TEXT NOT NULL DEFAULT 'ingested',
    ingested_at  TEXT NOT NULL,
    updated_at   TEXT NOT NULL,
    last_error   TEXT,
    PRIMARY KEY (project_id, issue_number)
);

CREATE TABLE IF NOT EXISTS ticket_runtime (
    project_id      TEXT NOT NULL,
    ticket_id       TEXT NOT NULL,
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
    updated_at      TEXT NOT NULL,
    PRIMARY KEY (project_id, ticket_id)
);

CREATE TABLE IF NOT EXISTS workers (
    project_id    TEXT NOT NULL,
    ticket_id     TEXT NOT NULL,
    pid           INTEGER,
    branch        TEXT,
    worktree_path TEXT,
    status        TEXT NOT NULL DEFAULT 'running',
    started_at    TEXT,
    heartbeat_at  TEXT,
    updated_at    TEXT NOT NULL,
    PRIMARY KEY (project_id, ticket_id)
);

CREATE TABLE IF NOT EXISTS runtime_events (
    id            BIGSERIAL PRIMARY KEY,
    project_id    TEXT NOT NULL,
    ticket_id     TEXT,
    event_type    TEXT NOT NULL,
    message       TEXT NOT NULL,
    metadata_json TEXT,
    created_at    TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_runtime_events_project ON runtime_events (project_id);
CREATE INDEX IF NOT EXISTS idx_runtime_events_project_ticket ON runtime_events (project_id, ticket_id);

CREATE TABLE IF NOT EXISTS ticket_intelligence (
    project_id                          TEXT NOT NULL,
    ticket_id                           TEXT NOT NULL,
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
    estimated_cost_min                  DOUBLE PRECISION,
    estimated_cost_max                  DOUBLE PRECISION,
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
    -- Lifecycle timestamps + origin. ISO-8601 in TEXT to match the rest of this
    -- module's convention; columns mirror runtime_db.py (SQLite) so the public
    -- shape stays backend-agnostic. Idempotent ALTERs further down handle
    -- pre-existing databases.
    started_at                          TEXT,
    completed_at                        TEXT,
    failed_at                           TEXT,
    failure_origin                      TEXT,
    stage                               TEXT,
    created_at                          TEXT NOT NULL,
    updated_at                          TEXT NOT NULL,
    PRIMARY KEY (project_id, ticket_id)
);

CREATE TABLE IF NOT EXISTS ticket_readiness (
    project_id               TEXT NOT NULL,
    ticket_id                TEXT NOT NULL,
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
    updated_at               TEXT NOT NULL,
    PRIMARY KEY (project_id, ticket_id)
);

CREATE TABLE IF NOT EXISTS ticket_approvals (
    id               BIGSERIAL PRIMARY KEY,
    project_id       TEXT NOT NULL,
    ticket_id        TEXT NOT NULL,
    approval_type    TEXT NOT NULL,
    approval_status  TEXT NOT NULL,
    approved_by      TEXT,
    approval_comment TEXT,
    approved_at      TEXT,
    created_at       TEXT NOT NULL,
    updated_at       TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_ticket_approvals_lookup
    ON ticket_approvals (project_id, ticket_id, approval_type, id);

CREATE TABLE IF NOT EXISTS project_execution_rules (
    project_id         TEXT NOT NULL,
    rule_key           TEXT NOT NULL,
    enabled            BOOLEAN NOT NULL,
    configuration_json JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at         TEXT NOT NULL DEFAULT to_char(now() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"'),
    updated_at         TEXT NOT NULL DEFAULT to_char(now() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"'),
    PRIMARY KEY (project_id, rule_key)
);

CREATE TABLE IF NOT EXISTS ticket_rule_evaluation (
    ticket_id          TEXT NOT NULL PRIMARY KEY,
    project_id         TEXT NOT NULL,
    eligibility_status TEXT NOT NULL,
    failed_rules_json  JSONB NOT NULL DEFAULT '[]'::jsonb,
    passed_rules_json  JSONB NOT NULL DEFAULT '[]'::jsonb,
    warnings_json      JSONB NOT NULL DEFAULT '[]'::jsonb,
    evaluated_at       TEXT NOT NULL,
    created_at         TEXT NOT NULL DEFAULT to_char(now() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"'),
    updated_at         TEXT NOT NULL DEFAULT to_char(now() AT TIME ZONE 'UTC', 'YYYY-MM-DD"T"HH24:MI:SS"Z"')
);

CREATE TABLE IF NOT EXISTS ticket_diagnostics (
    project_id               TEXT NOT NULL,
    ticket_id                TEXT NOT NULL,
    diagnostic_status        TEXT NOT NULL DEFAULT 'completed',
    is_stuck                 INTEGER NOT NULL DEFAULT 0,
    severity                 TEXT NOT NULL DEFAULT 'info',
    summary                  TEXT,
    current_state            TEXT,
    last_known_step          TEXT,
    last_error               TEXT,
    checks_json              JSONB NOT NULL DEFAULT '[]'::jsonb,
    recommended_actions_json JSONB NOT NULL DEFAULT '[]'::jsonb,
    generated_at             TEXT NOT NULL,
    created_at               TEXT NOT NULL,
    updated_at               TEXT NOT NULL,
    PRIMARY KEY (project_id, ticket_id)
);

CREATE TABLE IF NOT EXISTS ticket_operation_audit (
    id            BIGSERIAL PRIMARY KEY,
    project_id    TEXT,
    ticket_id     TEXT NOT NULL,
    operation_key TEXT NOT NULL,
    status        TEXT NOT NULL,
    reason        TEXT,
    requested_by  TEXT,
    details_json  JSONB,
    created_at    TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_ticket_operation_audit_lookup
    ON ticket_operation_audit (project_id, ticket_id, id);

-- T215: Global runtime settings. V1 supports scope='global' only and the table
-- is keyed solely by `key` (no project_id column). All helpers operate without
-- a project_id argument, matching the SQLite backend's semantics one-for-one.
CREATE TABLE IF NOT EXISTS runtime_settings (
    key              TEXT PRIMARY KEY,
    value            TEXT NOT NULL,
    value_type       TEXT NOT NULL,
    scope            TEXT NOT NULL DEFAULT 'global',
    description      TEXT,
    is_sensitive     BOOLEAN NOT NULL DEFAULT FALSE,
    requires_restart BOOLEAN NOT NULL DEFAULT FALSE,
    updated_at       TEXT NOT NULL,
    updated_by       TEXT
);

-- T218: backlog batches and per-batch dependency-analysis output. All three
-- tables carry a project_id column so the same single Postgres database can
-- host multiple projects without row-level leakage. Composite primary keys put
-- project_id first so every lookup is forced to scope by it.
CREATE TABLE IF NOT EXISTS backlog_batches (
    project_id                        TEXT NOT NULL,
    batch_id                          TEXT NOT NULL,
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
    notes                             TEXT,
    PRIMARY KEY (project_id, batch_id)
);

-- A ticket may belong to at most one batch within a project at a time. The
-- UNIQUE(project_id, ticket_id) constraint is what insert_backlog_batch_ticket
-- relies on to report "already in a batch" via ON CONFLICT DO NOTHING.
CREATE TABLE IF NOT EXISTS backlog_batch_tickets (
    project_id TEXT NOT NULL,
    batch_id   TEXT NOT NULL,
    ticket_id  TEXT NOT NULL,
    added_at   TEXT NOT NULL,
    PRIMARY KEY (project_id, batch_id, ticket_id),
    UNIQUE (project_id, ticket_id)
);

CREATE TABLE IF NOT EXISTS ticket_dependency_analysis (
    project_id                        TEXT NOT NULL,
    ticket_id                         TEXT NOT NULL,
    batch_id                          TEXT NOT NULL,
    depends_on_json                   TEXT NOT NULL,
    blocks_json                       TEXT NOT NULL,
    parallel_group                    TEXT,
    conflicting_tickets_json          TEXT NOT NULL,
    execution_phase                   TEXT,
    relationship_classifications_json TEXT NOT NULL,
    analyzed_at                       TEXT NOT NULL,
    PRIMARY KEY (project_id, ticket_id, batch_id)
);
"""


# Idempotent migration block for ticket_intelligence lifecycle columns. Kept
# alongside _DDL so the migration is co-located with the canonical schema. The
# columns mirror runtime_db.py (SQLite) so the API TicketIntelligence response
# is identical regardless of backend — see T208 plan §4.
_TICKET_INTELLIGENCE_LIFECYCLE_MIGRATION = """
ALTER TABLE ticket_intelligence ADD COLUMN IF NOT EXISTS started_at TEXT;
ALTER TABLE ticket_intelligence ADD COLUMN IF NOT EXISTS completed_at TEXT;
ALTER TABLE ticket_intelligence ADD COLUMN IF NOT EXISTS failed_at TEXT;
ALTER TABLE ticket_intelligence ADD COLUMN IF NOT EXISTS failure_origin TEXT;
ALTER TABLE ticket_intelligence ADD COLUMN IF NOT EXISTS stage TEXT;
"""


def _now_iso() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def database_name() -> str:
    """The single logical database that holds all projects' rows."""
    return os.environ.get("RUNTIME_DB_NAME", _DEFAULT_DBNAME)


def resolve_project_id(project_id: str | None) -> str:
    """Resolve the project_id used to scope rows.

    Order: explicit argument → PROJECT_NAME env → default (ai-dev-factory).
    The value is stored verbatim in the project_id column (parameterised, so no
    sanitisation needed). Falling back to a default keeps the column NOT NULL
    while a clear startup banner makes the active project_id observable.
    """
    return project_id or os.environ.get("PROJECT_NAME") or _DEFAULT_PROJECT_ID


class PgHandle:
    """Opaque DB handle for the Postgres backend.

    Carries the project_id used to scope every query, and quacks like the
    ``Path`` returned by the SQLite backend's ``get_db_path`` so existing
    callers (e.g. ``if handle is None or not handle.exists()``) keep working.
    """

    def __init__(self, project_id: str) -> None:
        self.project_id = project_id
        self.dbname = database_name()

    def exists(self) -> bool:
        # Server-backed store: presence is established lazily via init_runtime_db.
        return True

    def describe(self) -> str:
        host = os.environ.get("RUNTIME_DB_HOST", "127.0.0.1")
        return f"backend=postgres project_id={self.project_id} db={self.dbname} host={host}"

    def __str__(self) -> str:
        return f"postgres:{self.dbname}#{self.project_id}"

    def __repr__(self) -> str:
        return f"PgHandle(project_id={self.project_id!r}, dbname={self.dbname!r})"


def get_handle(project_id: str | None = None) -> PgHandle:
    return PgHandle(resolve_project_id(project_id))


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


def ensure_database() -> None:
    """Create the single runtime database if it does not exist (idempotent).

    Connects to the always-present ``postgres`` maintenance DB. In the default
    docker-compose setup the database is created by the container
    (POSTGRES_DB), so this is a best-effort safety net.
    """
    import psycopg

    dbname = database_name()
    with psycopg.connect(**_conn_kwargs("postgres"), autocommit=True) as conn:
        exists = conn.execute(
            "SELECT 1 FROM pg_database WHERE datname = %s", (dbname,)
        ).fetchone()
        if not exists:
            conn.execute(f'CREATE DATABASE "{dbname}"')


def init_runtime_db(handle: PgHandle) -> None:
    """Ensure the database and (project-agnostic) tables exist. Idempotent.

    The schema is shared across all projects, so this does no per-project work —
    it just guarantees the single database and tables are present.
    """
    try:
        with _connect(handle) as conn:
            conn.execute(_DDL)
            conn.execute(_TICKET_INTELLIGENCE_LIFECYCLE_MIGRATION)
    except Exception:
        # Database may not exist yet (fresh server without POSTGRES_DB) — create
        # it once, then retry the DDL.
        ensure_database()
        with _connect(handle) as conn:
            conn.execute(_DDL)
            conn.execute(_TICKET_INTELLIGENCE_LIFECYCLE_MIGRATION)


def check_and_recover_db(handle: PgHandle) -> bool:
    """No-op for Postgres (the server guarantees durability). Always healthy."""
    return True


def verify_backend_available() -> None:
    """Fail fast if the Postgres backend cannot be used.

    Postgres mode NEVER falls back to SQLite, so a missing driver is a hard,
    visible configuration error rather than a silent downgrade.
    """
    try:
        import psycopg  # noqa: F401
    except Exception as exc:  # ImportError or partial install
        raise RuntimeError(
            "RUNTIME_DB_BACKEND=postgres but psycopg is not importable "
            f"({exc!r}). Install psycopg[binary] in this environment. "
            "Postgres mode never falls back to SQLite."
        ) from exc


def healthcheck(handle: PgHandle) -> None:
    """Validate the backend end-to-end: psycopg import + DB reachable + schema.

    Raises (never returns a degraded SQLite handle) so misconfiguration is
    immediately visible to whoever starts the API, supervisor or daemon.
    """
    verify_backend_available()
    init_runtime_db(handle)


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
                (project_id, issue_number, ticket_id, branch, status, ingested_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (project_id, issue_number) DO UPDATE SET
                ticket_id  = EXCLUDED.ticket_id,
                branch     = EXCLUDED.branch,
                status     = EXCLUDED.status,
                updated_at = EXCLUDED.updated_at
            """,
            (handle.project_id, issue_number, ticket_id, branch, status, now, now),
        )


def get_issue_intake(handle: PgHandle, issue_number: int) -> dict | None:
    with _connect(handle) as conn:
        row = conn.execute(
            "SELECT * FROM issue_intake WHERE project_id = %s AND issue_number = %s",
            (handle.project_id, issue_number),
        ).fetchone()
    return dict(row) if row else None


def list_issue_intake(handle: PgHandle) -> list[dict]:
    with _connect(handle) as conn:
        rows = conn.execute(
            "SELECT * FROM issue_intake WHERE project_id = %s ORDER BY issue_number",
            (handle.project_id,),
        ).fetchall()
    return [dict(r) for r in rows]


# ── ticket_runtime ────────────────────────────────────────────────────────────

def upsert_ticket_runtime(handle: PgHandle, ticket_id: str, **fields) -> None:
    now = _now_iso()
    with _connect(handle) as conn:
        existing = conn.execute(
            "SELECT ticket_id FROM ticket_runtime WHERE project_id = %s AND ticket_id = %s",
            (handle.project_id, ticket_id),
        ).fetchone()
        if existing:
            if fields:
                set_clause = ", ".join(f"{k}=%s" for k in fields)
                conn.execute(
                    f"UPDATE ticket_runtime SET {set_clause}, updated_at=%s "
                    f"WHERE project_id=%s AND ticket_id=%s",
                    list(fields.values()) + [now, handle.project_id, ticket_id],
                )
            else:
                conn.execute(
                    "UPDATE ticket_runtime SET updated_at=%s WHERE project_id=%s AND ticket_id=%s",
                    (now, handle.project_id, ticket_id),
                )
        else:
            fields.setdefault("state", "INIT")
            cols = ["project_id", "ticket_id", "updated_at"] + list(fields.keys())
            placeholders = ", ".join(["%s"] * len(cols))
            conn.execute(
                f"INSERT INTO ticket_runtime ({', '.join(cols)}) VALUES ({placeholders})",
                [handle.project_id, ticket_id, now] + list(fields.values()),
            )


def get_ticket_runtime(handle: PgHandle, ticket_id: str) -> dict | None:
    with _connect(handle) as conn:
        row = conn.execute(
            "SELECT * FROM ticket_runtime WHERE project_id = %s AND ticket_id = %s",
            (handle.project_id, ticket_id),
        ).fetchone()
    return dict(row) if row else None


def list_ticket_runtime(handle: PgHandle) -> list[dict]:
    with _connect(handle) as conn:
        rows = conn.execute(
            "SELECT * FROM ticket_runtime WHERE project_id = %s ORDER BY ticket_id",
            (handle.project_id,),
        ).fetchall()
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
                (project_id, ticket_id, pid, branch, worktree_path, status, started_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, 'running', %s, %s)
            ON CONFLICT (project_id, ticket_id) DO UPDATE SET
                pid           = EXCLUDED.pid,
                branch        = EXCLUDED.branch,
                worktree_path = EXCLUDED.worktree_path,
                status        = 'running',
                started_at    = EXCLUDED.started_at,
                updated_at    = EXCLUDED.updated_at
            """,
            (handle.project_id, ticket_id, pid, branch, worktree_path, now, now),
        )


def remove_worker(handle: PgHandle, ticket_id: str) -> None:
    with _connect(handle) as conn:
        conn.execute(
            "DELETE FROM workers WHERE project_id = %s AND ticket_id = %s",
            (handle.project_id, ticket_id),
        )


def list_workers(handle: PgHandle) -> list[dict]:
    with _connect(handle) as conn:
        rows = conn.execute(
            "SELECT * FROM workers WHERE project_id = %s ORDER BY ticket_id",
            (handle.project_id,),
        ).fetchall()
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
            INSERT INTO runtime_events
                (project_id, ticket_id, event_type, message, metadata_json, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (handle.project_id, ticket_id, event_type, message, meta_json, now),
        )


def list_runtime_events(
    handle: PgHandle,
    ticket_id: str | None = None,
    limit: int = 100,
) -> list[dict]:
    with _connect(handle) as conn:
        if ticket_id:
            rows = conn.execute(
                "SELECT * FROM runtime_events WHERE project_id = %s AND ticket_id = %s "
                "ORDER BY id DESC LIMIT %s",
                (handle.project_id, ticket_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM runtime_events WHERE project_id = %s ORDER BY id DESC LIMIT %s",
                (handle.project_id, limit),
            ).fetchall()
    return [dict(r) for r in rows]


# ── ticket_intelligence ────────────────────────────────────────────────────────

def upsert_ticket_intelligence(handle: PgHandle, ticket_id: str, **fields) -> None:
    """Insert or update a ticket_intelligence row. Sets created_at only on first insert."""
    now = _now_iso()
    with _connect(handle) as conn:
        existing = conn.execute(
            "SELECT ticket_id FROM ticket_intelligence WHERE project_id = %s AND ticket_id = %s",
            (handle.project_id, ticket_id),
        ).fetchone()
        if existing:
            if fields:
                set_clause = ", ".join(f"{k}=%s" for k in fields)
                conn.execute(
                    f"UPDATE ticket_intelligence SET {set_clause}, updated_at=%s "
                    f"WHERE project_id=%s AND ticket_id=%s",
                    list(fields.values()) + [now, handle.project_id, ticket_id],
                )
            else:
                conn.execute(
                    "UPDATE ticket_intelligence SET updated_at=%s "
                    "WHERE project_id=%s AND ticket_id=%s",
                    (now, handle.project_id, ticket_id),
                )
        else:
            fields.setdefault("analysis_status", "not_started")
            cols = ["project_id", "ticket_id", "created_at", "updated_at"] + list(fields.keys())
            placeholders = ", ".join(["%s"] * len(cols))
            conn.execute(
                f"INSERT INTO ticket_intelligence ({', '.join(cols)}) VALUES ({placeholders})",
                [handle.project_id, ticket_id, now, now] + list(fields.values()),
            )


def get_ticket_intelligence(handle: PgHandle, ticket_id: str) -> dict | None:
    with _connect(handle) as conn:
        row = conn.execute(
            "SELECT * FROM ticket_intelligence WHERE project_id = %s AND ticket_id = %s",
            (handle.project_id, ticket_id),
        ).fetchone()
    return dict(row) if row else None


# ── ticket_readiness ───────────────────────────────────────────────────────────

_READINESS_LIST_FIELDS = ("blocking_reasons_json", "warnings_json")


def _encode_readiness_lists(fields: dict) -> dict:
    out = dict(fields)
    for key in _READINESS_LIST_FIELDS:
        val = out.get(key)
        if isinstance(val, list):
            out[key] = json.dumps(val)
    return out


def _decode_readiness_lists(row: dict) -> dict:
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


def upsert_ticket_readiness(handle: PgHandle, ticket_id: str, **fields) -> None:
    """Insert or update a ticket_readiness row. Sets created_at only on first insert."""
    fields = _encode_readiness_lists(fields)
    now = _now_iso()
    with _connect(handle) as conn:
        existing = conn.execute(
            "SELECT ticket_id FROM ticket_readiness WHERE project_id = %s AND ticket_id = %s",
            (handle.project_id, ticket_id),
        ).fetchone()
        if existing:
            if fields:
                set_clause = ", ".join(f"{k}=%s" for k in fields)
                conn.execute(
                    f"UPDATE ticket_readiness SET {set_clause}, updated_at=%s "
                    f"WHERE project_id=%s AND ticket_id=%s",
                    list(fields.values()) + [now, handle.project_id, ticket_id],
                )
            else:
                conn.execute(
                    "UPDATE ticket_readiness SET updated_at=%s "
                    "WHERE project_id=%s AND ticket_id=%s",
                    (now, handle.project_id, ticket_id),
                )
        else:
            fields.setdefault("readiness_status", "not_started")
            cols = ["project_id", "ticket_id", "created_at", "updated_at"] + list(fields.keys())
            placeholders = ", ".join(["%s"] * len(cols))
            conn.execute(
                f"INSERT INTO ticket_readiness ({', '.join(cols)}) VALUES ({placeholders})",
                [handle.project_id, ticket_id, now, now] + list(fields.values()),
            )


def get_ticket_readiness(handle: PgHandle, ticket_id: str) -> dict | None:
    with _connect(handle) as conn:
        row = conn.execute(
            "SELECT * FROM ticket_readiness WHERE project_id = %s AND ticket_id = %s",
            (handle.project_id, ticket_id),
        ).fetchone()
    if row is None:
        return None
    return _decode_readiness_lists(dict(row))


# ── ticket_approvals ──────────────────────────────────────────────────────────

_APPROVAL_FINAL_STATUSES = frozenset({"approved", "rejected"})


def insert_ticket_approval(
    handle: PgHandle,
    ticket_id: str,
    approval_type: str,
    approval_status: str,
    approved_by: str | None = None,
    approval_comment: str | None = None,
) -> int:
    now = _now_iso()
    approved_at = now if approval_status in _APPROVAL_FINAL_STATUSES else None
    with _connect(handle) as conn:
        row = conn.execute(
            """
            INSERT INTO ticket_approvals
                (project_id, ticket_id, approval_type, approval_status,
                 approved_by, approval_comment, approved_at,
                 created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                handle.project_id, ticket_id, approval_type, approval_status,
                approved_by, approval_comment, approved_at,
                now, now,
            ),
        ).fetchone()
    return int(row["id"])


def list_ticket_approvals(handle: PgHandle, ticket_id: str) -> list[dict]:
    with _connect(handle) as conn:
        rows = conn.execute(
            "SELECT * FROM ticket_approvals "
            "WHERE project_id = %s AND ticket_id = %s "
            "ORDER BY id ASC",
            (handle.project_id, ticket_id),
        ).fetchall()
    return [dict(r) for r in rows]


def get_latest_ticket_approval(
    handle: PgHandle, ticket_id: str, approval_type: str
) -> dict | None:
    with _connect(handle) as conn:
        row = conn.execute(
            "SELECT * FROM ticket_approvals "
            "WHERE project_id = %s AND ticket_id = %s AND approval_type = %s "
            "ORDER BY id DESC LIMIT 1",
            (handle.project_id, ticket_id, approval_type),
        ).fetchone()
    return dict(row) if row else None


# ── project_execution_rules ───────────────────────────────────────────────────

def _maybe_json_decode(val):
    if val is None:
        return None
    if isinstance(val, (dict, list)):
        return val
    if isinstance(val, str):
        try:
            return json.loads(val)
        except (json.JSONDecodeError, TypeError):
            return None
    return None


def list_project_rules(handle: PgHandle, project_id: str) -> list[dict]:
    with _connect(handle) as conn:
        rows = conn.execute(
            "SELECT * FROM project_execution_rules "
            "WHERE project_id = %s ORDER BY rule_key",
            (project_id,),
        ).fetchall()
    out = []
    for row in rows:
        item = dict(row)
        item["enabled"] = bool(item.get("enabled"))
        raw = item.get("configuration_json")
        decoded = _maybe_json_decode(raw)
        item["configuration"] = decoded if isinstance(decoded, dict) else {}
        out.append(item)
    return out


def upsert_project_rule(
    handle: PgHandle,
    project_id: str,
    rule_key: str,
    enabled: bool,
    configuration: dict | None = None,
) -> None:
    now = _now_iso()
    cfg_json = json.dumps(configuration or {})
    with _connect(handle) as conn:
        conn.execute(
            """
            INSERT INTO project_execution_rules
                (project_id, rule_key, enabled, configuration_json, created_at, updated_at)
            VALUES (%s, %s, %s, %s::jsonb, %s, %s)
            ON CONFLICT (project_id, rule_key) DO UPDATE SET
                enabled            = EXCLUDED.enabled,
                configuration_json = EXCLUDED.configuration_json,
                updated_at         = EXCLUDED.updated_at
            """,
            (project_id, rule_key, bool(enabled), cfg_json, now, now),
        )


def replace_project_rules(
    handle: PgHandle,
    project_id: str,
    rules: list[dict],
) -> None:
    now = _now_iso()
    with _connect(handle) as conn:
        conn.execute("BEGIN")
        try:
            conn.execute(
                "DELETE FROM project_execution_rules WHERE project_id = %s",
                (project_id,),
            )
            for rule in rules:
                cfg_json = json.dumps(rule.get("configuration") or {})
                conn.execute(
                    """
                    INSERT INTO project_execution_rules
                        (project_id, rule_key, enabled, configuration_json,
                         created_at, updated_at)
                    VALUES (%s, %s, %s, %s::jsonb, %s, %s)
                    """,
                    (
                        project_id,
                        rule["rule_key"],
                        bool(rule.get("enabled")),
                        cfg_json,
                        now,
                        now,
                    ),
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
        if isinstance(val, list):
            continue
        decoded = _maybe_json_decode(val)
        out[key] = decoded if isinstance(decoded, list) else []
    return out


def get_ticket_rule_evaluation(handle: PgHandle, ticket_id: str) -> dict | None:
    with _connect(handle) as conn:
        row = conn.execute(
            "SELECT * FROM ticket_rule_evaluation WHERE ticket_id = %s",
            (ticket_id,),
        ).fetchone()
    if row is None:
        return None
    return _decode_rule_eval_lists(dict(row))


def upsert_ticket_rule_evaluation(
    handle: PgHandle,
    ticket_id: str,
    project_id: str,
    eligibility_status: str,
    passed_rules: list,
    failed_rules: list,
    warnings: list,
    evaluated_at: str,
) -> None:
    now = _now_iso()
    passed_json = json.dumps(passed_rules or [])
    failed_json = json.dumps(failed_rules or [])
    warnings_json = json.dumps(warnings or [])
    with _connect(handle) as conn:
        conn.execute(
            """
            INSERT INTO ticket_rule_evaluation
                (ticket_id, project_id, eligibility_status,
                 failed_rules_json, passed_rules_json, warnings_json,
                 evaluated_at, created_at, updated_at)
            VALUES (%s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s, %s, %s)
            ON CONFLICT (ticket_id) DO UPDATE SET
                project_id         = EXCLUDED.project_id,
                eligibility_status = EXCLUDED.eligibility_status,
                failed_rules_json  = EXCLUDED.failed_rules_json,
                passed_rules_json  = EXCLUDED.passed_rules_json,
                warnings_json      = EXCLUDED.warnings_json,
                evaluated_at       = EXCLUDED.evaluated_at,
                updated_at         = EXCLUDED.updated_at
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
_DIAGNOSTICS_JSONB_FIELDS = frozenset(_DIAGNOSTICS_LIST_FIELDS)


def _encode_diagnostics_lists(fields: dict) -> dict:
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
        if isinstance(val, list):
            continue
        decoded = _maybe_json_decode(val)
        out[key] = decoded if isinstance(decoded, list) else []
    return out


def upsert_ticket_diagnostics(handle: PgHandle, ticket_id: str, **fields) -> None:
    """Insert or update a ticket_diagnostics row. Sets created_at only on first insert."""
    fields = _encode_diagnostics_lists(fields)
    now = _now_iso()
    fields.setdefault("generated_at", now)
    with _connect(handle) as conn:
        existing = conn.execute(
            "SELECT ticket_id FROM ticket_diagnostics WHERE project_id = %s AND ticket_id = %s",
            (handle.project_id, ticket_id),
        ).fetchone()
        if existing:
            if fields:
                set_clauses = []
                for k in fields:
                    if k in _DIAGNOSTICS_JSONB_FIELDS:
                        set_clauses.append(f"{k}=%s::jsonb")
                    else:
                        set_clauses.append(f"{k}=%s")
                set_clause = ", ".join(set_clauses)
                conn.execute(
                    f"UPDATE ticket_diagnostics SET {set_clause}, updated_at=%s "
                    f"WHERE project_id=%s AND ticket_id=%s",
                    list(fields.values()) + [now, handle.project_id, ticket_id],
                )
            else:
                conn.execute(
                    "UPDATE ticket_diagnostics SET updated_at=%s "
                    "WHERE project_id=%s AND ticket_id=%s",
                    (now, handle.project_id, ticket_id),
                )
        else:
            cols = ["project_id", "ticket_id", "created_at", "updated_at"] + list(fields.keys())
            placeholder_list = []
            for c in cols:
                if c in _DIAGNOSTICS_JSONB_FIELDS:
                    placeholder_list.append("%s::jsonb")
                else:
                    placeholder_list.append("%s")
            placeholders = ", ".join(placeholder_list)
            conn.execute(
                f"INSERT INTO ticket_diagnostics ({', '.join(cols)}) VALUES ({placeholders})",
                [handle.project_id, ticket_id, now, now] + list(fields.values()),
            )


def get_ticket_diagnostics(handle: PgHandle, ticket_id: str) -> dict | None:
    with _connect(handle) as conn:
        row = conn.execute(
            "SELECT * FROM ticket_diagnostics WHERE project_id = %s AND ticket_id = %s",
            (handle.project_id, ticket_id),
        ).fetchone()
    if row is None:
        return None
    return _decode_diagnostics_lists(dict(row))


# ── ticket_operation_audit ────────────────────────────────────────────────────

def append_ticket_operation_audit(
    handle: PgHandle,
    ticket_id: str,
    project_id: str | None,
    operation_key: str,
    status: str,
    reason: str | None = None,
    requested_by: str | None = None,
    details: dict | None = None,
) -> int:
    now = _now_iso()
    details_json = json.dumps(details) if details else None
    pid = project_id if project_id is not None else handle.project_id
    with _connect(handle) as conn:
        row = conn.execute(
            """
            INSERT INTO ticket_operation_audit
                (project_id, ticket_id, operation_key, status,
                 reason, requested_by, details_json, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s)
            RETURNING id
            """,
            (
                pid, ticket_id, operation_key, status,
                reason, requested_by, details_json, now,
            ),
        ).fetchone()
    return int(row["id"])


def list_ticket_operation_audit(
    handle: PgHandle,
    ticket_id: str,
    limit: int = 50,
) -> list[dict]:
    with _connect(handle) as conn:
        rows = conn.execute(
            "SELECT * FROM ticket_operation_audit "
            "WHERE project_id = %s AND ticket_id = %s "
            "ORDER BY id DESC LIMIT %s",
            (handle.project_id, ticket_id, limit),
        ).fetchall()
    out: list[dict] = []
    for row in rows:
        item = dict(row)
        raw = item.get("details_json")
        if isinstance(raw, (dict, list)):
            item["details"] = raw
        elif isinstance(raw, str) and raw:
            try:
                item["details"] = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                item["details"] = None
        else:
            item["details"] = None
        out.append(item)
    return out


# ── runtime_settings (global only — no project_id) ────────────────────────────

def _row_to_runtime_setting(row: dict) -> dict:
    out = dict(row)
    out["is_sensitive"] = bool(out.get("is_sensitive"))
    out["requires_restart"] = bool(out.get("requires_restart"))
    return out


def list_runtime_settings(handle: PgHandle) -> list[dict]:
    with _connect(handle) as conn:
        rows = conn.execute(
            "SELECT * FROM runtime_settings ORDER BY key"
        ).fetchall()
    return [_row_to_runtime_setting(r) for r in rows]


def get_runtime_setting(handle: PgHandle, key: str) -> dict | None:
    with _connect(handle) as conn:
        row = conn.execute(
            "SELECT * FROM runtime_settings WHERE key = %s", (key,)
        ).fetchone()
    return _row_to_runtime_setting(row) if row else None


def upsert_runtime_setting(
    handle: PgHandle,
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
    now = _now_iso()
    with _connect(handle) as conn:
        conn.execute(
            """
            INSERT INTO runtime_settings
                (key, value, value_type, scope, description,
                 is_sensitive, requires_restart, updated_at, updated_by)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (key) DO UPDATE SET
                value            = EXCLUDED.value,
                value_type       = EXCLUDED.value_type,
                scope            = EXCLUDED.scope,
                description      = EXCLUDED.description,
                is_sensitive     = EXCLUDED.is_sensitive,
                requires_restart = EXCLUDED.requires_restart,
                updated_at       = EXCLUDED.updated_at,
                updated_by       = EXCLUDED.updated_by
            """,
            (
                key,
                value,
                value_type,
                scope,
                description,
                bool(is_sensitive),
                bool(requires_restart),
                now,
                updated_by,
            ),
        )
    row = get_runtime_setting(handle, key)
    assert row is not None
    return row


def delete_runtime_setting(handle: PgHandle, key: str) -> None:
    with _connect(handle) as conn:
        conn.execute("DELETE FROM runtime_settings WHERE key = %s", (key,))


# ── backlog_batches / backlog_batch_tickets (T218) ────────────────────────────
#
# Public signatures mirror the SQLite helpers in runtime_db.py one-for-one so
# the rebind block stays a trivial assignment. Project scoping comes from the
# PgHandle, not from a function parameter — same convention as the rest of
# this module.

def insert_backlog_batch(
    handle: PgHandle,
    batch_id: str,
    *,
    status: str,
    created_at: str,
    last_activity_at: str,
    freeze_blocked: bool = False,
    freeze_blocked_reason: str | None = None,
) -> None:
    with _connect(handle) as conn:
        conn.execute(
            """
            INSERT INTO backlog_batches
                (project_id, batch_id, status, created_at, last_activity_at,
                 freeze_blocked, freeze_blocked_reason,
                 dependency_analysis_attempts)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 0)
            """,
            (
                handle.project_id,
                batch_id,
                status,
                created_at,
                last_activity_at,
                1 if freeze_blocked else 0,
                freeze_blocked_reason,
            ),
        )


def get_backlog_batch(handle: PgHandle, batch_id: str) -> dict | None:
    with _connect(handle) as conn:
        row = conn.execute(
            "SELECT * FROM backlog_batches "
            "WHERE project_id = %s AND batch_id = %s",
            (handle.project_id, batch_id),
        ).fetchone()
    return dict(row) if row else None


def list_backlog_batches(
    handle: PgHandle, *, status: str | None = None
) -> list[dict]:
    with _connect(handle) as conn:
        if status is None:
            rows = conn.execute(
                "SELECT * FROM backlog_batches WHERE project_id = %s "
                "ORDER BY created_at, batch_id",
                (handle.project_id,),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM backlog_batches "
                "WHERE project_id = %s AND status = %s "
                "ORDER BY created_at, batch_id",
                (handle.project_id, status),
            ).fetchall()
    return [dict(r) for r in rows]


def update_backlog_batch(handle: PgHandle, batch_id: str, **fields) -> None:
    """Partial update by kwarg → column. Mirrors the SQLite helper exactly.

    Callers only pass known column names (see backlog_batch.py) so it is safe
    to interpolate them directly. Values stay parameterised.
    """
    if not fields:
        return
    with _connect(handle) as conn:
        set_clause = ", ".join(f"{k}=%s" for k in fields)
        conn.execute(
            f"UPDATE backlog_batches SET {set_clause} "
            f"WHERE project_id=%s AND batch_id=%s",
            list(fields.values()) + [handle.project_id, batch_id],
        )


def insert_backlog_batch_ticket(
    handle: PgHandle,
    batch_id: str,
    ticket_id: str,
    added_at: str,
) -> bool:
    """Insert one membership row. Returns False on conflict (already in a batch).

    Uses ``ON CONFLICT DO NOTHING`` so a ticket that is already in *any* batch
    for this project is rejected without raising — matching the SQLite contract
    where ``UNIQUE(ticket_id)`` raises ``IntegrityError`` and is caught.
    """
    with _connect(handle) as conn:
        cur = conn.execute(
            """
            INSERT INTO backlog_batch_tickets
                (project_id, batch_id, ticket_id, added_at)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT DO NOTHING
            """,
            (handle.project_id, batch_id, ticket_id, added_at),
        )
    return getattr(cur, "rowcount", 0) > 0


def list_backlog_batch_ticket_ids(
    handle: PgHandle, batch_id: str
) -> list[str]:
    with _connect(handle) as conn:
        rows = conn.execute(
            "SELECT ticket_id FROM backlog_batch_tickets "
            "WHERE project_id = %s AND batch_id = %s "
            "ORDER BY added_at, ticket_id",
            (handle.project_id, batch_id),
        ).fetchall()
    return [r["ticket_id"] for r in rows]


def get_batch_for_ticket(handle: PgHandle, ticket_id: str) -> str | None:
    with _connect(handle) as conn:
        row = conn.execute(
            "SELECT batch_id FROM backlog_batch_tickets "
            "WHERE project_id = %s AND ticket_id = %s",
            (handle.project_id, ticket_id),
        ).fetchone()
    return row["batch_id"] if row else None


# ── ticket_dependency_analysis (T218) ─────────────────────────────────────────

_DEPENDENCY_ANALYSIS_JSON_FIELDS = (
    "depends_on_json",
    "blocks_json",
    "conflicting_tickets_json",
    "relationship_classifications_json",
)


def upsert_dependency_analysis(
    handle: PgHandle,
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
    with _connect(handle) as conn:
        conn.execute(
            """
            INSERT INTO ticket_dependency_analysis
                (project_id, ticket_id, batch_id, depends_on_json, blocks_json,
                 parallel_group, conflicting_tickets_json, execution_phase,
                 relationship_classifications_json, analyzed_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (project_id, ticket_id, batch_id) DO UPDATE SET
                depends_on_json                   = EXCLUDED.depends_on_json,
                blocks_json                       = EXCLUDED.blocks_json,
                parallel_group                    = EXCLUDED.parallel_group,
                conflicting_tickets_json          = EXCLUDED.conflicting_tickets_json,
                execution_phase                   = EXCLUDED.execution_phase,
                relationship_classifications_json = EXCLUDED.relationship_classifications_json,
                analyzed_at                       = EXCLUDED.analyzed_at
            """,
            (
                handle.project_id,
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
    handle: PgHandle,
    ticket_id: str,
    batch_id: str | None = None,
) -> dict | None:
    """Return the most recent analysis row for ``ticket_id`` (filtered by batch when given)."""
    with _connect(handle) as conn:
        if batch_id is None:
            row = conn.execute(
                "SELECT * FROM ticket_dependency_analysis "
                "WHERE project_id = %s AND ticket_id = %s "
                "ORDER BY analyzed_at DESC LIMIT 1",
                (handle.project_id, ticket_id),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT * FROM ticket_dependency_analysis "
                "WHERE project_id = %s AND ticket_id = %s AND batch_id = %s",
                (handle.project_id, ticket_id, batch_id),
            ).fetchone()
    if row is None:
        return None
    out = dict(row)
    for key in _DEPENDENCY_ANALYSIS_JSON_FIELDS:
        raw = out.get(key)
        decoded_key = key.removesuffix("_json")
        if raw is None or raw == "":
            out[decoded_key] = []
            continue
        try:
            out[decoded_key] = json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            out[decoded_key] = []
    return out
