## Summary

Implemented T213 strictly per the approved plan.

### Files modified

**Python**
- `tools/agent_runner/ticket_readiness_evaluator.py` — Tightened module docstring to state the entry-prerequisite contract explicitly. Added `_is_entry_prerequisite_reason()` guard and `_FORBIDDEN_BLOCKER_SUBSTRINGS` constant. In `run_evaluation`, every candidate blocker now passes through the guard at runtime — violations are logged and dropped, never block. Renamed `_check_human_plan_review_advisory` → `_collect_future_approval_warnings`; it now emits both `"Human plan review may be required later"` (when `requires_human_plan_review`) and `"Human execution approval may be required later"` (when `requires_human_execution_approval`). Added comment on `_state_implies_plan_approved` clarifying it is a signal only (never influences `blocked`).
- `services/control_api/routes/readiness.py` — Module docstring restating the readiness scope.
- `tools/agent_runner/ticket_execution_eligibility.py` — Added a comment near the `"Human plan approval required"` detail clarifying the Eligibility/Readiness boundary.

**Dashboard**
- `apps/dashboard/src/lib/ticketWorkflowStatus.js` — `readinessStep()` now takes `ticket` and:
  - returns `done` when downstream `ticket.state` is `PLAN_APPROVED` or later;
  - returns `done` for both `ready_candidate` and `ready_to_take`;
  - returns `done` (not `blocked`) when `readiness_status="blocked"` but `blocking_reasons` is empty (defensive against stale rows / advisory-only states).
- `apps/dashboard/src/components/TicketReadinessPanel.jsx` — Removed hardcoded `"Human plan review may be required later"` copy; the payload-driven warnings list is now the single source.

**Tests added**
- `tests/test_ticket_readiness_evaluator.py` — `test_missing_human_execution_approval_does_not_block`, parametrized `test_planner_review_states_do_not_block_readiness`, `test_execution_rules_state_does_not_block_readiness`, `test_blocking_reasons_only_from_entry_prerequisites`, and accept/reject tests for `_is_entry_prerequisite_reason`.
- `tests/test_ticket_readiness_api.py` — `test_readiness_returns_warnings_not_blockers_when_approvals_pending`, `test_readiness_status_ready_candidate_with_advisory_warnings_is_not_blocked`.
- `apps/dashboard/tests/ticketWorkflowStatus.test.js` — Cases for advisory-only warnings, `ready_to_take`, stale `blocked` row with no blockers, and completed-ticket downstream states.

### Verification

- `tests/test_ticket_readiness_*.py` + `tests/test_ticket_execution_eligibility.py` + `tests/test_ticket_approval_service.py` + `tests/test_execution_rules_engine.py` + `tests/test_ticket_diagnostics_safety.py`: **90 passed**.
- Dashboard targeted tests (`ticketWorkflowStatus`, `TicketWorkflowTimeline`, `TicketDetail`, `TicketDetailPage`): **46 passed**.
- Other failures observed in the full suite are pre-existing environment issues (Postgres handle, sandbox/worktree, ticket_timeline 404s, Vitest OOM in `RuntimeDashboardPage`) — none touch the readiness contract.

### Limits / assumptions

- `requires_human_execution_approval` is read defensively from the intelligence row but is not (yet) a real DB column — production rows return falsy and the warning never fires until intelligence is extended to populate it. The test exercises the path via a monkeypatched `get_ticket_intelligence`.
