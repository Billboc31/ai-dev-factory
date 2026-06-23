## Objective
Replace the stacked collection of disconnected ticket panels on the Ticket detail page with a vertical workflow timeline at the top of the page. Each step shows a compact status / reason / next-action summary and can be expanded inline to reveal the full existing panel. A prominent global summary surfaces the overall ticket status, blocking reason, and next action. No business logic, API, or backend behavior changes.

## Included

- `apps/dashboard/src/components/TicketWorkflowTimeline.jsx` *(new)*
  - Pure presentational component that renders an ordered list of `TicketWorkflowStep` children.
  - Renders an arrow / connector between steps (`↓`) and a top-of-page global summary block (`Status`, `Reason`, `Next action`) computed by the page from props.
  - Steps order: `Intelligence → Readiness → Rules → Human Approval → Ready To Take → Execution`.
  - No data fetching, no business logic — purely visual.
- `apps/dashboard/src/components/TicketWorkflowStep.jsx` *(new)*
  - Renders one row with: status icon (`✓ / ⏳ / ✗ / ○`), step label, compact summary, optional blocking reason, optional "next action" hint.
  - Expand/collapse via native `<details>` (matches the existing `Disclosure` pattern in `TicketIntelligencePanel.jsx`). Collapsed by default except when the step is the current blocker (auto-open).
  - Accepts `status` (`done | current | blocked | pending`), `label`, `summary`, `blockingReason`, `nextAction`, and `children` (the rich panel to render when expanded).
  - Adds a stable `data-testid` per step (e.g. `workflow-step-intelligence`) for tests.
- `apps/dashboard/src/lib/ticketWorkflowStatus.js` *(new — pure helpers, no I/O)*
  - `deriveStepStatuses({ intelligence, readiness, approval, ruleEvaluation, ticket })` → `{ intelligence, readiness, rules, approval, readyToTake, execution }` each `{ status, summary, blockingReason, nextAction }`.
  - `deriveGlobalSummary(stepStatuses)` → `{ status, reason, nextAction }` (e.g. `BLOCKED` / `READY TO TAKE`), picking the first blocking step in workflow order; falls back to "All checks passed" when none.
  - Mapping rules (read-only; mirrors what the existing panels already display):
    - Intelligence: `analysis_status` (`completed → done`, `running/queued → current`, `failed → blocked`, else `pending`); summary uses `difficulty_score`, `risk_score`.
    - Readiness: `readiness_status` (`ready_candidate → done`, `running/queued → current`, `blocked/failed → blocked`); blockingReason = first entry of `blocking_reasons`.
    - Rules: `eligibility_status` (`eligible → done`, `blocked → blocked`); blockingReason = first `failed_rules[].reason`.
    - Approval: latest approval entry — `approved → done`, `rejected → blocked`, missing/`pending` with `ready_candidate` readiness → `current`.
    - Ready To Take: `done` iff intelligence, readiness, rules, and approval are `done`; otherwise `pending` (or `blocked` if any upstream is `blocked`).
    - Execution: `done` when `ticket.state` is in the post-execution set (`MERGED`, `IMPLEMENTATION_APPROVED`, etc.); `current` when state is in an active execution set; `blocked` when state is in `CONFLICT_PANEL_STATES` or `*_FAILED`; otherwise `pending`.
