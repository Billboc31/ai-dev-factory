Now I have enough to produce the review. Let me write it.

---

# Implementation Review — T209

## Verdict

The implementation matches the ticket and plan, adds a clean visual workflow timeline above the existing tabs, and preserves access to all six panels via per-step expand. T209-specific tests (36 across 4 files) all pass. The five remaining test failures observed in the full dashboard suite (`RuntimeDashboardPage.test.jsx` × 4, `DaemonActivityFeed.test.jsx` × 1) live in files this branch does **not** modify and are pre-existing — they exist on `main` and are unrelated to T209's diff.

## Correctness vs. ticket

- Global summary block, six ordered steps (`Intelligence → Readiness → Rules → Human Approval → Ready To Take → Execution`), arrows between steps, status chips, blocking-reason and next-action lines: all in `TicketWorkflowTimeline.jsx:36-75` and `TicketWorkflowStep.jsx:32-67`.
- Each step expands to reveal the original panel unchanged (`TicketDetailPage.jsx:361-380`). The six previously-inlined panels are no longer rendered as direct page siblings.
- Auto-open of the first `current`/`blocked` step (`TicketWorkflowTimeline.jsx:41-43`) matches the "land on the blocker" UX requirement.
- Specific UX strings (`Human plan approval required` / `Approve plan review` / `All checks passed` / `Assign worker`) are produced by `ticketWorkflowStatus.js:181-186, 207-213, 316-321` and asserted by tests in both `TicketWorkflowTimeline.test.jsx` and `ticketWorkflowStatus.test.js`.

## Scope compliance

- Diff is limited to `apps/dashboard/src/{components,lib,pages}` + new tests. No changes under `apps/api/`, `apps/scheduler/`, `apps/worker/`, or other modules. ✓
- No new API endpoints; the new top-level fetch reuses existing `getTicketIntelligence/Readiness/Approvals/RuleEvaluation` (`TicketDetailPage.jsx:275-291`). ✓
- Existing tabs, action buttons, and `ConflictResolutionPanel` behavior preserved (now mounted inside the Execution step, still gated on `CONFLICT_PANEL_STATES`).

## Code quality

- `ticketWorkflowStatus.js` is pure, side-effect-free, and exhaustively covered (17 unit tests for `deriveStepStatuses`/`deriveGlobalSummary` including nothing-started, intelligence-running, readiness-blocked, approval-pending, all-done, blocked/active/done execution states).
- Component split is clean: `TicketWorkflowTimeline` only orchestrates layout; `TicketWorkflowStep` only renders one row + expand.
- `safeFetch` (`TicketDetailPage.jsx:207-223`) swallows non-404 errors silently. Acceptable here because the per-panel polling still surfaces its own errors when expanded.

## Observations (non-blocking)

- `CONFLICT_RESOLVING` is listed in both `EXECUTION_ACTIVE_STATES` (line 41) and `EXECUTION_BLOCKED_STATES` (line 46). Because `executionStep` checks blocked before active, conflict-resolving correctly ends up classified as `blocked` — but the duplication is a minor smell. Consider dropping it from `EXECUTION_ACTIVE_STATES`.
- `<details open={defaultOpen}>` is re-evaluated on each 5-s poll. If `blockerKey` is stable across polls, React's diff sees the same `open={true}` prop and won't re-snap the user's manual close — but this is dependent on React's reconciler behavior and matches the pre-existing `Disclosure` pattern in `TicketIntelligencePanel.jsx`. Worth tracking if users report the timeline auto-opening on its own.
- Network duplication is acknowledged in the plan: the page-level fetch plus each open panel's own polling means data is fetched twice while a panel is expanded. The plan explicitly allowed this to keep the existing panels untouched.

## Tests

- New: `tests/TicketWorkflowTimeline.test.jsx` (6 tests), `tests/ticketWorkflowStatus.test.js` (17 tests).
- Updated: `tests/TicketDetailPage.test.jsx` and `tests/TicketDetail.test.jsx` — mocks the four new workflow endpoints, asserts the global-summary block renders.
- Result on this branch: 36 T209 tests pass. The 5 failures in `RuntimeDashboardPage.test.jsx` and `DaemonActivityFeed.test.jsx` exist on `main` (those files were last modified at `598a7562` / `10420d38`, not on this branch) — pre-existing and out of scope for T209.

## Blocking issues

None.

IMPLEMENTATION_APPROVED
