# T211 — Add READY_TO_TAKE eligibility service and unified ticket execution decision

**Source**: GitHub Issue #278

## Description

# Add READY_TO_TAKE eligibility service and unified ticket execution decision

## Context

AI Dev Factory now contains several independent decision systems:

```text
Ticket Intelligence
Ticket Readiness
Execution Rules
Human Approval
```

However, there is currently no single component responsible for answering the most important question:

```text
Can this ticket be taken by a worker?
```

This decision will become the foundation of the future dispatcher and multi-worker scheduler.

## Goal

Introduce a dedicated eligibility service that computes a unified:

```text
READY_TO_TAKE
```

status for every ticket.

The service should explain:

```text
why a ticket can be executed
why a ticket is blocked
what action is required next
```

## Scope

Create a new service:

```text
TicketExecutionEligibilityService
```

that aggregates the existing systems without changing their logic.

The service is read-only.

## Inputs

The service evaluates:

```text
Ticket Intelligence
Ticket Readiness
Rule Evaluation
Human Approval state
Ticket dependencies
Current ticket state
```

## Output

Return a structure similar to:

```json
{
  "ready_to_take": false,
  "status": "BLOCKED",
  "reason": "Human plan approval required",
  "next_action": "Approve plan review",
  "blocking_step": "approval"
}
```

## Example decisions

### Ready

```text
Intelligence completed
Readiness ready_candidate
Rules eligible
Approvals approved
Dependencies satisfied

=> READY_TO_TAKE = true
```

### Blocked by approval

```text
Plan review pending

=> READY_TO_TAKE = false
=> blocking_step = approval
```

### Blocked by dependency

```text
Dependency T001 not merged

=> READY_TO_TAKE = false
=> blocking_step = dependencies
```

## UI

Expose the eligibility result on the Ticket page and integrate it with the workflow timeline introduced in T209.

The UI should clearly display:

```text
READY TO TAKE
BLOCKED
WAITING HUMAN ACTION
DEPENDENCY BLOCKED
```

with the associated reason and next action.

## Non-goals

- No automatic worker assignment.
- No scheduler modifications.
- No dispatcher implementation.
- No automatic ticket start.
- No changes to existing rule engines.

This ticket only centralizes decision making.

## Acceptance criteria

- A dedicated eligibility service exists.
- The service produces a single execution decision for a ticket.
- The service explains why a ticket is blocked.
- The service exposes the next required action.
- Existing Intelligence, Readiness, Rules and Approval logic remain unchanged.
- The workflow timeline displays the eligibility result.
- No scheduler or worker behavior changes are introduced.
- Existing tests continue to pass.
