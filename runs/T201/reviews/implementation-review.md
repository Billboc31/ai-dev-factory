All 4 plan-documented endpoints are registered, plus the optional project-scoped mounts.

# Review — T201 (Execution Rules Engine)

## Scope compliance ✅

The implementation matches the approved plan exactly. No scope creep:
- Engine is advisory only — verified by `tests/test_execution_rules_pipeline_untouched.py` and confirmed via `git diff` and grep on `tools/agent_runner/run_daemon.py`, `run_ticket.py`, `run_step.py` (none modified, no imports of `execution_rules_engine`).
- No work under `tools/api/` or `web/`.
- All dashboard work under `apps/dashboard/src/` with React Router.

## Correctness ✅

**DB layer** (`tools/agent_runner/runtime_db.py` + `runtime_db_pg.py`)
- Both tables created with the documented columns and PK `(project_id, rule_key)` / `(ticket_id)`.
- Helpers `list_project_rules`, `upsert_project_rule`, `replace_project_rules` (atomic BEGIN/COMMIT/ROLLBACK), `get_ticket_rule_evaluation`, `upsert_ticket_rule_evaluation` are present in both backends and rebound under `RUNTIME_DB_BACKEND=postgres` (`runtime_db.py:869-873`).
- JSON columns decode back to Python lists/dicts.

**Engine** (`tools/agent_runner/execution_rules_engine.py`)
- `RuleSpec`/`RuleContext`/`RuleResult` dataclasses, six rules registered exactly as specified.
- `get_execution_approval_state` is the sole bridge to `ticket_approval_service.compute_execution_eligibility` (line 266-269). Static test `test_execution_rules_approval_isolation.py` enforces this.
- Default policy: 4 `require_*`/`block_*` enabled, 2 thresholds disabled — verified in `test_execution_rules_default_policy.py`.
- `evaluate_ticket` loads intelligence/readiness, calls approval bridge once, evaluates only enabled rules, persists, returns the expected dict.

**API** (`services/control_api/routes/rules.py`)
- All 4 documented endpoints registered + project-scoped mounts (verified by listing routes).
- `PUT` validates unknown rule keys (422), duplicates (422), negative cost/difficulty (422).
- `POST /tickets/{id}/evaluate-rules` returns HTTP 202 with `{"status": "scheduled", "ticket_id"}` via FastAPI `BackgroundTasks`.
- Reset-to-defaults via empty body or `action: "reset_defaults"`.

**Frontend**
- `ProjectRulesPanel.jsx`, `TicketRuleEvaluationPanel.jsx`, `ProjectRulesPage.jsx` follow the visual conventions of existing panels.
- Route `/projects/:projectId/rules` registered in `App.jsx:92`.
- `TicketRuleEvaluationPanel` embedded in `TicketDetailPage.jsx:281` next to the other panels.
- Re-evaluate polls (1.5 s × 20 attempts) until `evaluated_at` changes, with `clearTimeout` cleanup.

## Tests ✅

Verified locally:
- **53 Python tests pass** (`test_execution_rules_{engine,db,default_policy,approval_isolation,pipeline_untouched,api}.py`) in 1.35 s.
- **15 dashboard tests pass** (`ProjectRulesPanel.test.jsx`, `TicketRuleEvaluationPanel.test.jsx`) in 2.19 s.

## Quality observations (non-blocking)

1. Minor duplication: `_resolve_effective_rules` in `execution_rules_engine.py:274` and `_get_effective_rules` in `routes/rules.py:113` do the same job. Could be deduplicated.
2. `evaluate_ticket_rules`' fallback project-id resolution (`existing.evaluation → handle.project_id → "default"`) is pragmatic but slightly ad-hoc — the project-scoped POST route is what the dashboard uses, so this is acceptable.
3. `ticket_rule_evaluation` in Postgres keys on `ticket_id` alone (no `project_id`), unlike other PG tables which are composite-keyed. This follows the plan literally; worth flagging only because it diverges from the rest of the PG schema's project-scoping pattern.

## Security/safety ✅

- No secrets logged; no destructive operations.
- Validation at API boundary (rule key, negative numeric inputs).
- Engine is advisory: no implicit execution gating, no scheduler change.

---

IMPLEMENTATION_APPROVED
