## Objective
Eliminate the "stuck in running" failure mode of Ticket Intelligence analyses. Every analysis must reach `completed` or `failed` quickly with a meaningful, preserved error message — never relying on the 900 s reaper to mask a swallowed exception or a dead worker. The lifecycle timestamp and origin columns introduced for this fix must exist and round-trip identically across both runtime DB backends (SQLite and Postgres), so the API surface stays backend-agnostic.

## Included

### 1. Background-thread lifecycle hardening
- `services/control_api/routes/intelligence.py` (`analyze_intelligence._bg`, ~L353-363) and `services/supervisor/main.py` (`project_ticket_intelligence_analyze._bg`, ~L2339-2348):
  - On any exception escaping `run_analysis`, the `_bg` wrapper must persist `analysis_status="failed"` with `analysis_summary="Background thread crashed: <exc>"` and `failed_at=<utc-iso>`. Today the `except` only logs.
  - Wrap the entire body of `tools/agent_runner/ticket_intelligence_analyzer.py::run_analysis` in a top-level `try/finally`. The `finally` block re-reads the row; if status is still `queued` or `running`, force-transition it to `failed` with summary `"Analyzer exited without terminal status"` and `failure_origin="finally_guard"`. This closes the path where any code between the `running` write and a terminal write raises (currently `_normalize`, `_load_prompt_template`, `extract_signals`, JSON serialization can do so).
  - Move the `analysis_status="running"` upsert to the very first statement of the `try` block (already there) and add a matching `started_at=<utc-iso>` column write.

### 2. Subprocess execution made forcibly bounded
- In `ticket_intelligence_analyzer.run_analysis`, replace the `subprocess.run(..., timeout=_ANALYSIS_TIMEOUT)` call (L271-280) with a `subprocess.Popen` + `proc.communicate(timeout=_ANALYSIS_TIMEOUT)` pattern that, on `TimeoutExpired`, calls `proc.kill()` then a second `proc.communicate()` to drain pipes, ensuring no orphaned child holds the worker thread.
- Add a configurable `_ANALYSIS_TIMEOUT = int(os.environ.get("AI_DEV_FACTORY_INTEL_TIMEOUT", "120"))` so the upper bound is explicit and tunable.
- Log `intel.ai_request.started` (with command, timeout, prompt_size) before `Popen` and `intel.ai_request.completed` (with rc, stdout_len, stderr_len, duration_ms) after `communicate`. Both at INFO level on `_intel_log`.

### 3. Schema and persistence — SQLite backend
- `tools/agent_runner/runtime_db.py`:
  - Add columns `started_at TEXT`, `completed_at TEXT`, `failed_at TEXT`, `failure_origin TEXT` to the `ticket_intelligence` table. Use an idempotent migration in `init_runtime_db` that introspects `PRAGMA table_info('ticket_intelligence')` and runs `ALTER TABLE ticket_intelligence ADD COLUMN <name> TEXT` only for columns that are missing.
  - Verify `upsert_ticket_intelligence` accepts the new fields through its `**fields` pass-through (no allow-list filtering); add the new column names to any explicit allow-list if one exists.
  - Verify `get_ticket_intelligence` / list helpers return the new columns (a `SELECT *` style is sufficient; a column-list style must be extended).

### 4. Schema and persistence — Postgres backend
- `tools/agent_runner/runtime_db_pg.py`:
  - The `ticket_intelligence` table is owned by this module (CREATE TABLE in `_DDL` ~L99-130). Extend the embedded DDL to declare the four new columns:
    ```
    started_at      TEXT,
    completed_at    TEXT,
    failed_at       TEXT,
    failure_origin  TEXT
    ```
    (nullable, no default — same TEXT-as-ISO-8601 convention used by the surrounding columns).
  - In `init_runtime_db` (~L312), after `conn.execute(_DDL)`, run an idempotent migration block on existing databases:
    ```sql
    ALTER TABLE ticket_intelligence ADD COLUMN IF NOT EXISTS started_at TEXT;
    ALTER TABLE ticket_intelligence ADD COLUMN IF NOT EXISTS completed_at TEXT;
    ALTER TABLE ticket_intelligence ADD COLUMN IF NOT EXISTS failed_at TEXT;
    ALTER TABLE ticket_intelligence ADD COLUMN IF NOT EXISTS failure_origin TEXT;
    ```
    These statements must run in the same connection as the DDL, and must be idempotent so re-running `init_runtime_db` against a populated database is a no-op.
  - Confirm `upsert_ticket_intelligence` (~L543) propagates the new keys through its `**fields` mechanism (current implementation builds the `set_clause` / column list from `fields.keys()`, so no signature change is needed) and that `get_ticket_intelligence` (~L575) returns them (current `SELECT *` is sufficient).
  - No new `runtime_db_pg.py` public function is introduced; only schema and existing helpers are touched.

