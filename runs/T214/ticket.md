# T214 — Simplify Ticket Workflow by removing Rules as a ticket gate and defer policy enforcement to Dispatcher

**Source**: GitHub Issue #284

## Description

# Simplify Ticket Workflow by removing Rules as a ticket gate and defer policy enforcement to Dispatcher

## Context

Recent work introduced the following workflow timeline:

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

During integration testing it became clear that the current `Rules` step duplicates concerns already handled by:

- Ticket Readiness
- Human Approval
- Future Dispatcher
- Workflow engine

Examples of problematic rules:

```text
require_ticket_intelligence
require_readiness_candidate
require_human_approval
block_when_human_review_required
```

These rules create overlapping responsibilities and confusing UI states.

Example:

```text
Readiness = READY_CANDIDATE
Rules = BLOCKED
Human Approval = CURRENT
```

This makes the workflow difficult to understand.

## Goal

Simplify the ticket workflow.

Remove `Rules` as a visible workflow gate and defer policy enforcement to the future Dispatcher.

The ticket workflow should become:

```text
Intelligence
↓
Readiness
↓
Human Approval
↓
Ready To Take
↓
Execution
```

## Scope

### Ticket timeline

Remove the `Rules` step from:

```text
TicketWorkflowTimeline
TicketWorkflowStatus
```

The timeline must no longer display:

```text
Rules BLOCKED
Rules PASSED
```

## Project Rules panel

Temporarily remove or hide the Project Rules panel/UI.

The current rules configuration will be redesigned later as part of the Dispatcher configuration experience.

## Rules engine

Keep the existing code in place if useful, but:

```text
- stop using it as a ticket workflow gate
- stop surfacing rule failures in the ticket timeline
- stop coupling it to Ready To Take computation
```

No business logic migration is required.

## Future direction

Policy evaluation will later be owned by:

```text
Dispatcher Policy Configuration
Dispatcher Eligibility Engine
Dispatcher Scheduler
```

Examples of future dispatcher policies:

```text
require intelligence
require readiness
require human approval
max difficulty
max estimated cost
allowed labels
blocked labels
parallel execution policies
```

## Non-goals

- Do not implement Dispatcher policies in this ticket.
- Do not remove the workflow engine.
- Do not redesign Ready To Take.
- Do not delete Rules code permanently.

## Acceptance criteria

- The ticket workflow timeline no longer contains a Rules step.
- The workflow becomes:
  Intelligence → Readiness → Human Approval → Ready To Take → Execution.
- The Project Rules panel is removed or hidden.
- Rule failures are no longer displayed in ticket pages.
- Existing ticket workflow behavior continues to work.
- Rules code may remain internally but no longer gates ticket progression.
- Existing tests are updated accordingly.
- The UI becomes simpler and easier to understand.
