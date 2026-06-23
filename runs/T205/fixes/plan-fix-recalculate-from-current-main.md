# Plan fix — recalculate T205 from current main

## Required plan update

Before coding T205, regenerate `runs/T205/plan.md` from the current `main` branch.

The previous plan is considered stale because `main` changed after it was generated.

Do not patch the old plan incrementally unless the planner first reloads the current repository state and confirms every referenced file and component still exists.

## Files that must be re-read from current main

The corrected plan must inspect the current implementation of:

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

If new panels or components have been added since the original plan, the corrected plan must preserve their order and avoid breaking the ticket detail layout.

## Correct target

T205 should only improve the Ticket Intelligence UI.

It must not modify:

- Ticket Intelligence analyzer logic
- Ticket Readiness logic
- Human Approval logic
- Execution Rules logic
- Ticket Diagnostics logic
- Ticket Operations logic
- scheduler / dispatcher / worker behavior
- database schema unless strictly necessary for display compatibility

## UI behavior expected

The corrected plan should implement a compact-first Ticket Intelligence panel.

Default collapsed/summary view should show:

```text
analysis status
last analyzed date
difficulty score + label
risk score + label
recommended model
estimated cost range
human plan review required yes/no
human code review required yes/no
dependency hints
short analysis summary
```

Long sections should be hidden by default behind expanders such as:

```text
Show details
Show reasoning
Show raw/debug data
```

The UI should remain useful when fields are missing or unknown.

## UX requirements

The default page must be scannable.

Avoid rendering long JSON blobs or long reasoning text by default.

Use concise badges/cards for the summary.

Use expandable sections for:

- complexity factors
- dependency hints
- model reasoning
- cost breakdown
- raw computed signals
- raw AI response / debug data, if currently exposed

## Tests to update/add

The corrected plan should include tests for:

- compact summary renders important fields
- detailed reasoning is hidden by default
- clicking expand shows detailed analysis
- unknown/missing fields do not crash the panel
- existing re-analyze behavior still works
- ticket detail page still renders all existing panels

## Acceptance criteria additions

Add these acceptance criteria to the recalculated plan:

- The plan explicitly states it was recalculated from current `main`.
- The implementation targets the current `apps/dashboard/src/components/TicketIntelligencePanel.jsx` location.
- The Ticket Intelligence panel is compact by default.
- Long detail/reasoning/raw sections are collapsed by default.
- Users can expand details when needed.
- Existing Ticket Detail panels remain mounted and functional.
- No scheduler, dispatcher, worker, readiness, rules, diagnostics, approval, or operations behavior is changed.

## Review verdict after fix

After the plan is regenerated against current `main`, it can be reviewed again for `PLAN_APPROVED`.
