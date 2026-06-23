All 27 TicketIntelligencePanel tests pass with the new T210 stage assertions.

## Summary

I implemented T210 (Ticket Intelligence observability) per the approved plan. End-to-end stage tracking now lets developers identify exactly where an analysis is blocked from logs, runtime events, the API payload, and the dashboard.

### Files modified
- `tools/agent_runner/runtime_db.py` — added `stage` column to the `ticket_intelligence` schema and migration (T210)
- `tools/agent_runner/runtime_db_pg.py` — added `stage` column to the Postgres DDL + idempotent migration
- `tools/agent_runner/ticket_intelligence_stages.py` — **new** module exporting stage constants
- `tools/agent_runner/ticket_intelligence_analyzer.py` — added `_set_stage()` helper; every lifecycle point now writes a stage, appends a runtime event, and logs structured `stage=…` keys. Every failure branch (timeout / nonzero rc / json parse / generic exception / finally guard) persists `stage=failed` + a `ticket_intelligence_analysis_failed` event carrying the stage at which it failed, with a truncated traceback where applicable
- `tools/agent_runner/ticket_intelligence_recovery.py` — reaper sets `stage=failed` and emits a `ticket_intelligence_analysis_failed` runtime event with `{reason, previous_status, age_seconds}`
- `services/control_api/routes/intelligence.py` — `_parse_row` returns `stage`; bg-thread crash handler writes `stage=failed` and appends a runtime event with the traceback
- `services/supervisor/main.py` — bg-thread crash handler writes `stage=failed` and appends a runtime event with the traceback
- `services/control_api/models/schemas.py` — added `stage: Optional[str]` to `TicketIntelligence`
- `apps/dashboard/src/components/TicketIntelligencePanel.jsx` — shows "Current stage / Started / Running for: Ns" while active; appends "Failed during: \<stage\>" on failed analyses
- `apps/dashboard/tests/TicketIntelligencePanel.test.jsx` — updated running-state test; added two new stage-related UI tests

### Tests added
- `tests/test_ticket_intelligence_analyzer.py` — extended timeout / nonzero-rc / invalid-json / exception / finally-guard tests to assert `stage="failed"` + runtime event; new `test_stage_progresses_through_lifecycle_on_success` verifies the complete ordered transition list
- `tests/test_ticket_intelligence_db.py` — `test_upsert_persists_stage`, `test_migration_adds_stage_column_to_existing_db`
- `tests/test_ticket_intelligence_api.py` — `test_get_intelligence_returns_stage_field`, `test_bg_thread_crash_writes_stage_failed_and_runtime_event`
- `tests/test_ticket_intelligence_recovery.py` — `test_reaper_sets_stage_failed_and_emits_event`

### Verifications
- All 49 ticket-intelligence Python tests pass (`tests/test_ticket_intelligence_*.py`)
- 2/2 supervisor intelligence tests pass
- 27/27 `TicketIntelligencePanel.test.jsx` tests pass (including the 3 new T210 cases)
- Other failures in the full suite (env routes, ticket timeline, sandbox worktree, etc.) were verified against the baseline commit `86920467` and are pre-existing — none introduced by T210

### Limitations / assumptions
- Manual UI verification in the live dashboard not performed (no dev server started); covered by the new vitest assertions instead
- The "exception during extract_signals" path emits `stage=starting` (extract runs before STAGE_BUILDING_PROMPT is set) — matches the plan's "kept in a local variable updated at each transition" rule
- The auto-checkpoint hook committed my changes mid-session; the working tree may need re-commit for the latest test additions
