# T212 — Test Report

## Validation Method

Static review of implementation artifacts + execution of automated tests + regression baseline against `main`.

Test commands executed:
- `python -m pytest tests/test_ticket_dispatcher.py -v`
- `python -m pytest tests/test_ticket_dispatcher_api.py -v`
- `python -m pytest tests/` (full backend)
- `npx vitest run` (full frontend, from `apps/dashboard`)
- Same backend + frontend suites re-run against `main` to confirm pre-existing failures.

## Implementation artifacts inspected

| Concern | File |
|---|---|
| Service | `tools/agent_runner/ticket_dispatcher.py` |
| API routes | `services/control_api/routes/dispatcher.py` (registered in `services/control_api/main.py:221-223`) |
| API schemas | `services/control_api/models/schemas.py:665-705` |
| UI page | `apps/dashboard/src/pages/DispatcherPage.jsx` |
| UI route | `apps/dashboard/src/App.jsx:94` (`/projects/:projectId/dispatcher`) |
| UI nav | `apps/dashboard/src/components/ProjectSidebar.jsx:6` |
| API client | `apps/dashboard/src/api/dispatcher.js` |
| Backend tests | `tests/test_ticket_dispatcher.py` (12), `tests/test_ticket_dispatcher_api.py` (8) |

## Acceptance criteria

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | A `TicketDispatcherService` exists | **PASS** | `tools/agent_runner/ticket_dispatcher.py` — module exposes `get_recommended_tickets(...)`, `get_dispatcher_mode()`, `DISPATCHER_MODES` |
| 2 | Dispatcher can be disabled | **PASS** | Mode `off` short-circuits to empty payload; default mode is `off`; unknown env value falls back to `off` (`tools/agent_runner/ticket_dispatcher.py:63-83`). Tests `test_default_mode_is_off`, `test_unknown_mode_falls_back_to_off`, `test_off_mode_returns_empty_and_skips_eligibility` pass |
| 3 | When disabled, current behavior is unchanged | **PASS** | In `off`, eligibility evaluator is never called (proven by `test_off_mode_returns_empty_and_skips_eligibility`); no daemon/runner imports anywhere in dispatcher modules (proven by `test_dispatcher_modules_do_not_import_runner`); `run_daemon.py` and `run_ticket.py` contain zero references to `dispatcher` |
| 4 | Advisory recommendations are computed without side effects | **PASS** | `test_dispatcher_does_not_write_to_db` verifies SQLite bytes unchanged before/after calls; `test_endpoint_does_not_persist` verifies the same for HTTP endpoints; service uses only read-only `_safe_call(runtime_db.list_ticket_runtime / get_ticket_intelligence)` |
| 5 | Dispatcher exposes recommendation reasons | **PASS** | Each recommendation includes `reason` (e.g. `"READY_TO_TAKE, difficulty=simple, queue_rank=1, no blockers"`); each blocked entry includes `status`, `blocking_step`, `reason` from the eligibility aggregator. Verified by `test_advisory_returns_ranked_ready_tickets` and `test_blocked_tickets_are_reported` |
| 6 | A dedicated Dispatcher page exists | **PASS** | `DispatcherPage.jsx` renders mode badge, evaluated_at, recommended queue table (rank/score/difficulty/queue_rank/reason), blocked tickets table (status/blocking step/reason), disabled banner, and `not_implemented` notice for `auto`. Route registered at `/projects/:projectId/dispatcher`; sidebar entry present |
| 7 | No worker or scheduler behavior changes | **PASS** | `test_dispatcher_modules_do_not_import_runner` enforces no `run_ticket`/`run_daemon`/`supervisor` references in dispatcher modules; no diff against `run_daemon.py` / `run_ticket.py` (grep returns no `dispatcher` matches) |
| 8 | Existing tests continue to pass | **PASS (with regression baseline)** | See test results section |

Additional ticket requirements verified:
- All four modes (`off`, `advisory`, `manual`, `auto`) declared in `DISPATCHER_MODES`. `auto` returns `{not_implemented: True, recommendations: []}` as specified (`test_auto_mode_returns_not_implemented`).
- `manual` returns the same ranked recommendations as `advisory`; launching tickets remains a human action (no auto-execute path) — `test_manual_mode_recommendations_match_advisory`.
- Service input signals match ticket spec: open tickets, READY_TO_TAKE eligibility, queue_rank, intelligence/difficulty, ticket age, runtime state.
- Output shape matches example (`ticket_id`, `score`, `rank`, `reason`, plus `intelligence`, `ready_to_take`).

## Test results

### Dispatcher-specific (added by T212)
- **Backend unit (`test_ticket_dispatcher.py`)**: 12 passed / 0 failed
- **Backend API (`test_ticket_dispatcher_api.py`)**: 8 passed / 0 failed
- **Frontend (T212-touched: `TicketIntelligencePanel`, `TicketWorkflowTimeline`, `ticketWorkflowStatus`)**: 56 passed / 0 failed

### Regression baseline

| Suite | T212 branch | `main` baseline | Delta |
|---|---|---|---|
| Backend (`pytest tests/`) | 1753 passed, 120 failed, 14 errors | 1711 passed, 120 failed, 14 errors | **+42 passing**, identical failures/errors |
| Frontend (`vitest run` in `apps/dashboard`) | 187 passed, 5 failed (1 unhandled OOM) | 187 passed, 5 failed (same files) | identical |

The 120 backend failures + 14 errors and 5 frontend failures (`RuntimeDashboardPage.test.jsx` × 4, `DaemonActivityFeed.test.jsx` × 1) reproduce identically on the `main` worktree at HEAD `4f9cd83` (T209) and are unrelated to dispatcher code (env/runtime DB backend, sandbox worktree, traefik, environment provisioning, etc.). Not regressions caused by T212.

## Anomalies / observations

- **Frontend OOM during full vitest run** (`ERR_WORKER_OUT_OF_MEMORY`): pre-existing on `main`. Tests still report deterministically (187 pass / 5 fail); the OOM occurs in an unhandled worker after the suite reports. Non-blocking for T212 acceptance but worth flagging for a future infra ticket.
- **Pre-existing failure baseline is large** (120 + 14). T212 does not improve or worsen it. Out of scope for this ticket.

## Verdict

**VALIDATION PASS.** All 8 acceptance criteria are satisfied. T212 adds a read-only advisory dispatcher with `off` / `advisory` / `manual` modes (+ reserved `auto`), exposes API endpoints and a dedicated UI page, makes zero changes to the daemon/runner/scheduler, and introduces no regressions against `main`. 20 new dispatcher tests cover mode resolution, ranking, blocked-ticket reporting, read-only contract, and runner-import isolation.
