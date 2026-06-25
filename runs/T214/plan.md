## Objective
Remove the `Rules` step from the ticket workflow timeline and from the Ready To Take eligibility computation, hide the Project Rules configuration UI, and stop surfacing rule failures on ticket pages. The rules engine code remains in place internally but no longer gates ticket progression; policy enforcement will move to the future Dispatcher.

## Included

### Frontend — workflow status & timeline

- `apps/dashboard/src/lib/ticketWorkflowStatus.js`
  - Remove `'rules'` from `STEP_KEYS` (line 7-14).
  - Remove the `rules: 'Rules'` entry from `STEP_LABELS` (line 16-23).
  - Delete the `rulesStep(ruleEvaluation)` function (line 188-215).
  - In `readyToTakeStep(...)`, drop `stepsSoFar.rules` from the `upstream` array (line 252).
  - In `deriveStepStatuses(...)`, stop calling `rulesStep(...)` and remove the `ruleEvaluation` argument; update the returned shape so `steps.rules` is no longer present.
  - In `deriveGlobalSummary(...)`, remove `'rules'` from the `PRE_EXECUTION` array (line 364-373).

- `apps/dashboard/src/components/TicketWorkflowTimeline.jsx`
  - No structural change needed; once `STEP_KEYS` shrinks, the Rules row is no longer rendered. Verify the component still renders correctly with 5 steps.

### Frontend — ticket detail page

- `apps/dashboard/src/pages/TicketDetailPage.jsx`
  - Remove the `{ key: 'rules', label: 'Rule evaluation' }` entry from `READY_TO_TAKE_GATES` (line 147-152).
  - Remove `safeFetch(() => api.getTicketRuleEvaluation(id, projectId))` from the `Promise.all` workflow fetch (line 302-307) and remove the corresponding `ruleEvaluation` field from `workflowData`.
  - Drop the `ruleEvaluation` argument passed to `deriveStepStatuses(...)` (line 345-353).
  - Remove the `rules: <TicketRuleEvaluationPanel … />` entry from the `stepContent` mapping (line 398) so the panel is no longer reachable from the timeline.

### Frontend — Project Rules panel

- `apps/dashboard/src/App.jsx`
  - Remove the `<Route path="/projects/:projectId/rules" element={<ProjectRulesPage />} />` registration (line 93) and the corresponding import.
