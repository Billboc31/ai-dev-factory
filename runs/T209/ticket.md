# T209 — Add visual ticket workflow timeline with expandable step details

**Source**: GitHub Issue #274

## Description

# Add visual ticket workflow timeline with expandable step details

## Context

The Ticket page has recently gained multiple independent panels:

```text
Ticket Intelligence
Ticket Readiness
Execution Rules
Human Approval
Diagnostics
Operations
```

While technically correct, the current UI is becoming difficult to read and does not clearly communicate the overall ticket lifecycle.

For demos, sales, and day-to-day usage, users should immediately understand:

```text
Where the ticket currently is
Why it is blocked
What the next required action is
Whether the ticket can be taken by a worker
```

## Goal

Replace the current collection of disconnected panels with a visual workflow-oriented experience.

The Ticket page should clearly show the lifecycle progression of a ticket.

## Proposed UX

Display a workflow/timeline at the top of the page:

```text
Intelligence
   ↓
Readiness
   ↓
Rules
   ↓
Human Approval
   ↓
Ready To Take
   ↓
Execution
```

Each step should expose:

```text
status
summary
blocking reason (if any)
next action
```

Example:

```text
[Intelligence]      ✓ Completed
[Readiness]         ✓ Candidate
[Rules]             ✓ Allowed
[Approval]          ⏳ Waiting for plan approval
[Ready To Take]     ✗ Blocked
```

## Global summary

A prominent summary section should display:

```text
Ticket status: BLOCKED
Reason: Human plan approval required
Next action: Approve plan review
```

or:

```text
Ticket status: READY TO TAKE
Reason: All checks passed
Next action: Assign worker
```

## Important requirement

The new workflow UI must NOT remove access to detailed information.

Every workflow step must remain expandable.

Users must still be able to inspect the full details currently provided by the existing panels.

Suggested behavior:

```text
Workflow step
↓
Compact summary visible by default
↓
Expand
↓
Full existing panel/details
```

Examples:

```text
[Intelligence]
Difficulty: 7/10
Risk: Medium
Model: GPT-5.5

[Show details]
```

expands into:

```text
Detailed analysis
Reasoning
Signals
Raw intelligence
```

## Scope

Likely affected areas:

```text
apps/dashboard/src/pages/TicketDetailPage.jsx
apps/dashboard/src/components/TicketIntelligencePanel.jsx
apps/dashboard/src/components/TicketReadinessPanel.jsx
apps/dashboard/src/components/TicketRuleEvaluationPanel.jsx
apps/dashboard/src/components/HumanApprovalPanel.jsx
apps/dashboard/src/components/TicketDiagnosticsPanel.jsx
apps/dashboard/src/components/TicketOperationsPanel.jsx
```

A new reusable component may be introduced:

```text
TicketWorkflowTimeline
TicketWorkflowStep
```

## Non-goals

- No change to business logic.
- No change to dispatcher behavior.
- No change to readiness evaluation.
- No new backend endpoints.
- No modification of scheduler/worker logic.

This is a UI/UX improvement only.

## Acceptance criteria

- The Ticket page displays a visual workflow/timeline.
- Users can immediately identify where the ticket is blocked.
- A global summary displays current status, blocking reason, and next action.
- Every workflow step exposes a compact summary.
- Every workflow step can be expanded to reveal the existing detailed information.
- Existing detailed panels remain accessible.
- No business logic changes are introduced.
- Existing tests continue to pass.
- The new UI significantly improves demo/readability value.
