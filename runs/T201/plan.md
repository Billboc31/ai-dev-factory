## Objective

Introduce a project-level Execution Rules Engine that evaluates configurable policies against a ticket and emits an `eligible` or `blocked` decision with explicit reasons. The engine is advisory: it persists evaluations and exposes them via the existing Control API and dashboard, but it does not start execution, dispatch workers, reserve workers, reorder queues, or change scheduler/daemon behavior.

## Included

### Database

- Extend `tools/agent_runner/runtime_db.py` and `tools/agent_runner/runtime_db_pg.py` to create the table `project_execution_rules` in both the SQLite and PostgreSQL initialisation paths, with columns:
  - `project_id TEXT NOT NULL`
  - `rule_key TEXT NOT NULL`
  - `enabled INTEGER NOT NULL` (boolean in PG)
  - `configuration_json TEXT NOT NULL DEFAULT '{}'` (JSONB in PG)
  - `created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP`
  - `updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP`
  - PRIMARY KEY `(project_id, rule_key)`
- Extend the same modules to create `ticket_rule_evaluation` with columns:
  - `ticket_id TEXT NOT NULL`
  - `project_id TEXT NOT NULL`
  - `eligibility_status TEXT NOT NULL` (`eligible` or `blocked`)
  - `failed_rules_json TEXT NOT NULL DEFAULT '[]'`
  - `passed_rules_json TEXT NOT NULL DEFAULT '[]'`
  - `warnings_json TEXT NOT NULL DEFAULT '[]'`
  - `evaluated_at TEXT NOT NULL`
  - `created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP`
  - `updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP`
  - PRIMARY KEY `(ticket_id)`
- Add to `tools/agent_runner/runtime_db.py` (and PG equivalents in `runtime_db_pg.py`):
  - `list_project_rules(db_path, project_id) -> list[dict]`
  - `upsert_project_rule(db_path, project_id, rule_key, enabled, configuration)` — upserts one row.
  - `replace_project_rules(db_path, project_id, rules: list[dict])` — atomically replaces the project's rule set; used by `PUT /projects/{project_id}/rules`.
  - `get_ticket_rule_evaluation(db_path, ticket_id) -> dict | None`
  - `upsert_ticket_rule_evaluation(db_path, ticket_id, project_id, eligibility_status, passed_rules, failed_rules, warnings, evaluated_at)` — overwrites the row keyed by `ticket_id`.
- All helpers accept both SQLite and PostgreSQL `db_path`/DSN via the existing connection abstraction; JSON columns are read back as Python lists/dicts.

### Rules engine

Create `tools/agent_runner/execution_rules_engine.py` containing:

- A module-level `RULE_REGISTRY: dict[str, RuleSpec]` mapping every supported rule key to a `RuleSpec` dataclass holding:
  - `key: str`
  - `description: str`
  - `default_enabled: bool`
  - `default_configuration: dict`
  - `evaluator: Callable[[RuleContext], RuleResult]`