### 5. Persistence call sites
- In `ticket_intelligence_analyzer.run_analysis`, set `completed_at=<utc-iso>` on the success path (L340-346) and `failed_at=<utc-iso>` together with `failure_origin` (`"timeout"`, `"nonzero_rc"`, `"json_parse"`, `"exception"`, `"finally_guard"`) on every failure path.
- All `upsert_ticket_intelligence` callers use the same keyword arguments regardless of backend, so the SQLite vs Postgres choice is transparent.

### 6. Reaper preserves original cause
- `tools/agent_runner/ticket_intelligence_recovery.py::reap_stale_intelligence` (L72-121):
  - Before overwriting, `SELECT analysis_summary, failure_origin` for the row.
  - If `analysis_summary` is non-empty and `failure_origin` is set, keep them and only append `" (reaper-confirmed after Xs)"`. Set `failure_origin="reaper-confirmed"` only when no prior origin exists.
  - When no prior summary exists, write the current generic message but with `failure_origin="reaper-stale"`.
  - Add `failed_at=<utc-iso>` to the reaper's upsert so failure timestamp is recorded uniformly.

### 7. API schema and dashboard
- `services/control_api/models/schemas.py`: extend `TicketIntelligence` with optional `started_at: str | None`, `completed_at: str | None`, `failed_at: str | None`, `failure_origin: str | None`. The same schema is returned regardless of backend.
- `apps/dashboard/src/components/TicketIntelligencePanel.jsx`: display `failure_origin` and `failed_at` alongside the failure message; JSX-only addition, no polling/logic change.

### 8. Observability — additional structured log lines
In `ticket_intelligence_analyzer.run_analysis`, emit on `_intel_log` (INFO):
- `intel.step.signals_extracted ticket_id=… signals_count=N`
- `intel.step.prompt_built ticket_id=… prompt_len=N`
- `intel.ai_request.started` / `intel.ai_request.completed` (see §2)
- `intel.step.json_parsed ticket_id=… fields=…`
- `intel.persisted ticket_id=… status=completed|failed db_path=…`

### 9. Tests (in `tests/`)
- `test_ticket_intelligence_analyzer.py` — add cases:
  - `test_completed_persists_completed_at` — happy path writes `completed_at`.
  - `test_timeout_uses_kill_and_persists_failed_at` — patch `Popen` so `communicate` raises `TimeoutExpired`; assert `proc.kill()` called, status `failed`, `failure_origin="timeout"`, `failed_at` set.
  - `test_unexpected_exception_in_extract_persists_failed` — monkey-patch `extract_signals` to raise; assert status `failed`, `failure_origin="exception"`.
  - `test_finally_guard_marks_running_row_failed` — monkey-patch `_normalize` to raise `BaseException`; the `finally` re-checks and writes `failed` with `failure_origin="finally_guard"`.
- `test_ticket_intelligence_recovery.py` — add:
  - `test_reaper_preserves_existing_summary` — pre-seed a `running` row with a real error in `analysis_summary` and `failure_origin="exception"`; expect those preserved with a `(reaper-confirmed after Xs)` suffix.
  - `test_reaper_writes_failed_at` — assert `failed_at` populated.
- `test_ticket_intelligence_api.py` — add:
  - `test_bg_thread_crash_persists_failed` — patch `_analyzer.run_analysis` to raise immediately; after the POST, GET returns `failed` with a `"Background thread crashed"` summary (no need for the 900 s reaper).
- Postgres backend coverage:
  - **Preferred** — if the repo already runs Postgres-backed tests (gated by `RUNTIME_DB_BACKEND=postgres` or a `pytest` marker), add `test_pg_ticket_intelligence_lifecycle_fields_are_created_and_round_trip` in `tests/test_runtime_db_pg.py` (or its existing equivalent). It must:
    1. Call `init_runtime_db` on a fresh test database.
    2. Query `information_schema.columns` for `ticket_intelligence` and assert the four new columns are present.
    3. Call `upsert_ticket_intelligence` with all four lifecycle fields, then `get_ticket_intelligence` and assert they round-trip.
    4. Drop one of the four columns, re-run `init_runtime_db`, and assert it is recreated (idempotent migration).
  - **Fallback** — if no Postgres test infrastructure is available, add an acceptance criterion (see §Acceptance criteria) plus a short comment block in `runtime_db_pg.py` adjacent to the new ALTER statements explaining the parity contract with `runtime_db.py`.

