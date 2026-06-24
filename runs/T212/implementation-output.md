## Summary

T212 — Implemented the advisory `TicketDispatcherService` per the approved plan. All changes are read-only, opt-in via `AI_DEV_FACTORY_DISPATCHER_MODE` (defaults to `off`), and leave the existing ticket execution chain untouched.

### Files created
- `tools/agent_runner/ticket_dispatcher.py` — service module: `DISPATCHER_MODES`, `get_dispatcher_mode()`, `get_recommended_tickets()`. Short-circuits to an empty payload in `off`; reuses `ticket_execution_eligibility.evaluate_eligibility(...)` for `advisory`/`manual`; refuses to act in `auto` (returns `not_implemented=True`). Score = `50 (READY) + queue_rank bonus + difficulty bonus + age bonus`. Deterministic tiebreak: `(-score, queue_rank, updated_at, ticket_id)`. Excludes states `PLANNING`/`CODING`/`CANCELLED`/`TEST_COMPLETE` and archived tickets.
- `services/control_api/routes/dispatcher.py` — `GET /dispatcher/status`, `GET /dispatcher/recommendations`, `GET /projects/{project_id}/dispatcher/recommendations` (with `?mode=` override).
- `apps/dashboard/src/api/dispatcher.js`, `apps/dashboard/src/pages/DispatcherPage.jsx` — disabled / advisory / manual / auto variants, recommended-queue table, blocked-tickets table. `manual` mode shows an "Open" link to the existing ticket detail page; **no new launch endpoint added**.
- `tests/test_ticket_dispatcher.py` (12 tests), `tests/test_ticket_dispatcher_api.py` (8 tests) — covers `off` short-circuit (asserts eligibility is never called), ranking, blocked list, deterministic ties, `auto` not-implemented, pure-read contract (byte-for-byte DB snapshot), excluded states, no scheduler/daemon imports.

### Files modified
- `services/control_api/models/schemas.py` — added `DispatcherStatus`, `DispatcherRecommendation`, `DispatcherRecommendationIntelligence`, `DispatcherBlockedTicket`, `DispatcherResponse`.
- `services/control_api/main.py` — registers `dispatcher.router` + `dispatcher.project_router`.
- `apps/dashboard/src/App.jsx` — route `/projects/:projectId/dispatcher`.
- `apps/dashboard/src/components/ProjectSidebar.jsx` — "Dispatcher" nav entry.

### Verifications
- All 20 new tests pass (`tests/test_ticket_dispatcher*.py`).
- 60 adjacent tests pass (`test_ticket_execution_eligibility`, `test_ticket_eligibility_api`, `test_ticket_readiness_api`, `test_execution_rules_api`, `test_ticket_intelligence_api`).
- Pre-existing failures in `test_control_api_endpoints.py` (daemon/projects pollution from the live runtime) reproduce on the unmodified branch — unrelated.
- `vite build` succeeds.

### Limits / assumptions
- The eligibility aggregator is invoked once per non-excluded ticket per dispatcher call; on large boards this scales linearly. No caching, as per "read-only and stateless" scope.
- The `manual` mode UI surfaces an "Open" link rather than a direct "Run ticket" button (the existing run-next action lives on the ticket detail page); this matches the plan's "reuses the existing run-ticket action" rule and avoids adding a new launch flow.
