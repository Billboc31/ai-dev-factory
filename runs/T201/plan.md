## Objective

Introduce a project-level Execution Rules Engine that evaluates whether a ticket is eligible to proceed through the autonomous factory, based on configurable per-project policies. The engine is advisory: it persists explained decisions (ELIGIBLE / BLOCKED) but does not schedule, dispatch, or execute work.

## Included

**Database schema** (declared inline in `tools/agent_runner/runtime_db.py` and `tools/agent_runner/runtime_db_pg.py`, mirroring T197–T199 conventions):
- `project_execution_rules` — columns: `project_id`, `rule_key`, `enabled`, `configuration_json`, `created_at`, `updated_at` (PK `(project_id, rule_key)`).
- `ticket_rule_evaluation` — columns: `project_id`, `ticket_id`, `eligibility_status` (`eligible|blocked|failed`), `failed_rules_json`, `passed_rules_json`, `warnings_json`, `evaluated_at`, `created_at`, `updated_at` (PK `(project_id, ticket_id)`).
- Accessor helpers in `runtime_db.py`: `get_project_rules`, `upsert_project_rule`, `get_ticket_rule_evaluation`, `upsert_ticket_rule_evaluation` — and their PostgreSQL counterparts.

**Rules engine module** — new file `tools/agent_runner/execution_rules_engine.py`:
- `RULE_REGISTRY` mapping `rule_key` → evaluator callable. Initial rules:
  - `require_readiness_candidate` (reads `ticket_readiness.readiness_status == ready_candidate`)
  - `require_human_approval` (reads latest `ticket_approvals.approval_status == approved` for type `execution`, surfaced via T199 lifecycle as `ready_to_take`)
  - `require_ticket_intelligence` (reads `ticket_intelligence.analysis_status == completed`)
  - `max_estimated_cost_usd` (compares `ticket_intelligence.estimated_cost_max` to threshold)
  - `max_difficulty` (compares `ticket_intelligence.difficulty_score` to threshold)
  - `block_when_human_review_required` (blocks when `ticket_intelligence.requires_human_plan_review` is true and no execution approval exists)
- `evaluate_ticket(project_id, ticket_id)` — loads project rules, loads intelligence/readiness/approval state via existing `runtime_db` helpers, runs only enabled rules, returns a dict `{eligibility_status, failed_rules, passed_rules, warnings}` with per-rule human-readable reasons, and persists via `upsert_ticket_rule_evaluation`.
- Default project policy (returned when `project_execution_rules` is empty for a project): all four `require_*` rules enabled; thresholds disabled.

**API routes** — new file `services/control_api/routes/execution_rules.py`, registered in the FastAPI app:
- `GET /projects/{project_id}/rules` — returns the list of configured (or default) rules.
- `PUT /projects/{project_id}/rules` — accepts a list of `{rule_key, enabled, configuration}` entries, upserts each row.
- `GET /tickets/{ticket_id}/rule-evaluation` — returns the persisted evaluation (or `404` if none).
- `POST /tickets/{ticket_id}/evaluate-rules` — returns `202 Accepted`, spawns a `threading.Thread` running `execution_rules_engine.evaluate_ticket`, mirroring the dispatch pattern used in `services/control_api/routes/readiness.py`.
- Pydantic models added to `services/control_api/models/schemas.py` (`ProjectRule`, `ProjectRulesPayload`, `RuleEvaluationResponse`, `RuleEvaluationQueued`).

**Frontend** (React + Vite under `apps/dashboard/`):
- New page `src/pages/ProjectRulesPage.jsx` listing rules with enable/disable toggles and threshold inputs; uses a new API helper `src/api/projectRules.js`.
- New component `src/components/TicketRuleEvaluationPanel.jsx` integrated into `TicketDetailPage.jsx`, displaying `eligibility_status`, failed rules with reasons, warnings, and `evaluated_at`. Reuses `hooks/usePolling.js` while the evaluation is queued.

**Tests** (under `tests/`, mirroring T197–T199 layout):
- `test_execution_rules_db.py` — schema, upsert, fetch, JSON round-trip.
- `test_execution_rules_engine.py` — each rule evaluated in isolation, default-policy fallback, eligibility aggregation, persisted evaluation shape, missing intelligence/readiness handled gracefully.
- `test_execution_rules_api.py` — GET/PUT rules, GET evaluation, POST returns `202` and persists asynchronously.

## Excluded

- Any change to the scheduler, worker dispatch, queue ordering, or `run_ticket.py` lifecycle — the engine remains advisory.
- Automatic re-evaluation triggers (cron, on-state-change hooks). Evaluation is only invoked explicitly via the POST endpoint in this ticket.
- New rule types beyond the six listed above (custom DSL, regex on labels, time windows, etc.) — extension is left to follow-up tickets via `RULE_REGISTRY`.
- Versioning or audit history of rule edits (the table records the current configuration only; the `ticket_rule_evaluation` table is point-in-time, not append-only).
- Multi-project UI navigation overhaul; the Project Rules page is reachable from the existing project context, no global redesign.
- Authentication or RBAC on the new endpoints (consistent with current API surface).

## Acceptance criteria

- `project_execution_rules` and `ticket_rule_evaluation` tables are created on first run in both SQLite and PostgreSQL backends; existing data is preserved.
- `GET /projects/{project_id}/rules` returns the default policy when no rows exist, and the persisted rows otherwise; `PUT` round-trips a configuration without data loss.
- `POST /tickets/{ticket_id}/evaluate-rules` returns `202 Accepted`; a subsequent `GET /tickets/{ticket_id}/rule-evaluation` returns the persisted decision with `failed_rules`, `passed_rules`, and `warnings` populated.
- Every entry in `failed_rules_json` includes a non-empty human-readable `reason`; `eligibility_status` is `blocked` whenever `failed_rules` is non-empty and `eligible` otherwise.
- Disabling a rule via `PUT` causes the next evaluation to skip it (rule absent from both `passed_rules` and `failed_rules`).
- The Project Rules page renders the configured rules, allows toggling and editing thresholds, and persists changes via the API.
- The Ticket Rule Evaluation panel displays the current decision and refreshes after a triggered evaluation.
- `pytest tests/test_execution_rules_db.py tests/test_execution_rules_engine.py tests/test_execution_rules_api.py` passes; the full existing test suite continues to pass.
- No file under `tools/agent_runner/run_ticket.py` or the scheduler is modified.
