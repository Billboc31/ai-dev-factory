## Objective

Eliminate the desynchronization between Control API, Supervisor, and analyzer that leaves Ticket Intelligence analyses indefinitely visible as `queued` or `running` in the dashboard. Guarantee that every analysis lifecycle terminates in a `completed` or `failed` state reachable through `GET /tickets/{id}/intelligence`, with automatic recovery for stale analyses and clear diagnostic logs of the runtime DB path actually used at each step.

## Included

### 1. Project-scoped DB resolution (root-cause fix)

- `tools/agent_runner/runtime_db.py`:
  - Extend `get_db_path()` with an optional `project_id: str | None = None` argument. When `project_id` is provided and `AI_DEV_FACTORY_RUNTIME_ROOT` is set, return `RUNTIME_ROOT / project_id / _DB_FILENAME`; when `RUNTIME_BASE_ROOT` is set, return `RUNTIME_BASE_ROOT / project_id / _DB_FILENAME`. Without `project_id`, preserve existing behavior so single-project setups keep working.
  - Add a small helper `resolve_db_path_for_project(project_id, project_runtime_root=None)` that mirrors `runtime_resolver.resolve_runs_dir` precedence (explicit `project_runtime_root` wins, then env-derived, then fallback). Use it from both API and supervisor so the resolution rule lives in one place.

- `services/supervisor/main.py` (`project_ticket_intelligence_analyze`, ~line 2246):
  - Replace `db = runtime_db.get_db_path()` with `db = runtime_db.resolve_db_path_for_project(project_id, project_runtime_root=project_runtime_root)`.
  - Initialize the resolved DB (call `runtime_db.init_runtime_db(db)`) before any read/write, since a per-project DB may not yet exist.

- `services/control_api/main.py` (`create_app`, where `app.state.db_path` is set):
  - When a `project_id` is known at startup (single-project deployment), pass it to `get_db_path()`. When the API serves multiple projects, leave `app.state.db_path` as the legacy global path **and** add a per-request resolver helper used by `routes/intelligence.py`.

- `services/control_api/routes/intelligence.py`:
  - Replace `_db_path(request)` calls in `get_intelligence`, `analyze_intelligence`, `get_intelligence_project`, `analyze_intelligence_project` with a new `_resolve_db_for_project(request, project_id)` that calls `runtime_db.resolve_db_path_for_project(project_id, ...)` whenever `project_id` is present, falling back to `app.state.db_path` otherwise.
  - Ensure both the project-scoped GET and POST use the same resolver so reads and writes target the same file.

### 2. Delegation correctness

- `services/control_api/routes/intelligence.py` (`analyze_intelligence`, lines 213–228):
  - Before calling `_delegate_analyze_to_supervisor`, write `analysis_status="queued"` to the resolved project DB so the very first dashboard poll after delegation observes a real row instead of a 404.
  - On any 5xx from supervisor, persist `analysis_status="failed"` with `analysis_summary` describing the delegation failure (unreachable / timeout / non-2xx detail) instead of only raising `HTTPException`. Still raise so the POST surfaces the error, but DB state must reflect reality for the polling UI.

- `services/supervisor/main.py` (`project_ticket_intelligence_analyze`):
  - Wrap the body in a `try/except` that, on any pre-thread failure, persists `analysis_status="failed"` to the resolved project DB before returning the JSON error.
  - Keep the existing idempotency guard (`queued`/`running` short-circuit) but read it from the resolved per-project DB.

### 3. Stale analysis recovery

- New module `tools/agent_runner/ticket_intelligence_recovery.py`:
  - Function `reap_stale_intelligence(db_path, *, now=None) -> list[dict]`.
  - Threshold constants (module-level): `STALE_QUEUED_SECONDS = 10 * 60`, `STALE_RUNNING_SECONDS = 15 * 60`.
  - Scan `ticket_intelligence` rows whose `analysis_status` is `queued` or `running` and whose `updated_at` is older than the threshold. For each, call `upsert_ticket_intelligence(...)` with `analysis_status="failed"` and `analysis_summary=f"Analysis stuck in {prev_status!r} for {age}s — auto-recovered by reaper."`. Return one dict per recovered ticket for logging.
  - The function is read-then-write; no scheduling, no threads inside this module.

