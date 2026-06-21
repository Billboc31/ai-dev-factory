# T198 — Add Ticket Readiness Evaluator and execution eligibility workflow

**Source**: GitHub Issue #253

## Description

# Add Ticket Readiness Evaluator and execution eligibility workflow

## Context

AI Dev Factory now includes a Ticket Intelligence Analyzer that enriches tickets with advisory metadata.

The next step is to determine whether a ticket is actually eligible to enter the development pipeline.

A dedicated Readiness Evaluator must analyze the current project state and determine if a ticket can be executed.

This component is intentionally separate from Ticket Intelligence.

```text
Ticket Intelligence
= analysis / recommendations

Readiness Evaluator
= execution eligibility decision
```

The goal is to avoid situations where tickets start with stale context, missing approvals, or unresolved dependencies.

## Goals

Introduce a new evaluation step:

```text
Ticket
↓
Ticket Intelligence
↓
Readiness Evaluator
↓
Ready Candidate / Blocked
```

The evaluator decides whether a ticket is:

```text
READY_CANDIDATE
BLOCKED
```

without modifying the existing execution pipeline yet.

For this ticket, the evaluator is advisory only.

## Non-goals

Do not:

- automatically start ticket execution
- modify scheduler behavior
- reorder queues
- dispatch workers
- enforce execution policies
- automatically merge tickets

These behaviors will be implemented later.

## Ticket lifecycle additions

Introduce two new ticket states:

```text
READY_CANDIDATE
BLOCKED
```

A ticket may become READY_CANDIDATE when all readiness checks pass.

A ticket becomes BLOCKED when at least one readiness rule fails.

The evaluator must also expose blocking reasons.

Example:

```text
Status: BLOCKED

Reasons:
- Dependency T001 not merged
- Human plan approval missing
```

## Database

Create a new table:

```text
ticket_readiness
```

Suggested fields:

```text
ticket_id
readiness_status
blocking_reasons_json
warnings_json
dependency_check_status
approval_check_status
context_freshness_status
human_approval_required
human_approval_present
ready_candidate
evaluated_at
created_at
updated_at
```

Only one active readiness evaluation per ticket is required.

## Readiness checks

The evaluator should support the following checks.

### Dependency validation

Detect explicit dependencies:

```text
Depends on T001
After T001
Blocked by T001
```

Verify:

```text
all prerequisite tickets are merged into main
```

If not:

```text
BLOCKED
```

### Human approval validation

Use Ticket Intelligence metadata.

If:

```text
requires_human_plan_review = true
```

then verify approval exists.

If approval is missing:

```text
BLOCKED
```

### Context freshness validation

Store:

```text
main_sha_when_evaluated
```

Future components will compare this against current main.

For this ticket only expose:

```text
fresh
unknown
stale
```

without enforcing execution behavior.

### Intelligence validation

A ticket cannot become READY_CANDIDATE if:

```text
Ticket Intelligence analysis does not exist
```

Example:

```text
BLOCKED
Reason: Missing Ticket Intelligence analysis
```

## Evaluator service

Create:

```text
tools/agent_runner/ticket_readiness_evaluator.py
```

Responsibilities:

1. Load ticket
2. Load Ticket Intelligence result
3. Execute readiness checks
4. Produce structured readiness result
5. Persist result in DB

Suggested output:

```json
{
  "readiness_status": "BLOCKED",
  "ready_candidate": false,
  "blocking_reasons": [
    "Dependency T001 not merged",
    "Human plan approval missing"
  ],
  "warnings": [],
  "dependency_check_status": "failed",
  "approval_check_status": "failed",
  "context_freshness_status": "fresh"
}
```

## API

Add:

```text
GET /api/tickets/{ticket_id}/readiness
POST /api/tickets/{ticket_id}/evaluate-readiness
```

POST should behave similarly to Ticket Intelligence:

```text
returns 202 Accepted
runs in background
```

## Frontend

Add a new panel:

```text
Ticket Readiness
```

Display:

- readiness status
- ready candidate badge
- blocking reasons
- warnings
- last evaluation date
- dependency state
- approval state
- context freshness state

Example:

```text
READY CANDIDATE

No blocking issues detected.
```

or

```text
BLOCKED

- Dependency T001 not merged
- Missing human approval
```

## Human workflow

For now, human users manually decide if a READY_CANDIDATE ticket should later become:

```text
READY_TO_TAKE
```

This ticket does not implement READY_TO_TAKE.

## Acceptance criteria

- Tickets can be evaluated for readiness independently of execution.
- Readiness results are persisted in DB.
- Missing Ticket Intelligence analysis blocks readiness.
- Dependency checks produce blocking reasons.
- Human approval requirements produce blocking reasons.
- API exposes readiness information.
- Dashboard displays readiness status and blocking reasons.
- Existing scheduler and execution behavior remain unchanged.
- Existing test suite continues to pass.
