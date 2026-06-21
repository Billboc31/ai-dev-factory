Implementation complete. Here's a summary of the changes:

## Summary

Implemented the T199 ticket exactly per the approved plan: a human approval workflow gating the new `ready_to_take` lifecycle state. All decisions are persisted append-only in a new `ticket_approvals` table; idempotent retries replay the latest row; contradictory transitions and out-of-context decisions return HTTP 409. Scheduler/worker code is unchanged.

### Files created
- `tools/agent_runner/ticket_approval_service.py` — `request_execution_approval`, `approve_execution`, `reject_execution`, `get_ticket_approvals`, `compute_execution_eligibility`
- `services/control_api/routes/approvals.py` — 3 endpoints × 2 mounts (`/tickets/...` + `/projects/{pid}/tickets/...`)
- `apps/dashboard/src/components/HumanApprovalPanel.jsx` — UI panel with badges, history, approve/reject buttons
- `tests/test_ticket_approval_db.py` — 9 tests
- `tests/test_ticket_approval_service.py` — 15 tests
- `tests/test_ticket_approval_api.py` — 14 tests

### Files modified
- `tools/agent_runner/runtime_db.py` — added `ticket_approvals` schema + index + 3 helpers; rebound them for Postgres mode
- `tools/agent_runner/runtime_db_pg.py` — added Postgres `ticket_approvals` table + project-scoped helpers
- `tools/agent_runner/ticket_readiness_evaluator.py` — re-evaluation preserves `ready_to_take` instead of demoting an already-approved ticket
- `services/control_api/models/schemas.py` — `TicketApproval`, `TicketApprovalHistory`, `ApprovalDecision`
- `services/control_api/main.py` — wired the new router
- `apps/dashboard/src/api/tickets.js` — `getTicketApprovals`, `approveExecution`, `rejectExecution`
- `apps/dashboard/src/pages/TicketDetailPage.jsx` — render `HumanApprovalPanel` under `TicketReadinessPanel`
- `apps/dashboard/src/pages/BoardPage.jsx` — `READY CANDIDATE` / `READY TO TAKE` / `BLOCKED` badges + client-side filter

### Verification
- 38 new tests pass (`test_ticket_approval_{db,service,api}.py`)
- Directly impacted regression suite (78 tests across readiness/intelligence/human_approval/runtime_db) all pass under `RUNTIME_DB_BACKEND=sqlite`
- The pre-existing failures in `test_control_api_artifacts.py` / `test_control_api_subprocess.py` / `test_control_api_endpoints.py` were verified to exist at the parent commit and are unrelated to this work (they look like project-root / sandbox-env issues triggered by running from a worktree)

### Limitations
- UI not exercised in a browser (no headless test of the rendered panel/board)
- Auto-commit hook captured intermediate state during the session into commit `5e2b48f6` — the working tree is clean and all final code is in HEAD
