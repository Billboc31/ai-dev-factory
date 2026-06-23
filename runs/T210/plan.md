## Objective

Add end-to-end observability to the Ticket Intelligence execution pipeline so developers can identify exactly where an analysis is blocked or failing. Introduce a persisted `stage` field on each analysis row, emit structured lifecycle logs and runtime events at every transition, ensure every exception carries the stage + identifiers + stacktrace, and surface the current stage and elapsed time in the dashboard while an analysis is running.

## Included

### 1. Schema — new `stage` column on `ticket_intelligence`

- `tools/agent_runner/runtime_db.py`
  - Add `stage TEXT` to the `CREATE TABLE ticket_intelligence` block in `_SCHEMA` (around lines 67–100). Default `NULL` (legacy rows) — the analyzer always sets a stage before writing a row going forward.
  - Append `"stage"` to `_TICKET_INTELLIGENCE_LIFECYCLE_COLUMNS` (around lines 256–261) so the idempotent migration `_ensure_ticket_intelligence_lifecycle_columns` adds the column to existing SQLite databases on next `init_runtime_db()` call.
- `tools/agent_runner/runtime_db_pg.py`
  - Add `stage TEXT` to the Postgres DDL block `_DDL` (around lines 99–138).
- `tools/agent_runner/runtime_db.py::upsert_ticket_intelligence`
  - Add `stage` to the allowed/serialized field set so callers can update it on every persist call.

Stage vocabulary (constants in a new module `tools/agent_runner/ticket_intelligence_stages.py`):

```
STAGE_QUEUED              = "queued"
STAGE_STARTING            = "starting"
STAGE_BUILDING_PROMPT     = "building_prompt"
STAGE_WAITING_AI          = "waiting_ai"
STAGE_PARSING_RESULT      = "parsing_result"
STAGE_PERSISTING          = "persisting"
STAGE_COMPLETED           = "completed"
STAGE_FAILED              = "failed"
```

The module also exposes the ordered list of stages and a tiny `set_stage(db_path, ticket_id, stage)` helper that calls `upsert_ticket_intelligence(..., stage=...)` and writes a `runtime_events` row in a single call.

### 2. Analyzer — emit stage transitions, logs and runtime events

`tools/agent_runner/ticket_intelligence_analyzer.py`:

- At every existing lifecycle point already identified by T208, replace the bare `_intel_log.info("intel.step.<x> ...")` calls with a call to `set_stage(...)` from the new helper (which performs both the DB stage write AND the runtime event write AND the structured log line).
  - Before `upsert_ticket_intelligence(status='running', started_at=_now_iso())` (line ~304) → `STAGE_STARTING`.
  - Before `extract_signals(ticket_content)` (line ~311) → keep STAGE_STARTING; on its return emit a log only (no stage change — extraction is cheap).
  - Before `_load_prompt_template` / `_fill_template` (lines ~318–323) → `STAGE_BUILDING_PROMPT`.
  - Before `_run_ai_subprocess(...)` (line ~245) → `STAGE_WAITING_AI`.
  - Right after subprocess returns, before `_extract_json(stdout)` (line ~383) → `STAGE_PARSING_RESULT`.
  - Before the final `upsert_ticket_intelligence(status='completed', ...)` (line ~407) → `STAGE_PERSISTING`, then immediately `STAGE_COMPLETED` together with `status='completed'`.
- Every failure branch (timeout ~350–363, nonzero rc ~365–381, json parse ~383–398, generic exception ~419–430, finally guard ~431–454) must:
  - Capture the *current* stage (kept in a local variable updated at each transition).
  - Persist `stage=STAGE_FAILED` together with the existing `failure_origin` write.
  - Emit `_intel_log.exception("intel.failed ... stage=%s ...", current_stage, ...)` so the full stacktrace is in the log (use `logger.exception` for the generic-exception branch; use `logger.error` with explicit `exc_info=True` where no live exception exists, e.g. nonzero rc).
  - Write a `runtime_events` row of type `ticket_intelligence_analysis_failed` carrying `stage`, `failure_origin`, `ticket_id`, `project_id`, and a truncated `analysis_summary`.
