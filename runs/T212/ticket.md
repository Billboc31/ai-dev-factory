# T212 — Add advisory Ticket Dispatcher service with optional integration modes

**Source**: GitHub Issue #280

## Description

# Add advisory Ticket Dispatcher service with optional integration modes

## Context

AI Dev Factory now provides:

```text
Ticket Intelligence
Ticket Readiness
Execution Rules
Human Approval
READY_TO_TAKE Eligibility
```

However, there is still no central component responsible for selecting the next best ticket to execute.

A future multi-worker scheduler will rely on such a component.

## Important constraint

The current ticket execution chain must continue to work unchanged.

The dispatcher must be fully optional and disableable.

When disabled, AI Dev Factory must behave exactly as it does today.

## Goal

Introduce a read-only advisory dispatcher service able to recommend the next ticket(s) to execute.

Initially the dispatcher does not start tickets automatically.

It only recommends execution order.

## Dispatcher modes

Support configurable modes:

```text
off
advisory
manual
auto (future)
```

### off

```text
Current behavior unchanged.
Dispatcher completely ignored.
```

### advisory

```text
Dispatcher computes recommendations only.
No automatic execution.
```

### manual

```text
Dispatcher computes recommendations.
Human may explicitly launch a recommended ticket.
```

### auto

Reserved for future work.
No implementation required in this ticket.

## Service

Create:

```text
TicketDispatcherService
```

Example:

```text
get_recommended_tickets(project_id)
```

Inputs:

```text
Open tickets
READY_TO_TAKE eligibility
Ticket priority
Intelligence score
Queue order
Ticket age
```

Output example:

```json
[
  {
    "ticket_id": "T004",
    "score": 98,
    "rank": 1,
    "reason": "READY_TO_TAKE, high priority, no blockers"
  }
]
```

## UI

Create a dedicated Dispatcher page.

The page should display:

```text
Dispatcher mode
Recommended execution queue
Recommendation score
Recommendation reasons
Blocked tickets
Blocking reasons
```

This page will become the future control center for multi-worker scheduling.

## Non-goals

- No automatic worker assignment.
- No scheduler implementation.
- No automatic ticket execution.
- No daemon changes.
- No multi-worker support.
- No modifications to the existing run ticket workflow.

## Acceptance criteria

- A TicketDispatcherService exists.
- Dispatcher can be disabled.
- When disabled, current behavior is unchanged.
- Advisory recommendations are computed without side effects.
- Dispatcher exposes recommendation reasons.
- A dedicated Dispatcher page exists.
- No worker or scheduler behavior changes are introduced.
- Existing tests continue to pass.
