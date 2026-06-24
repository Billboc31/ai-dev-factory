62 tests pass — including all 16 new tests and the static guards confirming the existing engine/readiness/approval modules are not impacted.

## Summary

Implemented T211: a read-only `TicketExecutionEligibilityService` that aggregates Intelligence + Readiness + Rules + Approval + dependency state into a single `READY_TO_TAKE` decision.

**Files created**
- `tools/agent_runner/ticket_execution_eligibility.py` — pure aggregator with check order `intelligence → dependencies → readiness → rules → approval`. Reuses `_extract_dependencies` and `is_ticket_merged`; never writes to the DB.
- `services/control_api/routes/eligibility.py` — `GET /tickets/{id}/eligibility` and project-scoped variant.
- `tests/test_ticket_execution_eligibility.py` — 9 unit tests covering every documented scenario (all-green, plan-pending, dep-not-merged, intel-missing, rules-blocked, unknown, no-write contract, check-order).
- `tests/test_ticket_eligibility_api.py` — 7 FastAPI tests including a static guard that the new module never imports the scheduler/daemon.

**Files modified**
- `services/control_api/main.py` — mounts the new routers.
- `services/control_api/models/schemas.py` — `TicketExecutionEligibility` + `TicketExecutionEligibilityCheck` Pydantic models.
- `apps/dashboard/src/api/tickets.js` — `getTicketEligibility(id, projectId)` client.
- `apps/dashboard/src/lib/ticketWorkflowStatus.js` — `eligibilityToGlobalSummary` helper (offline fallback preserved).
- `apps/dashboard/src/components/TicketWorkflowTimeline.jsx` — `WAITING HUMAN ACTION` + `DEPENDENCY BLOCKED` badge styles.
- `apps/dashboard/src/pages/TicketDetailPage.jsx` — fetches eligibility, prefers server payload for the global summary, surfaces reason/next-action/blocking-step in the Ready-To-Take step.
- `apps/dashboard/tests/ticketWorkflowStatus.test.js` + `apps/dashboard/tests/TicketWorkflowTimeline.test.jsx` — new cases for the four eligibility-driven labels.

**Verification**
- 16 new Python tests pass; static guard confirms `tools/agent_runner/ticket_{readiness_evaluator,execution_rules_engine,intelligence_analyzer,approval_service}.py` are byte-identical to `main`.
- 29 dashboard tests in the touched specs pass.
- The pre-existing pytest failures in the wider repo are environment-bound (Postgres backend / supervisor unreachable) and reproduce on `main`; none are caused by this change.

**Known limits / hypotheses**
- The aggregator only treats the `plan` approval row + `state.json` / `plan-approved.md` markers as "human plan approval present" — consistent with how `ticket_readiness_evaluator._check_human_approval` already decides. It deliberately does not invent a new approval type.
- Tests use `RUNTIME_DB_BACKEND=sqlite` even when the dev shell exports `postgres`, by rebinding the aggregator's `runtime_db` getters to the SQLite module — same pattern already used by `test_execution_rules_engine.py`/`test_execution_rules_api.py`.
