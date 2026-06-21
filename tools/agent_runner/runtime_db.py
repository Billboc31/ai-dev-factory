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
elif _RUNTIME_DB_BACKEND not in ("", "sqlite"):
    raise RuntimeError(
        f"unknown RUNTIME_DB_BACKEND={_RUNTIME_DB_BACKEND!r} "
        "(expected 'sqlite' or 'postgres')"
    )
