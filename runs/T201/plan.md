Plan replaced. `runs/T201/plan.md` is now the actual implementation plan: the four mandatory headings (`## Objective`, `## Included`, `## Excluded`, `## Acceptance criteria`), no narrative or past-tense report.

Concrete content, grounded in the real repo:

- **DDL** for both SQLite (`runtime_db.py`) and Postgres (`runtime_db_pg.py`) backends, with helper-function signatures matching the existing `upsert_*`/`get_*`/`list_*` conventions.
- **Engine surface** in `tools/agent_runner/execution_rules_engine.py` — full Python signatures for `DEFAULT_RULES`, `ensure_default_project_rules`, `list_effective_rules`, `get_execution_approval_state`, `evaluate_ticket`, `run_evaluation`.
- **`DEFAULT_RULES` given as a literal** with the 4 enabled + 2 disabled split spelled out, and a table mapping each `rule_key` to its pass condition.
- **`require_human_approval` pinned to `compute_execution_eligibility(...) == "ready_to_take"`** via the `get_execution_approval_state` wrapper; criterion #3 plus a grep assertion forbids any other access to `ticket_approvals` from the engine.
- **API** routes table — verbs, paths, response models, status codes (202 for evaluate, 503 on DB down), routers mirror `readiness.py`'s dual `router`/`project_router` pattern.
- **Pydantic models** added to `services/control_api/models/schemas.py`.
- **Frontend** — new `TicketRuleEvaluationPanel.jsx` (mounted on `TicketDetailPage.jsx`) and `ProjectRulesPage.jsx`, plus the four new methods to add to `apps/dashboard/src/api/tickets.js`.
- **Three test files** with explicit per-scenario coverage, following the `_isolate_env`/`_make_app`/`_make_ticket` fixture pattern of `test_ticket_readiness_api.py`.
- **Scheduler isolation** — `## Excluded` names the specific files that must not change; criterion #10 is a `git diff` check.