- `apps/dashboard/src/pages/TicketDetailPage.jsx` *(modified)*
  - Add a single new top-level data fetch for the four shared payloads needed by the helpers (`intelligence`, `readiness`, `approvals`, `ruleEvaluation`), reusing existing `api.getTicketIntelligence`, `api.getTicketReadiness`, `api.getTicketApprovals`, `api.getTicketRuleEvaluation`. Poll every 5s, reset on ticket navigation.
  - Compute `stepStatuses` and `globalSummary` via the new helpers.
  - Render at the top of the page (above the existing tabs and below the title): the global summary block, then `<TicketWorkflowTimeline>` whose six steps wrap the **existing** panels unchanged as their expanded `children`:
    - Intelligence → `<TicketIntelligencePanel>`
    - Readiness → `<TicketReadinessPanel>`
    - Rules → `<TicketRuleEvaluationPanel>`
    - Human Approval → `<HumanApprovalPanel>`
    - Ready To Take → renders an internal "all checks" summary; no extra panel.
    - Execution → `<TicketDiagnosticsPanel>` + `<TicketOperationsPanel>` + the existing `<ConflictResolutionPanel>` (still gated by `CONFLICT_PANEL_STATES`).
  - Remove the six bare `<TicketIntelligencePanel>` … `<TicketOperationsPanel>` renders previously inlined on the page — they are now reached only via the step's expand.
  - Keep the existing tabs section (`timeline / overview / logs / plan / review / tests / artifacts / audit`) and the bottom Workflow / Git-Runtime action buttons untouched.
- `apps/dashboard/tests/TicketWorkflowTimeline.test.jsx` *(new)*
  - Renders six steps in the correct order.
  - Shows the right status icon and blockingReason from a representative fixture.
  - Expanding a step reveals the `children` content.
  - Global summary fixture: blocked-by-approval shows `Reason: Human plan approval required` / `Next action: Approve plan review`.
- `apps/dashboard/tests/ticketWorkflowStatus.test.js` *(new)*
  - Unit tests for `deriveStepStatuses` and `deriveGlobalSummary` covering: nothing-started, intelligence-running, readiness-blocked, approval-pending, all-done.
- `apps/dashboard/tests/TicketDetailPage.test.jsx` *(modified)*
  - Update existing assertions to find the panels inside their expanded step rather than at the page root. Add an assertion that the global summary block renders.

## Excluded

- No changes to any API endpoint, dispatcher, scheduler, worker, readiness/rule evaluation, or any backend or business logic.
- No new backend endpoints, no schema or migration changes.
- No modification of the `WorkflowTimeline` component used inside the `timeline` tab — it stays as-is for the audit-style step view.
- No restyling, refactor, or behavior change inside `TicketIntelligencePanel`, `TicketReadinessPanel`, `TicketRuleEvaluationPanel`, `HumanApprovalPanel`, `TicketDiagnosticsPanel`, or `TicketOperationsPanel` beyond rendering them as expand-children.
- No change to the bottom action button bar or the tab content area.
- No persisted UI state (expand/collapse is in-memory only).
- No internationalization changes beyond the strings introduced in the new components.

## Acceptance criteria

- The Ticket detail page renders, above the tab section, a vertical workflow timeline with exactly six labeled steps in this order: **Intelligence, Readiness, Rules, Human Approval, Ready To Take, Execution**.
- A global summary block above the timeline shows three labeled fields: `Ticket status`, `Reason`, `Next action`. On a ticket awaiting plan approval it reads `BLOCKED` / `Human plan approval required` / `Approve plan review`; on a ready ticket it reads `READY TO TAKE` / `All checks passed` / `Assign worker`.
- Each step shows a compact one-line summary plus, when applicable, a blocking reason and a next-action hint, derived from the same data the existing panels already display.
- Each step is expandable; expanding reveals the full existing panel unchanged (Intelligence, Readiness, Rules, Approval, Diagnostics + Operations + Conflict for Execution). The "Ready To Take" step shows a checklist-style summary of the upstream gates.
- The six previously-inlined panels are no longer rendered as top-level siblings of the timeline; they are only reachable via the corresponding step's expand control.
- No change in network calls beyond consolidating the same data the panels already fetch into a page-level fetch reused by the timeline helpers; existing per-panel polling continues to function when a step is expanded.
- `npm --prefix apps/dashboard run test` passes, including the new `TicketWorkflowTimeline.test.jsx`, `ticketWorkflowStatus.test.js`, and the updated `TicketDetailPage.test.jsx`.
- All other existing tests (dashboard and backend) continue to pass without modification.
- No file under `apps/api/`, `apps/scheduler/`, `apps/worker/`, or any non-dashboard module is modified.