- Leave `apps/dashboard/src/pages/ProjectRulesPage.jsx`, `apps/dashboard/src/components/ProjectRulesPanel.jsx`, and `apps/dashboard/src/components/TicketRuleEvaluationPanel.jsx` files in place (they become unreferenced but are kept for the future Dispatcher redesign). Add no new code.
- `apps/dashboard/src/components/ProjectSidebar.jsx` — confirm there is no Rules entry to remove (exploration confirms there isn't).

### Backend — eligibility computation

- `tools/agent_runner/ticket_execution_eligibility.py`
  - Remove `"rules"` from `CHECK_ORDER` (line 30).
  - Delete the `_eval_rules(rule_evaluation)` function (line 151-168).
  - In `evaluate_eligibility(...)`, drop the `"rules": _eval_rules(rule_evaluation)` entry from the `checks` dict (line 290) and remove the `rule_evaluation` parameter from the function signature and from every internal/external call site.
  - In `_next_action_for(blocking_step)`, remove the `if blocking_step == "rules"` branch (line 229-230).
  - Update `_status_for(...)` similarly if it handles a `"rules"` case.

- `services/control_api/models/schemas.py`
  - In `TicketExecutionEligibility.blocking_step`, drop `"rules"` from the `Literal[...]` (line 525-600 region).
  - Leave `ProjectRule`, `TicketRuleEvaluation`, `RuleEvaluationEntry`, `RuleWarningEntry` schemas in place (still used by the unchanged Rules API).

- Update every caller of `evaluate_eligibility(...)` that previously passed `rule_evaluation` to stop fetching/passing it. Grep `evaluate_eligibility(` and `getTicketRuleEvaluation` to confirm all sites.

### Backend — Rules engine and API (kept, not wired)

- `tools/agent_runner/execution_rules_engine.py` — no change. Keep code intact.
- `services/control_api/routes/rules.py` and `services/control_api/main.py` (rules routers) — no change. Endpoints remain available for direct API access but are no longer consumed by the dashboard UI.

### Tests

- `apps/dashboard/tests/TicketWorkflowTimeline.test.jsx`
  - Remove `'rules'` from the expected step list (line 39-50).
  - Remove `ruleEvaluation` fixtures.
- `apps/dashboard/tests/ticketWorkflowStatus.test.js` (if it exists for this module) — update assertions to reflect the 5-step timeline and the removal of `rulesStep`.
- `apps/dashboard/tests/ProjectRulesPanel.test.jsx` and `apps/dashboard/tests/TicketRuleEvaluationPanel.test.jsx` — keep the files (the components still compile) but only update them if they break compilation. Do not extend coverage.
- `tests/test_ticket_execution_eligibility.py` (or equivalent) — remove the `"rules"` branch from expected `CHECK_ORDER` and from any test fixtures asserting the rules check is part of the eligibility payload.
- `tests/test_execution_rules_engine.py`, `tests/test_execution_rules_api.py`, `tests/test_execution_rules_default_policy.py`, `tests/test_execution_rules_db.py`, `tests/test_execution_rules_pipeline_untouched.py` — no change; the engine and its API still exist.

## Excluded

- Designing or implementing Dispatcher policies, Dispatcher eligibility engine, or Dispatcher scheduler.
- Permanently deleting the rules engine code (`execution_rules_engine.py`), the rules API routes (`routes/rules.py`), or the Rules-related Pydantic schemas.
- Permanently deleting `ProjectRulesPage.jsx`, `ProjectRulesPanel.jsx`, or `TicketRuleEvaluationPanel.jsx`. They are unmounted, not removed.
- Database migrations to drop rule_evaluation tables or purge stored rule evaluation rows.
- Any change to the workflow engine, scheduler, worker, or to the `Ready To Take` semantic beyond removing rules from its upstream set.
- Re-routing the `Rules` panel into a Dispatcher configuration page.
- Renaming or restructuring the remaining 5 workflow steps.
- Updating documentation in `ai/memory/*` or `docs/*` beyond what is strictly necessary to keep the project memory coherent (a separate Memory step will handle docs).

## Acceptance criteria

- `STEP_KEYS` in `apps/dashboard/src/lib/ticketWorkflowStatus.js` contains exactly `['intelligence', 'readiness', 'approval', 'readyToTake', 'execution']` in this order.
- Rendering `TicketWorkflowTimeline` on any ticket no longer shows a "Rules" row, neither as `BLOCKED` nor as `PASSED`.
- The Ready To Take checklist in `TicketDetailPage` no longer lists "Rule evaluation" as a gate.
- `CHECK_ORDER` in `tools/agent_runner/ticket_execution_eligibility.py` equals `("intelligence", "dependencies", "readiness", "approval")` and `evaluate_eligibility(...)`'s returned `checks` dict has no `"rules"` key.
- `TicketExecutionEligibility.blocking_step` in the schema no longer accepts `"rules"`.
- The route `/projects/:projectId/rules` returns a 404 (or the dashboard's default not-found view) because the route is no longer registered.
- The dashboard never calls `GET /tickets/{id}/rule-evaluation` or `POST /tickets/{id}/evaluate-rules` from any rendered page (verified by grepping `apps/dashboard/src` for `getTicketRuleEvaluation` and `postEvaluateTicketRules`).
- The Rules engine source files (`execution_rules_engine.py`, `routes/rules.py`) still exist and import without errors; their endpoints still respond when called directly.
- Existing dashboard test suite passes (`npm test` in `apps/dashboard`), with the updated timeline test asserting 5 steps.
- Existing Python test suite passes (`pytest`), with the eligibility tests updated to the new `CHECK_ORDER`.
- A ticket whose rules engine evaluation is `blocked` is no longer prevented from reaching `Ready To Take` solely because of rules; only Intelligence, Readiness, and Human Approval can block it.
- Manual smoke check on the dashboard: a ticket page renders without errors when its `rule_evaluation` record is missing.