- `services/control_api/routes/intelligence.py`:
  - In `get_intelligence` (and the project-scoped variant), call `reap_stale_intelligence(db)` opportunistically **before** the `runtime_db.get_ticket_intelligence` read. This is the cheapest place to trigger recovery: the dashboard polls every 4s while active, so a stuck analysis is auto-reaped on the next poll past the threshold without needing a background daemon.
  - Guard the reaper call so any exception is logged but never breaks the GET.

- `services/supervisor/main.py`: also call the reaper at the top of `project_ticket_intelligence_analyze` so a manual re-analyze on a stuck ticket clears the prior state instead of being blocked by the `queued`/`running` idempotency guard.

### 4. Structured logs covering the lifecycle

In `services/control_api/routes/intelligence.py`, `services/supervisor/main.py`, and `tools/agent_runner/ticket_intelligence_analyzer.py`, add `logger.info` lines (named `"intel"` sub-logger where reasonable) at these points, all including `project_id`, `ticket_id`, and the resolved `db_path`:

- `intel.queued` — when status first set to `queued`.
- `intel.delegated` — control API → supervisor handoff (include supervisor URL).
- `intel.started` — analyzer transitioning to `running`.
- `intel.subprocess` — exec_cmd, timeout, returncode (after subprocess returns).
- `intel.completed` — final upsert with `completed`.
- `intel.failed` — any failure path (timeout, non-zero rc, JSON parse, exception, reaper).
- `intel.reaped` — for each row auto-transitioned by the reaper, with previous status and age.

No log lines may include the full prompt or full stdout; truncate to 500 chars.

### 5. Polling resilience (minimal)

- `apps/dashboard/src/components/TicketIntelligencePanel.jsx`:
  - Add a hard cap on consecutive polling errors (count non-404 failures; after 5 consecutive errors stop polling and surface "polling halted — server unreachable" so the UI does not spin forever on a 5xx loop).
  - No other UI changes; the existing terminal-state handling for `completed`/`failed` already stops polling correctly once the API returns those states.

### 6. Tests

Add to `tests/`:

- `test_ticket_intelligence_db_resolution.py`:
  - `get_db_path(project_id="P1")` returns `RUNTIME_ROOT/P1/.runtime/ai-dev-factory.sqlite`.
  - `resolve_db_path_for_project` honors explicit `project_runtime_root` over env.
  - Without `project_id`, behavior is unchanged.

- Extend `tests/test_ticket_intelligence_api.py`:
  - `test_project_post_analyze_writes_queued_to_project_db`: with `AI_DEV_FACTORY_RUNTIME_ROOT=/tmp/rt` and `project_id="P1"`, POST analyze writes to `/tmp/rt/P1/.runtime/...`, not the global path.
  - `test_delegated_completion_visible_via_get`: monkeypatch `_delegate_analyze_to_supervisor` to actually call the supervisor handler (or its inner DB write) and assert that the subsequent GET on the same project_id returns the completed row.
  - `test_post_analyze_persists_failure_on_supervisor_unreachable`: when delegation raises `httpx.ConnectError`, the project DB row exists with `analysis_status="failed"`.

- `tests/test_ticket_intelligence_recovery.py`:
  - `test_reaper_transitions_stale_queued_to_failed`: insert row with `analysis_status="queued"` and `updated_at` older than 10 min → after `reap_stale_intelligence`, status is `failed` with descriptive summary.
  - `test_reaper_transitions_stale_running_to_failed`: same but `running` past 15 min.
  - `test_reaper_leaves_fresh_rows_untouched`: rows within threshold are unchanged.
  - `test_get_intelligence_triggers_reaper`: GET on a stuck ticket returns `failed` even when nothing else ran.

