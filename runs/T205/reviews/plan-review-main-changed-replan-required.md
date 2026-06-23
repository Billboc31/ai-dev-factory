# Plan review — main changed, replan required

The current T205 plan must not be implemented as-is because `main` has changed since the plan was generated.

T205 touches the Ticket Intelligence UI. This area is actively connected to recent work around:

- Ticket Intelligence
- Ticket Readiness
- Human Approval
- Execution Rules
- Ticket Diagnostics
- Ticket Operations
- project-scoped dashboard routes

Because the dashboard and ticket detail page have evolved, the existing plan may be stale and may target outdated component structure, props, API helpers, or layout assumptions.

## Required action

Recalculate the plan from the current `main` before the coder starts.

The planner must re-read the current files from `main`, especially:

```text
apps/dashboard/src/pages/TicketDetailPage.jsx
apps/dashboard/src/components/TicketIntelligencePanel.jsx
apps/dashboard/src/components/TicketReadinessPanel.jsx
apps/dashboard/src/components/HumanApprovalPanel.jsx
apps/dashboard/src/components/TicketRuleEvaluationPanel.jsx
apps/dashboard/src/components/TicketDiagnosticsPanel.jsx
apps/dashboard/src/api/tickets.js
services/control_api/routes/intelligence.py
services/control_api/models/schemas.py
```

If any of these files have moved or changed, the plan must adapt to the current repository structure.

## Product requirement reminder

The goal of T205 is not to remove detail from Ticket Intelligence.

The goal is to make the default UI compact and usable:

```text
show high-value summary first
hide long reasoning by default
allow expansion when needed
```

The compact view should prioritize:

- difficulty score / label
- risk score / label
- recommended model
- estimated cost
- human review requirement
- dependencies / blocking hints
- short summary
- analysis status / last analyzed date

Detailed analysis should be behind an expandable section.

Raw/debug data should be either hidden by default or placed in a secondary advanced section.

## Review verdict

PLAN_FIX_REQUIRED because the plan was generated against stale `main` and must be recalculated before implementation.