- Standard log key set, applied uniformly:
  ```
  project_id=<...> ticket_id=<...> stage=<...> duration_ms=<...> 
  ```
  Keep the existing dotted event names (`intel.step.*`, `intel.ai_request.started`, etc.) and add a `stage=<...>` key to every one so log lines remain greppable but now self-describe the lifecycle position.

### 3. Runtime events — persist significant lifecycle transitions

Use the existing `runtime_events` table and `append_runtime_event()` API in `tools/agent_runner/runtime_db.py` (lines ~497–513). Event types to emit from the analyzer:

| Event type                                  | Emitted at                                                   |
|---------------------------------------------|--------------------------------------------------------------|
| `ticket_intelligence_analysis_started`      | When the background thread enters STAGE_STARTING             |
| `ticket_intelligence_ai_process_started`    | Just before `_run_ai_subprocess` (STAGE_WAITING_AI)          |
| `ticket_intelligence_ai_process_completed`  | After subprocess returns (success path) with rc + duration_ms|
| `ticket_intelligence_stage_changed`         | On every stage transition (metadata: `from`, `to`)           |
| `ticket_intelligence_analysis_completed`    | After final `STAGE_COMPLETED` persist                        |
| `ticket_intelligence_analysis_failed`       | In every failure branch (metadata: `stage`, `failure_origin`)|

`metadata_json` payload always contains `{"project_id": ..., "stage": ..., "duration_ms": ...}` plus event-specific fields. Failures additionally include a truncated stacktrace (last ~2 KB) under `traceback`.

### 4. Background-thread crash + reaper alignment

- `services/control_api/routes/intelligence.py` (lines ~357–387) and `services/supervisor/main.py` (lines ~2339–2365): inside the `try/except` that already converts uncaught crashes to `failure_origin='bg_thread_crash'`, also persist `stage=STAGE_FAILED` and append a `ticket_intelligence_analysis_failed` runtime event carrying the stacktrace.
- `tools/agent_runner/ticket_intelligence_recovery.py` (`reap_stale_intelligence`, lines 81–148): when the reaper marks a row as failed, set `stage=STAGE_FAILED` while preserving the existing `failure_origin` precedence (reaper-confirmed vs reaper-stale) and append a `ticket_intelligence_analysis_failed` runtime event with metadata `{"reason": "reaper", "previous_status": ..., "age_seconds": ...}`.

### 5. REST schema — expose `stage`, keep timestamps as-is

- `services/control_api/models/schemas.py` (`TicketIntelligence`, lines ~440–478): add `stage: Optional[str] = None`.
- `services/control_api/routes/intelligence.py::_parse_row` (lines ~174–232): include `"stage": row["stage"] if "stage" in row.keys() else None` in the dictionary returned to the Pydantic model.
- No new endpoint. `GET /tickets/{ticket_id}/intelligence` and the project-scoped variant automatically return the new field.

### 6. Dashboard UI — show current stage + elapsed time while running

`apps/dashboard/src/components/TicketIntelligencePanel.jsx`:

- Add a small helper `STAGE_LABELS = { starting: "Starting…", building_prompt: "Building prompt", waiting_ai: "Waiting for AI response", parsing_result: "Parsing AI response", persisting: "Saving results", … }` (also surface unknown values verbatim as fallback).
- Inside the existing `isActive` branch (lines ~193–195) replace the static "Analysis in progress…" block with:
  ```
  Current stage: <STAGE_LABELS[stage] ?? stage ?? "Running">
  Started: <formatLocale(started_at)>
  Running for: <elapsedSeconds(started_at)>s
  ```
- `elapsedSeconds` is derived locally from `started_at` and a `now` value that re-renders via the existing 4-second `usePolling()` cycle (lines ~125). No new timer needed — the panel already re-renders on every poll.
- Failure section (lines ~197–221): when `stage` is present on a failed analysis, append "Failed during: `<STAGE_LABELS[stage]>`" beneath the existing failure summary.
- No styling overhaul; reuse the existing classes used by the surrounding labels.

### 7. Tests

Pytest (Python):

