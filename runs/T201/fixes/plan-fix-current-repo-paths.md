# Plan fix — target current Control API and dashboard paths

## Required plan update

Update `runs/T201/plan.md` before starting implementation.

The current plan is conceptually correct, but it references stale paths from an older architecture:

```text
tools/api/
web/
```

These paths must not be used for T201.

## Correct backend/API paths

Replace:

```text
tools/api/rules.py
tools/api/main.py
```

with:

```text
services/control_api/routes/rules.py
services/control_api/main.py
services/control_api/models/schemas.py
```

The new routes must follow the same style as the existing routes:

```text
services/control_api/routes/intelligence.py
services/control_api/routes/readiness.py
services/control_api/routes/approvals.py
```

Register the new router in `services/control_api/main.py` next to the existing `intelligence`, `readiness`, and `approvals` routers.

## Correct frontend paths

Replace all `web/` / Next.js references with the current dashboard structure:

```text
apps/dashboard/src/
```

Use paths like:

```text
apps/dashboard/src/api/tickets.js
apps/dashboard/src/components/TicketRuleEvaluationPanel.jsx
apps/dashboard/src/pages/TicketDetailPage.jsx
```

If a project-level rules page is implemented in this ticket, it must use the current React Router / dashboard conventions already present in `apps/dashboard`, not `web/app/...` or Next.js conventions.

Possible page/component names:

```text
apps/dashboard/src/pages/ProjectRulesPage.jsx
apps/dashboard/src/components/ProjectRulesPanel.jsx
```

The exact names may vary, but the implementation must remain inside `apps/dashboard/src`.

## Existing approval service to use

The rules engine must not query `ticket_approvals` directly.

It must use the existing helper introduced by the Human Approval Workflow:

```python
from ticket_approval_service import compute_execution_eligibility
```

Then wrap it in:

```python
def get_execution_approval_state(db_path, ticket_id) -> str:
    return compute_execution_eligibility(db_path, ticket_id)
```

Rules receive this value through `RuleContext.approval_state`.

The following must remain true:

```text
execution_rules_engine.py must not query approval tables directly
execution_rules_engine.py must not inspect ticket_approvals directly
execution_rules_engine.py must not duplicate approval lifecycle logic
```

## Updated implementation targets

Backend:

```text
tools/agent_runner/execution_rules_engine.py
tools/agent_runner/runtime_db.py
tools/agent_runner/runtime_db_pg.py
services/control_api/routes/rules.py
services/control_api/models/schemas.py
services/control_api/main.py
```

Frontend:

```text
apps/dashboard/src/api/tickets.js
apps/dashboard/src/components/TicketRuleEvaluationPanel.jsx
apps/dashboard/src/components/ProjectRulesPanel.jsx
apps/dashboard/src/pages/TicketDetailPage.jsx
```

Optional if routing is straightforward in the current dashboard:

```text
apps/dashboard/src/pages/ProjectRulesPage.jsx
```

Tests:

```text
tests/test_execution_rules_db.py
tests/test_execution_rules_engine.py
tests/test_execution_rules_default_policy.py
tests/test_execution_rules_approval_isolation.py
tests/test_execution_rules_api.py
tests/test_execution_rules_pipeline_untouched.py
apps/dashboard/tests/TicketRuleEvaluationPanel.test.jsx
apps/dashboard/tests/ProjectRulesPanel.test.jsx
```

## Acceptance criteria additions

Add these acceptance criteria to the corrected plan:

- No files are created under `tools/api/` for T201.
- No files are created under `web/` for T201.
- API routes live under `services/control_api/routes/rules.py` and are registered in `services/control_api/main.py`.
- API schemas live in `services/control_api/models/schemas.py`.
- Dashboard work lives under `apps/dashboard/src`.
- Rules engine approval state uses `ticket_approval_service.compute_execution_eligibility(...)` through a wrapper and does not read approval tables directly.
- Scheduler, daemon, run-ticket, worker dispatch, and queue code remain untouched.

## Non-goals reminder

Do not implement:

- automatic dispatch
- worker reservation
- scheduler gating
- queue ordering
- daemon behavior changes
- historical rule evaluation history

The Execution Rules Engine remains advisory only in T201.