- A `RuleContext` dataclass exposing the inputs each evaluator may read:
  - `project_id`
  - `ticket_id`
  - `configuration` (the rule's own JSON configuration)
  - `intelligence` (the Ticket Intelligence record, or `None`)
  - `readiness` (the Readiness record, or `None`)
  - `approval_state` (the canonical execution eligibility string returned by `compute_execution_eligibility`)
- A `RuleResult` dataclass: `passed: bool`, `reason: str`, optional `warnings: list[str]`.
- `get_execution_approval_state(db_path, ticket_id) -> str` — wrapper that calls `compute_execution_eligibility(db_path, ticket_id)` imported from `tools/agent_runner/ticket_approval_service.py` and returns the canonical string (`ready_candidate`, `ready_to_take`, `blocked`, `not_started`, etc.). This wrapper is the **only** place in the engine that resolves the approval state. Rule evaluators receive the resulting string through `RuleContext.approval_state`. The file must not import or reference `ticket_approvals` or `approval_status` directly.
- `evaluate_ticket(db_path, project_id, ticket_id) -> dict` that:
  1. Loads project rules via `list_project_rules`. If a registered rule has no row for the project, fall back to its registry defaults (default policy below).
  2. Loads Ticket Intelligence for `ticket_id` from the existing analysis tables.
  3. Loads Readiness state for `ticket_id` from the T199 readiness helpers.
  4. Calls `get_execution_approval_state` once and stores the result in `RuleContext`.
  5. Iterates over the registry; for each enabled rule, runs its evaluator with the populated `RuleContext`.
  6. Aggregates the results into:
     - `passed_rules: list[{"rule_key", "reason"}]`
     - `failed_rules: list[{"rule_key", "reason"}]`
     - `warnings: list[{"rule_key", "message"}]`
  7. Sets `eligibility_status = "blocked"` if any rule failed, otherwise `"eligible"`.
  8. Persists the decision via `upsert_ticket_rule_evaluation` with `evaluated_at = utcnow().isoformat()`.
  9. Returns the dict `{"eligibility_status", "passed_rules", "failed_rules", "warnings", "evaluated_at"}`.

### Supported rules

The engine ships with exactly these six rules registered in `RULE_REGISTRY`:

- `require_ticket_intelligence` — passes when the Ticket Intelligence record exists and `analysis_status == "completed"`. Default `enabled = true`.
- `require_readiness_candidate` — passes when readiness is loaded and `readiness_status == "ready_candidate"` (or any later canonical lifecycle state). Default `enabled = true`.
- `require_human_approval` — passes when `RuleContext.approval_state == "ready_to_take"`. The evaluator MUST read only from `RuleContext.approval_state`; it MUST NOT query the `ticket_approvals` table directly. Default `enabled = true`.
- `block_when_human_review_required` — fails when the Ticket Intelligence flag `requires_human_plan_review` is `true` AND `RuleContext.approval_state != "ready_to_take"`. Default `enabled = true`.
- `max_estimated_cost_usd` — configuration `{"max_cost_usd": float}`. Fails when the ticket's estimated AI cost from intelligence exceeds `max_cost_usd`. Default `enabled = false`, default configuration `{"max_cost_usd": 0.50}`.
- `max_difficulty` — configuration `{"max_difficulty": int}`. Fails when the ticket's difficulty score from intelligence exceeds `max_difficulty`. Default `enabled = false`, default configuration `{"max_difficulty": 7}`.

### Default policy

When `evaluate_ticket` finds no row in `project_execution_rules` for a given `(project_id, rule_key)`, it uses the registry default. The effective default policy is:

```
Default policy enables:
- require_ticket_intelligence
- require_readiness_candidate
- require_human_approval
- block_when_human_review_required

Default policy disables:
- max_estimated_cost_usd
- max_difficulty
```

`PUT /projects/{project_id}/rules` with no body OR with the special action `reset_defaults` resets the project to this exact policy by calling `replace_project_rules` with the registry defaults serialised out.

### Control API

Wire the following endpoints into the existing Control API. Place handlers in `services/control_api/routes/rules.py`, register the router in `services/control_api/main.py` next to the existing `intelligence`, `readiness`, and `approvals` routers, and add request/response schemas to `services/control_api/models/schemas.py`. Follow the conventions established by `services/control_api/routes/intelligence.py`, `routes/readiness.py`, and `routes/approvals.py`.

- `GET /projects/{project_id}/rules` — returns `{"rules": [{"rule_key", "enabled", "configuration", "description", "default_enabled", "default_configuration"}]}`. Rules without a stored row are returned with their registry defaults so the UI always sees the full set.
- `PUT /projects/{project_id}/rules` — body `{"rules": [{"rule_key", "enabled", "configuration"}]}`. Validates that every `rule_key` exists in `RULE_REGISTRY` and that `configuration` matches the rule's schema (e.g. `max_cost_usd` must be a non-negative number). Calls `replace_project_rules`. Returns the updated set in the same shape as the GET.
- `GET /tickets/{ticket_id}/rule-evaluation` — returns the persisted evaluation row (parsed JSON arrays). Returns `404` if none exists.
- `POST /tickets/{ticket_id}/evaluate-rules` — schedules `evaluate_ticket` on a FastAPI `BackgroundTasks` queue and immediately responds with HTTP `202 Accepted` and body `{"status": "scheduled", "ticket_id": ...}`. The background task writes the result via `upsert_ticket_rule_evaluation`; clients poll the GET endpoint to read it.

No changes are made to existing scheduler/queue endpoints.

### Frontend (dashboard)

All UI work targets the existing dashboard under `apps/dashboard/src/` (React + React Router). No file is created under `web/` and no Next.js conventions are used.

- Extend the existing API client at `apps/dashboard/src/api/tickets.js` (or add a sibling file `apps/dashboard/src/api/rules.js` if isolation is preferred) with:
  - `getProjectRules(projectId)`
  - `putProjectRules(projectId, rules)`
  - `getTicketRuleEvaluation(ticketId)`
  - `postEvaluateTicketRules(ticketId)`
- Add a **Project Rules panel** at `apps/dashboard/src/components/ProjectRulesPanel.jsx`:
  - Lists every rule from the registry with its description.
  - Each row has an enable/disable toggle.
  - Threshold rules (`max_estimated_cost_usd`, `max_difficulty`) expose an inline editable numeric field.
  - "Reset to defaults" button calls `PUT` with the default payload.
  - "Save" button calls `PUT` with the current state.
- Add a **Project Rules page** at `apps/dashboard/src/pages/ProjectRulesPage.jsx` that hosts `ProjectRulesPanel` and is wired into the existing React Router route table next to the other project pages.
- Add a **Ticket Rule Evaluation panel** at `apps/dashboard/src/components/TicketRuleEvaluationPanel.jsx`, following the visual conventions of `TicketIntelligencePanel.jsx`, `TicketReadinessPanel.jsx`, and `HumanApprovalPanel.jsx`:
  - Displays `eligibility_status` with a coloured badge (`eligible` = green, `blocked` = red).
  - Lists failed rules with their human-readable reasons.
  - Lists warnings.
  - Shows `evaluated_at` formatted as local datetime.
  - "Re-evaluate" button calls the POST endpoint, then polls the GET endpoint until `evaluated_at` changes.
- Embed `TicketRuleEvaluationPanel` into `apps/dashboard/src/pages/TicketDetailPage.jsx` next to the existing intelligence, readiness, and approval panels.

### Tests

Add the following Python test files under `tests/`:

- `tests/test_execution_rules_db.py` — round-trip persistence on both SQLite and PostgreSQL fixtures: schema creation, upsert/list of project rules, upsert/get of ticket evaluations, JSON columns deserialise to lists.
- `tests/test_execution_rules_engine.py` — for each of the six rules: one case where the rule passes and one where it fails, asserting the reason string. The `require_human_approval` cases must drive the result by setting `RuleContext.approval_state` to `"ready_to_take"` (pass) vs `"ready_candidate"` (fail). The `max_estimated_cost_usd` and `max_difficulty` cases cover both enabled and disabled configurations.
- `tests/test_execution_rules_default_policy.py` — when no rows exist in `project_execution_rules`, `evaluate_ticket` applies the four `require_*` / `block_when_*` rules with `enabled=true` and the two threshold rules with `enabled=false`.
- `tests/test_execution_rules_approval_isolation.py` — static grep test asserting that `tools/agent_runner/execution_rules_engine.py` does NOT contain the substrings `ticket_approvals` or `approval_status` outside of comments. The only allowed approval lookup path is `compute_execution_eligibility` via `get_execution_approval_state`.
- `tests/test_execution_rules_api.py` — FastAPI `TestClient` against `services/control_api/main.py` exercising `GET`/`PUT /projects/{project_id}/rules`, `GET /tickets/{ticket_id}/rule-evaluation`, and `POST /tickets/{ticket_id}/evaluate-rules` (asserting HTTP `202` and eventual persistence after the background task runs).
- `tests/test_execution_rules_pipeline_untouched.py` — asserts via static greps that `tools/agent_runner/run_daemon.py`, `tools/agent_runner/run_ticket.py`, and the scheduler module do not import `execution_rules_engine` and contain no call sites for `evaluate_ticket`.

Add the following frontend tests under `apps/dashboard/tests/` (matching the existing dashboard test setup):

- `apps/dashboard/tests/TicketRuleEvaluationPanel.test.jsx` — renders the panel with eligible/blocked fixtures, asserts the badge colour, failed-rule list, warnings list, and that clicking "Re-evaluate" calls the POST endpoint and re-fetches the GET endpoint.
- `apps/dashboard/tests/ProjectRulesPanel.test.jsx` — renders the panel with a mixed-rules fixture, asserts toggles and numeric inputs render, and that "Save" / "Reset to defaults" call the PUT endpoint with the expected payload.

## Excluded

- Any automatic gating of execution: the scheduler, worker dispatch, queue ordering, and `tools/agent_runner/run_daemon.py` / `tools/agent_runner/run_ticket.py` remain untouched and continue to schedule tickets exactly as before.
- Worker reservation, retry logic, or any change to the existing execution pipeline.
- New rules beyond the six listed above.
- Migration of historical tickets to populate `ticket_rule_evaluation` retroactively.
- Per-user or per-role rule overrides; rules are scoped to `project_id` only.
- Frontend visualisation of rule evaluation history (only the latest evaluation per ticket is stored and displayed).
- Notifications, webhooks, or alerts triggered by `blocked` evaluations.
- Refactors of the T198 Ticket Intelligence schema or the T199 approval lifecycle beyond reading their existing canonical state.
- Any work under `tools/api/` or `web/` — these paths are not used in T201.

## Acceptance criteria

1. Tables `project_execution_rules` and `ticket_rule_evaluation` are created in both SQLite (`tools/agent_runner/runtime_db.py`) and PostgreSQL (`tools/agent_runner/runtime_db_pg.py`) by the runtime DB initialiser, with the columns specified above.
2. Project rules are configurable through `GET` / `PUT /projects/{project_id}/rules` served by `services/control_api/routes/rules.py`, and the stored set is returned merged with registry defaults.
3. `POST /tickets/{ticket_id}/evaluate-rules` returns HTTP `202 Accepted`, runs `evaluate_ticket` asynchronously via FastAPI `BackgroundTasks`, and the resulting row is retrievable via `GET /tickets/{ticket_id}/rule-evaluation`.
4. `evaluate_ticket` returns `eligibility_status = "blocked"` whenever at least one enabled rule fails, and `"eligible"` only when all enabled rules pass.
5. Every failed rule in the persisted evaluation includes a human-readable reason; warnings are persisted in the `warnings_json` column.
6. The `require_human_approval` rule passes if and only if `compute_execution_eligibility(db_path, ticket_id) == "ready_to_take"`, and is wired through `get_execution_approval_state`, which is the sole bridge between the engine and `tools/agent_runner/ticket_approval_service.py`. The static test `tests/test_execution_rules_approval_isolation.py` confirms `execution_rules_engine.py` never references `ticket_approvals` or `approval_status` directly.
7. With no rows in `project_execution_rules`, the default policy enables `require_ticket_intelligence`, `require_readiness_candidate`, `require_human_approval`, `block_when_human_review_required`, and disables `max_estimated_cost_usd` and `max_difficulty`.
8. The threshold rules `max_estimated_cost_usd` and `max_difficulty` block tickets that exceed their configured limits, and are inert when disabled.
9. The Project Rules panel and page (`apps/dashboard/src/components/ProjectRulesPanel.jsx`, `apps/dashboard/src/pages/ProjectRulesPage.jsx`) allow toggling each rule and editing thresholds; the Ticket Rule Evaluation panel (`apps/dashboard/src/components/TicketRuleEvaluationPanel.jsx`) embedded in `apps/dashboard/src/pages/TicketDetailPage.jsx` displays eligibility status, failed rules with reasons, warnings, and evaluation date, and exposes a "Re-evaluate" action.
10. `tools/agent_runner/run_daemon.py`, `tools/agent_runner/run_ticket.py`, and the scheduler module contain no import of `execution_rules_engine` and no behavioural change; this is enforced by `tests/test_execution_rules_pipeline_untouched.py`.
11. No file is created under `tools/api/` and no file is created under `web/` for T201. The new API routes live under `services/control_api/routes/rules.py`, are registered in `services/control_api/main.py`, and their schemas live in `services/control_api/models/schemas.py`. All dashboard work lives under `apps/dashboard/src/`.
12. The full existing test suite continues to pass alongside the new Python tests under `tests/` and the new dashboard tests under `apps/dashboard/tests/`.
