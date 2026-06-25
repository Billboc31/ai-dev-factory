Summary of work done for T214:

## Implementation summary

Removed the Rules step as a ticket workflow gate per the approved plan. Policy enforcement is deferred to the future Dispatcher; rules engine code and API remain intact but no longer wired to ticket progression.

### Files modified

**Frontend — workflow status & timeline**
- `apps/dashboard/src/lib/ticketWorkflowStatus.js` — removed `'rules'` from `STEP_KEYS`/`STEP_LABELS`, deleted `rulesStep()`, dropped rules from `readyToTakeStep` upstream array, removed `ruleEvaluation` param from `deriveStepStatuses`, dropped `'rules'` from `PRE_EXECUTION`.
- `apps/dashboard/src/pages/TicketDetailPage.jsx` — removed `TicketRuleEvaluationPanel` import, dropped `rules` from `READY_TO_TAKE_GATES`, removed `ruleEvaluation` from `workflowData` state + Promise.all fetch + memo, removed `rules` mapping in `stepContent`.
- `apps/dashboard/src/App.jsx` — removed `ProjectRulesPage` import and `/projects/:projectId/rules` route.

**Backend — eligibility aggregator**
- `tools/agent_runner/ticket_execution_eligibility.py` — removed `'rules'` from `CHECK_ORDER`, deleted `_eval_rules()`, dropped rules from `checks` dict, removed `rule_evaluation` lookup, removed `'rules'` branch from `_next_action_for`.
- `services/control_api/models/schemas.py` — dropped `"rules"` from `TicketExecutionEligibility.blocking_step` Literal.
- `services/control_api/routes/eligibility.py` — doc comment updated.

**Tests updated (only those broken by the changes)**
- `apps/dashboard/tests/TicketWorkflowTimeline.test.jsx`, `apps/dashboard/tests/ticketWorkflowStatus.test.js` — dropped `ruleEvaluation` fixtures and the rules-blocked test; assertions adjusted to 5 steps.
- `apps/dashboard/tests/TicketDetail.test.jsx`, `apps/dashboard/tests/TicketDetailPage.test.jsx` — removed obsolete `getTicketRuleEvaluation` mock setup.
- `tests/test_ticket_execution_eligibility.py` — dropped `_seed_rules_eligible` helper, removed `get_ticket_rule_evaluation` monkeypatch, rewrote `test_blocked_when_rules_blocked` into `test_rules_blocked_no_longer_gates_eligibility` to assert rules no longer block.
- `tests/test_ticket_eligibility_api.py` — removed rules seeding from `_seed_all_green`, dropped `get_ticket_rule_evaluation` rebind, dropped `'rules'` from expected `checks` keys.

### Verifications run

- `pytest tests/test_ticket_execution_eligibility.py tests/test_ticket_eligibility_api.py` — 16/16 pass.
- `pytest tests/test_execution_rules_engine.py tests/test_execution_rules_api.py tests/test_execution_rules_default_policy.py tests/test_execution_rules_db.py tests/test_execution_rules_pipeline_untouched.py` — 51/51 pass (rules engine still works).
- `pytest -k "dispatcher"` — 20/20 pass.
- `pytest tests/test_ticket_diagnostics_service.py tests/test_ticket_diagnostics_api.py tests/test_ticket_readiness_evaluator.py` — 37/37 pass.
- `vitest run` over `ticketWorkflowStatus.test.js`, `TicketWorkflowTimeline.test.jsx`, `TicketDetailPage.test.jsx`, `TicketDetail.test.jsx`, `ProjectRulesPanel.test.jsx`, `TicketRuleEvaluationPanel.test.jsx`, `ProjectRouting.test.jsx`, `api.test.js`, `ProjectSidebar.test.jsx` — 89/89 pass.

### Known limits

- Did not run the full vitest suite to completion: the runner hangs on unrelated test files even after killing and retrying. All test files touching changed code were run individually and pass.
- `ProjectRulesPage.jsx`, `ProjectRulesPanel.jsx`, `TicketRuleEvaluationPanel.jsx` remain on disk (unmounted) per plan — to be repurposed for the future Dispatcher config UI. `apps/dashboard/src/api/tickets.js` still exports `getTicketRuleEvaluation` / `postEvaluateTicketRules`; those panels still reference them but are no longer reachable from any route.
