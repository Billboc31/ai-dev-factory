# Plan review — T201 must target the current repo architecture

The T201 plan is conceptually aligned with the issue: it introduces an advisory Execution Rules Engine, persists rule configuration and evaluations, exposes API/UI, and explicitly avoids changing scheduler, worker dispatch, daemon state, or execution queue behavior.

However, the plan targets stale / incorrect repository paths for the API and frontend.

## Blocking issue 1 — API path is wrong

The plan says:

```text
Wire endpoints into tools/api/
place handlers in tools/api/rules.py
register in tools/api/main.py
```

But the current repository uses the Control API under:

```text
services/control_api/
```

Existing related routes are already registered from:

```text
services/control_api/routes/intelligence.py
services/control_api/routes/readiness.py
services/control_api/routes/approvals.py
```

The new rules route must follow the same structure:

```text
services/control_api/routes/rules.py
services/control_api/main.py
```

## Blocking issue 2 — frontend path is wrong

The plan says:

```text
web/
web/lib/api/rules.ts
web/app/projects/[project_id]/rules/page.tsx
web/components/TicketRuleEvaluation.tsx
```

But the current dashboard is under:

```text
apps/dashboard/
```

The ticket detail page and existing panels live under:

```text
apps/dashboard/src/pages/TicketDetailPage.jsx
apps/dashboard/src/components/TicketIntelligencePanel.jsx
apps/dashboard/src/components/TicketReadinessPanel.jsx
apps/dashboard/src/components/HumanApprovalPanel.jsx
apps/dashboard/src/api/tickets.js
```

The new UI must target this structure, not `web/`.

## Blocking issue 3 — approval state helper should use existing T199 service

The plan correctly says the rules engine should not query the approval table directly.

However, the plan should explicitly use the existing T199 service:

```text
tools/agent_runner/ticket_approval_service.py::compute_execution_eligibility(db_path, ticket_id)
```

This helper already provides the canonical execution eligibility state such as:

```text
ready_candidate
ready_to_take
blocked
not_started
```

The rules engine should import this helper and expose it only through:

```text
get_execution_approval_state(db_path, ticket_id)
```

## Required correction

Update `runs/T201/plan.md` so that:

1. API work is implemented in `services/control_api/routes/rules.py`.
2. Router registration is done in `services/control_api/main.py`.
3. API schemas are added to `services/control_api/models/schemas.py`.
4. Frontend API helpers are added to `apps/dashboard/src/api/tickets.js` or a sibling file already used by the dashboard.
5. Ticket rule evaluation UI is added under `apps/dashboard/src/components/`.
6. The ticket detail page integration targets `apps/dashboard/src/pages/TicketDetailPage.jsx`.
7. If a Project Rules page is included, it must use the current React Router / dashboard structure, not Next.js `web/app` conventions.
8. The rules engine uses `ticket_approval_service.compute_execution_eligibility(...)` and never reads approval tables directly.

## Review verdict

PLAN_FIX_REQUIRED until the plan targets the current `services/control_api` + `apps/dashboard` architecture and the existing T199 approval service helper.