### 10. Files modified
- `services/control_api/routes/intelligence.py`
- `services/supervisor/main.py`
- `tools/agent_runner/ticket_intelligence_analyzer.py`
- `tools/agent_runner/ticket_intelligence_recovery.py`
- `tools/agent_runner/runtime_db.py`
- `tools/agent_runner/runtime_db_pg.py`
- `services/control_api/models/schemas.py`
- `apps/dashboard/src/components/TicketIntelligencePanel.jsx`
- New/extended tests under `tests/`

## Excluded
- Replacing the threading-based background execution with a real queue or process pool (Celery, RQ, asyncio worker). Out of scope — would require new infrastructure.
- Introducing any new database abstraction layer or unifying the SQLite and Postgres modules.
- Backfilling `completed_at` / `failed_at` / `failure_origin` for historical rows. NULL on pre-existing rows is acceptable; only new analyses populate them.
- Changing the dashboard polling cadence or auto-retry behaviour (`apps/dashboard/src/components/TicketIntelligencePanel.jsx` polling logic stays as-is).
- Reworking the supervisor delegation HTTP protocol between the Docker API and the host supervisor.
- Adding metrics/Prometheus instrumentation (logging only for now).
- Reaper threshold tuning (`STALE_QUEUED_SECONDS=600`, `STALE_RUNNING_SECONDS=900`). Values stay; we only change what the reaper writes.
- Touching the `ticket_intelligence_extractor` deterministic signal logic.
- Changing Postgres column types from the project-standard `TEXT`-as-ISO-8601 convention to native `TIMESTAMP` types.

## Acceptance criteria
- A POST to `/tickets/{id}/intelligence/analyze` whose background thread raises before `run_analysis` returns leaves the row in `failed` (not `queued` or `running`) within the next poll — verified by `test_bg_thread_crash_persists_failed`.
- A simulated AI subprocess hang produces `failed`, `failure_origin="timeout"`, `failed_at` set, and the `claude` child process is killed (no zombie). Verified by `test_timeout_uses_kill_and_persists_failed_at`.
- A success path writes `analysis_status="completed"`, `completed_at`, and full payload in a single `upsert_ticket_intelligence` call.
- The reaper, when triggered on a row whose `analysis_summary` already contains a real error, preserves that summary and only appends `" (reaper-confirmed after Xs)"`. Verified by `test_reaper_preserves_existing_summary`.
- `PRAGMA table_info('ticket_intelligence')` on a freshly initialised SQLite DB lists `started_at`, `completed_at`, `failed_at`, `failure_origin`. An already-populated SQLite DB receives the same columns via `init_runtime_db` without data loss.
- A freshly initialised Postgres runtime DB has `started_at`, `completed_at`, `failed_at`, `failure_origin` on `ticket_intelligence` — verifiable via `SELECT column_name FROM information_schema.columns WHERE table_name='ticket_intelligence'`. An already-populated Postgres DB receives the same columns via the idempotent `ALTER TABLE … ADD COLUMN IF NOT EXISTS` block in `init_runtime_db` without data loss.
- `upsert_ticket_intelligence` (Postgres) accepts the four new keyword fields and persists them; `get_ticket_intelligence` (Postgres) returns them. SQLite and Postgres expose the same Ticket Intelligence public shape, so the API `TicketIntelligence` response is backend-agnostic.
- Where Postgres test infrastructure is available, `test_pg_ticket_intelligence_lifecycle_fields_are_created_and_round_trip` passes. Where it is not, the parity contract is documented in `runtime_db_pg.py` adjacent to the new ALTER block and reviewed manually.
- `_intel_log` produces, for every analysis, the ordered sequence: `intel.queued` → `intel.started` → `intel.step.signals_extracted` → `intel.step.prompt_built` → `intel.ai_request.started` → `intel.ai_request.completed` → (`intel.step.json_parsed` →) `intel.persisted` (status=`completed` or `failed`).
- The dashboard panel renders the original failure summary and `failure_origin` for `failed` analyses (visual check; no logic regression in StatusBadge).
- `pytest tests/test_ticket_intelligence_*.py` passes — both new and pre-existing tests.
- `ruff` / existing lint config passes on all touched files.
- No analysis row remains in `queued` or `running` for longer than `_ANALYSIS_TIMEOUT + 30 s` under any code path covered by the tests above.