- `tests/test_ticket_intelligence_analyzer.py` (extend if exists, else new):
  - `test_subprocess_timeout_persists_failed`: monkeypatch `subprocess.run` to raise `TimeoutExpired` → DB row has `analysis_status="failed"` with timeout summary (covers the analyzer's existing path with an explicit assertion).
  - `test_subprocess_nonzero_rc_persists_failed`.

All new tests must use the existing `tmp_path` fixtures and the `init_runtime_db` helper, and must not invoke a real `claude` binary.

## Excluded

- Migrating SQLite to PostgreSQL or changing the existing dual-backend layer in `runtime_db.py`.
- Introducing a long-running background reaper daemon or cron — recovery is piggy-backed on the dashboard's existing poll, which is sufficient for the symptom described.
- Reworking `_needs_host_exec` detection logic or the supervisor delegation transport (sticking with the current `http://host.docker.internal:8090` + 15 s timeout).
- Refactoring `TicketIntelligencePanel.jsx` beyond the error-count safeguard described in §5.
- Adding new dashboard UI affordances (no new buttons, no diagnostics panel, no manual reaper trigger).
- Touching the ticket diagnostics engine (T203) or the operations panel (T204); the reaper is an independent helper, not a diagnostics action.
- Changing the analyzer prompt template, scoring bands, or normalization logic.
- Schema migrations to `ticket_intelligence` (the existing columns and `updated_at` index are sufficient).

## Acceptance criteria

- `runtime_db.get_db_path(project_id="P1")` with `AI_DEV_FACTORY_RUNTIME_ROOT=/tmp/rt` returns `/tmp/rt/P1/.runtime/ai-dev-factory.sqlite`; the function still works with no argument exactly as before.
- After `POST /projects/P1/tickets/T/intelligence/analyze` through the control API in delegated (Docker) mode, the supervisor's analyzer and the API's `GET /projects/P1/tickets/T/intelligence` read and write the same SQLite file.
- The dashboard panel transitions from `Analysis in progress…` to either the completed result block or the failed banner for every analysis, within the analyzer timeout plus one poll interval (≈124 s) under normal conditions, and within `STALE_RUNNING_SECONDS + POLL_INTERVAL` (≈904 s) in the worst case.
- A ticket whose row has `analysis_status="queued"` and `updated_at` older than 10 minutes is observed as `failed` on the next `GET /tickets/{id}/intelligence`, with `analysis_summary` indicating reaper-driven recovery.
- A ticket whose row has `analysis_status="running"` and `updated_at` older than 15 minutes is observed as `failed` on the next `GET /tickets/{id}/intelligence`.
- When delegation to the supervisor fails (connect error, timeout, or 5xx), the project DB contains a row with `analysis_status="failed"` and a summary describing the failure, and the POST surfaces a non-202 status to the caller.
- Logs at INFO level contain `intel.queued`, `intel.started`, `intel.completed` (or `intel.failed`), `intel.delegated` (when delegated), and `intel.reaped` (when applicable), each line including `project_id`, `ticket_id`, and the resolved `db_path` actually used.
- All new and existing tests in `tests/test_ticket_intelligence_*.py` pass under `pytest tests/test_ticket_intelligence_api.py tests/test_ticket_intelligence_db.py tests/test_ticket_intelligence_db_resolution.py tests/test_ticket_intelligence_recovery.py tests/test_ticket_intelligence_analyzer.py -q`.
- The dashboard panel stops polling and surfaces a clear error message after 5 consecutive non-404 polling failures, instead of polling indefinitely.
- No regression in single-project setups: when `project_id` is absent in the POST/GET path, `runtime_db.get_db_path()` behaves identically to today and `tests/test_ticket_intelligence_api.py` continues to pass without modification of its single-project cases.
