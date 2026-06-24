## Review — T211 Add READY_TO_TAKE eligibility service

### Scope & correctness

The implementation matches the ticket and plan precisely:

- **`tools/agent_runner/ticket_execution_eligibility.py`**: pure read-only aggregator with the documented check order `intelligence → dependencies → readiness → rules → approval`. Reuses `_extract_dependencies` and `is_ticket_merged` rather than reimplementing them. Status mapping (`READY_TO_TAKE` / `BLOCKED` / `WAITING_HUMAN_ACTION` / `DEPENDENCY_BLOCKED` / `UNKNOWN`) matches the spec.
- **`services/control_api/routes/eligibility.py`**: `GET /tickets/{id}/eligibility` + project-scoped variant. Returns 404 for unknown ticket, 503 if DB unavailable. No background thread, no DB writes.
- **`services/control_api/models/schemas.py`**: `TicketExecutionEligibility{,Check}` Pydantic models match the documented payload.
- **Dashboard**: server payload preferred, with `deriveStepStatuses`/`deriveGlobalSummary` retained as offline fallback. New badge styles for `WAITING HUMAN ACTION` (amber) and `DEPENDENCY BLOCKED` (orange). `ReadyToTakeChecklist` surfaces reason / next_action / blocking_step.
- **State.json path** at `tools/agent_runner/ticket_execution_eligibility.py:269` matches the pre-existing pattern in `ticket_readiness_evaluator.py:108` — consistent with the rest of the codebase.

### Non-goals respected

Verified: `ticket_readiness_evaluator.py`, `execution_rules_engine.py`, `ticket_intelligence_analyzer.py`, `ticket_approval_service.py` are untouched. The static guard test `test_eligibility_module_does_not_import_scheduler` (tests/test_ticket_eligibility_api.py:212) enforces no `run_ticket` / `run_daemon` / `supervisor` references. No new DB table or migration. No scheduler/worker changes.

(The diff also surfaces T210 observability changes in `intelligence.py` / `supervisor/main.py` — those are pulled in because the local `main` ref is stale, not T211 modifications.)

### Tests

- 16 new Python tests (`tests/test_ticket_execution_eligibility.py`, `tests/test_ticket_eligibility_api.py`) — all pass.
- 29 dashboard tests (touched specs) pass, including new cases for the four eligibility labels and the `eligibilityToGlobalSummary` mapping.
- Static guards: no scheduler imports, no DB mutation after repeated GETs.

### Minor observations (non-blocking)

- `_eval_intelligence` (tools/agent_runner/ticket_execution_eligibility.py:62) maps `queued`/`running` to `pending`, which then counts as a blocker via `blocking_step` selection and yields `status="BLOCKED"`. Semantically a running analysis is closer to "in progress" than blocked, but for the dispatcher's use case the verdict (don't take this ticket yet) is correct.
- `test_unknown_when_no_signals` (tests/test_ticket_execution_eligibility.py:253) doesn't actually assert `status="UNKNOWN"` — the comment acknowledges this. Practically reaching `UNKNOWN` requires every check including `dependencies` to be `unknown`, but `dependencies` defaults to `passed` when no deps are declared. The end-to-end UNKNOWN path is therefore unreachable in normal flow.
- `test_eligibility_endpoint_does_not_persist` (tests/test_ticket_eligibility_api.py:194) only re-reads readiness — extending it to all four tables would strengthen the no-write contract.

None of these block merge.

IMPLEMENTATION_APPROVED