- `tests/test_ticket_intelligence_analyzer.py`:
  - Add `test_stage_progresses_through_lifecycle_on_success` — assert the row's `stage` is `"completed"` at the end and that intermediate stages have been written to `runtime_events` in order.
  - Add `test_stage_is_set_to_failed_on_timeout` / `_on_nonzero_rc` / `_on_invalid_json` / `_on_exception` — extend the existing T208 tests to also assert `stage == "failed"` and that the runtime event for the failure carries the correct `stage` metadata (e.g. `"waiting_ai"` for timeout, `"parsing_result"` for invalid JSON).
  - Extend `test_finally_guard_marks_running_row_failed` to assert `stage == "failed"` is also written by the guard.
- `tests/test_ticket_intelligence_api.py`:
  - Add `test_get_intelligence_returns_stage_field` — after running an analysis to completion, assert the GET response payload contains `stage == "completed"`.
  - Add `test_bg_thread_crash_writes_stage_failed_and_runtime_event`.
- `tests/test_ticket_intelligence_recovery.py`:
  - Extend an existing reaper test to assert `stage == "failed"` is set and that a `ticket_intelligence_analysis_failed` runtime event is appended.
- `tests/test_ticket_intelligence_db.py`:
  - Add `test_upsert_persists_stage` — write `stage="waiting_ai"` and read it back.
  - Add `test_migration_adds_stage_column_to_existing_db` — open a DB seeded with the pre-T210 schema (no `stage` column), call `init_runtime_db()`, and assert the column is now present.

Frontend (no full-blown jest suite required if none exists for this panel): manually verify in the dashboard that the new lines render while an analysis is in flight and disappear once `analysis_status` becomes `completed`. If a jest test for `TicketIntelligencePanel.jsx` already exists, extend it; do not introduce a new test framework.

### 8. Backwards compatibility

- All new fields are nullable. Old rows without a `stage` value continue to render exactly as before (UI falls back to "Running" / hides "Failed during …" line).
- The new runtime events are append-only and consumed by no other code today; existing consumers of `runtime_events` are unaffected.
- The Pydantic schema field is `Optional` so existing API clients ignoring the new field keep working.

## Excluded

- No change to the AI prompt template, AI model selection, signal extractor, or normalizer logic.
- No change to the 600s / 900s reaper thresholds, no new reaper daemon, no change to the reaper's failure_origin precedence rules.
- No new REST endpoints. No websocket/SSE push of stage transitions — the existing 4-second polling is reused.
- No new dashboard timeline view, no historical stage chart — only the current stage + started_at + elapsed time line is added.
- No metrics export to Prometheus/OpenTelemetry. Observability is delivered via existing logs and the existing `runtime_events` table only.
- No refactor of the analyzer's overall control flow; transitions are layered onto the existing structure.
- No retroactive backfill of `stage` for historical rows.

## Acceptance criteria

- The `ticket_intelligence` table has a new `stage` column on both SQLite and Postgres, and the idempotent migration applies it to pre-existing SQLite databases on the next `init_runtime_db()` call.
- A successful analysis writes `stage` values in this order to the row (verifiable via runtime_events history): `starting` → `building_prompt` → `waiting_ai` → `parsing_result` → `persisting` → `completed`.
- A failing analysis ends with `stage = "failed"` AND the existing `failure_origin` is preserved. The runtime event of type `ticket_intelligence_analysis_failed` carries the stage at which failure occurred.
- Every exception path in the analyzer, in the API background thread, in the supervisor background thread, and in the reaper logs the full stacktrace together with `project_id`, `ticket_id`, and `stage`.
- `GET /tickets/{ticket_id}/intelligence` (and the project-scoped variant) returns the `stage` field in the JSON payload.
- While an analysis is `queued` or `running`, the Ticket Intelligence panel in the dashboard displays the current stage label, the `Started` timestamp, and a `Running for: <N>s` counter that increments on each poll cycle.
- All existing tests pass unchanged; new tests added in section 7 pass.
- A developer reading the application log for a single failing analysis can determine the failure stage without re-running the analysis or adding temporary logs.
