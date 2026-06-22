## Summary

T204 implementation complete. All changes auto-committed by harness as `6b23e157`.

### Files created
- `tools/agent_runner/ticket_operations.py` — registry of 12 operations (`OperationSpec` dataclass), `OperationContext`, `OperationError`, `list_operations`, `execute_operation`. Defensive post-condition check rejects any write of `PLANNING` / `CODING` / `CANCELLED`.
- `services/control_api/routes/operations.py` — `GET` + `POST` endpoints, both bare and `/projects/{project_id}/...` scoped.
- `apps/dashboard/src/components/TicketOperationsPanel.jsx` — four-group panel, safety-level badges, confirmation modal with reason / typed-id / double-confirm / force inputs, recommended-by-diagnostics chip.
- `tests/test_ticket_operations.py` — 24 tests covering registry shape, confirmation validation, every operation, audit logging, forbidden-state guardrail.
- `tests/test_control_api_operations.py` — 9 API integration tests.
- `apps/dashboard/tests/TicketOperationsPanel.test.jsx` — 6 frontend tests.

### Files modified
- `tools/agent_runner/runtime_db.py` and `runtime_db_pg.py` — `ticket_operation_audit` table, `append_ticket_operation_audit`, `list_ticket_operation_audit`, plus Postgres rebinds.
- `services/control_api/models/schemas.py` — `OperationDescriptor`, `OperationListResponse`, `OperationRequest`, `OperationResult`.
- `services/control_api/main.py` — register new routers.
- `apps/dashboard/src/api/tickets.js` — `listTicketOperations`, `executeTicketOperation`.
- `apps/dashboard/src/pages/TicketDetailPage.jsx` — mount panel.

### Key design choices (per approved plan)
- `reset_to_planning` → `PLAN_FIX_REQUIRED` (existing state).
- `reset_to_coding` → `IMPLEMENTATION_FIX_REQUIRED` (existing state).
- `archive_ticket` writes `archived` / `archived_reason` / `archived_by` / `archived_at` into `state.json`; runner state untouched, no `CANCELLED`.
- `delete_worktree` path-traversal guard (`Path.resolve().relative_to(worktrees_root)`), fresh-heartbeat refusal, dirty-worktree refusal unless `force=true`.
- Every attempt (completed / rejected / errored) audited in both `ticket_operation_audit` and `runtime_events`.
- No scheduler / dispatcher / worker / parallel-execution code touched.

### Test results
- 24/24 service tests pass.
- 9/9 API tests pass.
- 6/6 frontend tests pass.
- 99/99 related backend tests pass with explicit `RUNTIME_DB_BACKEND=sqlite`.
- Wider suite has 118 pre-existing failures (verified unrelated to my changes by `git stash` comparison) — caused by test isolation issues around `RUNTIME_DB_BACKEND` env var pollution and an unrelated supervisor restart-policy bug.
