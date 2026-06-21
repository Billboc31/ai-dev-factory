All implemented and tested. The auto-commit hook captured all 16 files in commit `6ec637a1`.

## Summary

T198 implemented per the approved plan. The Readiness Evaluator is advisory only: it persists a verdict per ticket but does not touch the scheduler, worker, or any execution gate.

### Files added
- `tools/agent_runner/ticket_merge_state.py` — `is_ticket_merged()` with the runtime-DB → GitHub metadata → `git log` resolution order.
- `tools/agent_runner/ticket_readiness_evaluator.py` — `run_evaluation()` background job. Checks intelligence presence, declared dependencies (`Depends on / After / Blocked by T###`), human plan approval (intelligence-driven), and captures `main` SHA for context freshness. Persists `ready_candidate | blocked | failed` with blocking reasons.
- `services/control_api/routes/readiness.py` — `GET /tickets/{id}/readiness` (200/404) and `POST /tickets/{id}/evaluate-readiness` (202, idempotent while `queued/running`), plus `/projects/{id}/...` variants. Registered in `main.py`.
- `apps/dashboard/src/components/TicketReadinessPanel.jsx` — status badge, READY CANDIDATE highlight, blocking-reasons list, warnings, sub-check states, last evaluation date, evaluate button. Mounted in `TicketDetailPage.jsx`.
- `tests/test_ticket_readiness_db.py`, `test_ticket_merge_state.py`, `test_ticket_readiness_evaluator.py`, `test_ticket_readiness_api.py` — 34 tests, all green.

### Files modified
- `tools/agent_runner/runtime_db.py` / `runtime_db_pg.py` — added `ticket_readiness` table (canonical lowercase statuses) and `upsert_ticket_readiness` / `get_ticket_readiness` with JSON-list encode/decode; Postgres rebinding added.
- `services/control_api/models/schemas.py` — `TicketReadiness` + `TicketReadinessQueued`.
- `services/control_api/main.py` — registered `readiness` router (and project variant).
- `apps/dashboard/src/api/tickets.js` — `getTicketReadiness` / `postEvaluateReadiness` helpers.

### Verifications
- 34/34 new tests pass.
- Broad suite `pytest tests/ --ignore=tests/integration --ignore=tests/supervisor` returns `118 failed, 1494 passed, 12 errors` — **identical numbers to the pre-change baseline**, so no regressions.

### Limits / assumptions
- Human approval detection looks for `runs/<ticket>/plan-approved.md`, with a fallback that treats a `state.json` state at or beyond `PLAN_APPROVED` as approved (the existing workflow's own approval signal).
- Frontend was not exercised in a browser; React panel changes are covered by component-shape inspection only.
