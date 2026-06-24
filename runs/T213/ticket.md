# T213 — Fix Ticket Readiness to evaluate only workflow entry prerequisites

**Source**: GitHub Issue #282

## Description

# Fix Ticket Readiness to evaluate only workflow entry prerequisites

## Context

Recent work introduced:

```text
Ticket Intelligence
Ticket Readiness
Execution Rules
Human Approval
Ready To Take
```

The current implementation mixes workflow-entry checks with gates that belong to later execution stages.

Example observed in the UI:

```text
Readiness = BLOCKED
Reason: Human plan approval missing
```

This is incorrect because plan approval occurs only after the planner has executed.

The existing workflow engine already manages:

```text
PLAN_REVIEW_NEEDED
PLAN_APPROVED
PLAN_FIX_REQUIRED
```

Therefore Ticket Readiness should not block execution because a future plan approval has not yet happened.

## Goal

Clarify the responsibility of Ticket Readiness.

Ticket Readiness must answer only:

```text
Can this ticket ENTER the AI workflow now?
```

It must not evaluate gates that belong to later workflow stages.

## New Readiness philosophy

Readiness evaluates only workflow-entry prerequisites.

Examples:

### Valid readiness checks

- dependency tickets completed
- ticket not already running
- ticket not already completed
- ticket description/context sufficiently populated
- project initialized correctly
- required AI project context exists
- project not in a globally blocked state

### Advisory warnings (non-blocking)

Examples:

```text
High implementation risk
Human plan review may be required later
Human execution approval will be required later
```

Warnings must not block readiness.

### Remove from readiness blocking logic

Readiness must no longer block on:

```text
human plan approval missing
human execution approval missing
execution rules evaluation
ready-to-take evaluation
planner review state
```

These concerns are already enforced elsewhere in the workflow.

## Scope

Review and update:

```text
TicketReadinessEvaluator
TicketReadinessService
Readiness UI messaging
```

and any related rules currently producing:

```text
Human plan approval missing
```

inside readiness blockers.

## UI expectations

Examples:

Instead of:

```text
BLOCKED
Reason: Human plan approval missing
```

show:

```text
READY_CANDIDATE
Warnings:
- Human plan review may be required later
```

when all workflow-entry requirements are satisfied.

## Acceptance criteria

- Ticket Readiness evaluates only workflow-entry prerequisites.
- Human plan approval never blocks readiness.
- Human execution approval never blocks readiness.
- Readiness no longer depends on planner review states.
- Readiness may expose non-blocking warnings for future approvals.
- Existing workflow approval mechanisms remain unchanged.
- Existing PLAN_REVIEW_NEEDED / PLAN_APPROVED behavior remains unchanged.
- Timeline UI becomes coherent for both new and completed tickets.
- Existing tests continue to pass and new readiness tests are added where necessary.
