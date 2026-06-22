## Summary

T201 — Execution Rules Engine — implemented strictly per the approved plan. The engine is advisory only; scheduler/daemon code remains untouched (statically enforced).

### Files created
- `tools/agent_runner/execution_rules_engine.py` — `RuleSpec`/`RuleContext`/`RuleResult` dataclasses, `RULE_REGISTRY` with the six required rules, `get_execution_approval_state` bridge to `compute_execution_eligibility`, `evaluate_ticket(...)`.
- `services/control_api/routes/rules.py` — `GET`/`PUT /projects/{id}/rules`, `GET /tickets/{id}/rule-evaluation`, `POST /tickets/{id}/evaluate-rules` (FastAPI `BackgroundTasks`, returns `202`), with project-scoped mounts.
- `apps/dashboard/src/components/ProjectRulesPanel.jsx`, `apps/dashboard/src/components/TicketRuleEvaluationPanel.jsx`, `apps/dashboard/src/pages/ProjectRulesPage.jsx`.
- Tests: `tests/test_execution_rules_db.py`, `tests/test_execution_rules_engine.py`, `tests/test_execution_rules_default_policy.py`, `tests/test_execution_rules_approval_isolation.py`, `tests/test_execution_rules_pipeline_untouched.py`, `tests/test_execution_rules_api.py`, `apps/dashboard/tests/TicketRuleEvaluationPanel.test.jsx`, `apps/dashboard/tests/ProjectRulesPanel.test.jsx`.

### Files modified
- `tools/agent_runner/runtime_db.py` — added `project_execution_rules` + `ticket_rule_evaluation` schemas and `list_project_rules`/`upsert_project_rule`/`replace_project_rules`/`get_ticket_rule_evaluation`/`upsert_ticket_rule_evaluation` helpers; rebound the new helpers under `RUNTIME_DB_BACKEND=postgres`.
- `tools/agent_runner/runtime_db_pg.py` — mirror DDL (JSONB) and helper functions.
- `services/control_api/models/schemas.py` — `ProjectRule`, `ProjectRulesResponse`, `ProjectRulesUpdate`, `TicketRuleEvaluation`, `TicketRuleEvaluationQueued`, etc.
- `services/control_api/main.py` — register the three rules routers.
- `apps/dashboard/src/api/tickets.js` — `getProjectRules`, `putProjectRules`, `getTicketRuleEvaluation`, `postEvaluateTicketRules`.
- `apps/dashboard/src/App.jsx` — wired `/projects/:projectId/rules` route.
- `apps/dashboard/src/pages/TicketDetailPage.jsx` — embedded `TicketRuleEvaluationPanel`.

### Verifications
- All 53 new Python tests pass (with `env -u RUNTIME_DB_BACKEND -u AI_DEV_FACTORY_RUNTIME_ROOT` to ignore the developer-shell config that pre-existing tests are sensitive to).
- All 15 new dashboard tests pass; existing `TicketIntelligencePanel`/`api`/`usePolling` tests continue to pass.
- Related existing API tests (`test_ticket_intelligence_api`, `test_ticket_readiness_api`, `test_ticket_approval_api`, `test_control_api_main`) continue to pass.

### Limits / known issues
- A larger set of pre-existing failures (`test_control_api_endpoints`, `test_daemon_*`, `test_sandbox_*`, `test_environment_*`, `test_traefik_separation`, etc.) reproduce on `main`-style state without my changes and are unrelated to T201 — they fail because of the shell having `AI_DEV_FACTORY_RUNTIME_ROOT`/`RUNTIME_DB_BACKEND=postgres` exported, or are independently broken. None of the new T201 tests is among the failures, and grepping the failure list for `execution_rules`/`rule_evaluation` returns nothing.
- `apps/dashboard/tests/TicketDetail*.test.jsx` already crashed pre-T201 due to auto-mocking returning `undefined` for `getTicketIntelligence`/`getTicketReadiness`/`getTicketApprovals` (they don't mock those panels' APIs). I confirmed the failure exists with my changes stashed, so this is not a regression. The new panel follows the same pattern as `TicketIntelligencePanel` / `TicketReadinessPanel`, intentionally matching the visual conventions called out in the plan.
