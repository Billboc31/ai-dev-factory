All 134 ticket-intelligence tests pass. The implementation cleanly maps onto the approved plan. Here is the structured review.

---

# Review — T210 Implementation

## Scope & plan compliance
- All 8 plan sections delivered: stage column (SQLite+Postgres+migration), constants module, analyzer stage transitions, runtime events, BG-thread crash handlers (API + supervisor), reaper alignment, REST schema, dashboard UI, tests.
- No scope creep: changes stay within the analyzer pipeline, supervisor/API BG-thread guards, reaper, REST `_parse_row`, panel render. Nothing else touched.
- Excluded items respected: no Prometheus, no new endpoints, no reaper threshold changes, no retroactive backfill.

## Correctness
- **Lifecycle ordering** `tools/agent_runner/ticket_intelligence_analyzer.py:396-639` — `STAGE_STARTING → BUILDING_PROMPT → WAITING_AI → PARSING_RESULT → PERSISTING → COMPLETED` is enforced and verified by `test_stage_progresses_through_lifecycle_on_success`.
- **`current_stage` tracking** — kept in a local var, updated immediately after each successful transition; every failure branch records the *pre-failure* stage via `_emit_failure_event(stage=current_stage, …)`, which is the documented intent.
- **Exception path stage = `starting`** — `extract_signals` runs before `STAGE_BUILDING_PROMPT` is set, matching the plan and `test_unexpected_exception_in_extract_persists_failed`.
- **Finally guard** — re-reads the row, only writes `stage=failed` when status is still `queued/running`; preserves the existing `failure_origin` precedence chain. `KeyboardInterrupt` test confirms BaseException coverage.
- **Reaper alignment** `tools/agent_runner/ticket_intelligence_recovery.py:137-165` — sets `stage=STAGE_FAILED` and appends `ticket_intelligence_analysis_failed` event with `{reason: "reaper", previous_status, age_seconds}`; preserves the prior `failure_origin` ("reaper-confirmed" vs "reaper-stale") cleanly.
- **BG-thread crash handlers** — both `services/control_api/routes/intelligence.py:358-413` and `services/supervisor/main.py:2339-2393` write `stage="failed"` and emit a runtime event with truncated traceback (last 2 KB). Symmetrical implementations, identical metadata shape.
- **API contract** — `stage: Optional[str]` added to `TicketIntelligence`; `_parse_row` extracts it; old clients ignore unknown fields, satisfying backward-compat.
- **UI** `apps/dashboard/src/components/TicketIntelligencePanel.jsx:216-262` — current-stage line + `Started` + `Running for: Ns` rendered under `isActive`; "Failed during: …" only shown when `stage !== 'failed'`; elapsed counter ticks via the existing 4 s `usePolling` cycle.

## Observations (non-blocking)

1. **`STAGE_QUEUED` constant defined but never written.** `tools/agent_runner/ticket_intelligence_stages.py:15` exposes it, but neither `services/control_api/routes/intelligence.py:352` nor `services/supervisor/main.py:2309` set `stage="queued"` when they upsert `analysis_status="queued"`. The dashboard label map has the entry. Behaviorally harmless (UI falls back to "Running"; analyzer immediately overwrites with `STAGE_STARTING`), but the constant is dead code as-is. Either start writing it at the queued upsert (minor consistency win) or drop it from the module — your call.
2. **Literal `"failed"` strings in API/supervisor.** The BG-thread crash handlers (`services/control_api/routes/intelligence.py:388,403`, `services/supervisor/main.py:2368,2383`) use the literal `"failed"` instead of importing `STAGE_FAILED`. Functionally identical but inconsistent with the reaper which imports the constant.
3. **Two events per failure.** Every failure branch emits both a `ticket_intelligence_stage_changed` (via `_set_stage(STAGE_FAILED)`) and a `ticket_intelligence_analysis_failed` event. Intentional and useful (transition + detailed metadata), worth noting for downstream consumers.

## Code quality & safety
- `_truncate_traceback(2048)` (analyzer) and `tb[-2048:]` (API/supervisor) — consistent cap, no risk of unbounded log payloads.
- `_set_stage` catches `Exception` only around `append_runtime_event`, letting `upsert_ticket_intelligence` propagate — correct, since the DB row write is essential while event emission is supplementary.
- No secrets or sensitive data introduced into logs/events.
- No new external dependencies.

## Tests
- 49 new/updated assertions across analyzer / db / API / recovery; full 134-test ticket-intelligence suite passes.
- 27/27 `TicketIntelligencePanel.test.jsx` pass, including the three new T210 cases (running with stage label, fallback when stage missing, "Failed during" line on mid-pipeline failure).
- Migration test (`test_migration_adds_stage_column_to_existing_db`) seeds a pre-T210 schema and asserts the `ALTER TABLE` path actually runs.

## Acceptance criteria
All 8 criteria from the ticket are met and individually verifiable from the diff + tests.

IMPLEMENTATION_APPROVED
