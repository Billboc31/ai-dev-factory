# T200 — Add Human Approval Workflow and READY_TO_TAKE lifecycle

**Source**: GitHub Issue #256

## Description

# Add Human Approval Workflow and READY_TO_TAKE lifecycle

## Context

AI Dev Factory now has:

- Ticket Intelligence Analyzer
- Ticket Readiness Evaluator

The next step is to introduce a human approval workflow before tickets are allowed to enter execution.

The goal is to let users decide which tickets may actually be executed while keeping the current scheduler and execution pipeline unchanged.

This introduces a distinction between:

```text
READY_CANDIDATE
```

and:

```text
READY_TO_TAKE
```

A ticket may be technically ready but still require a human decision.

## Goals

Introduce a human approval workflow that allows:

- approving a ticket for execution
- revoking approval
- tracking approval history
- displaying approval status on the dashboard

This ticket does not start execution automatically.

## Lifecycle

New state:

```text
READY_TO_TAKE
```

Proposed lifecycle:

```text
Draft
↓
Ticket Intelligence
↓
Readiness Evaluator
↓
READY_CANDIDATE
↓
Human Approval
↓
READY_TO_TAKE
↓
Future Dispatcher
```

A ticket cannot become READY_TO_TAKE unless:

```text
readiness_status == ready_candidate
```

## Non-goals

Do not:

- automatically start execution
- modify worker scheduling
- dispatch tickets
- reorder queues
- implement reservation logic
- implement stale context checks
- automatically approve tickets

Those behaviors will come later.

## Database

Create:

```text
ticket_approval
```

Suggested fields:

```text
ticket_id
approval_status
approved_by
approved_at
revoked_by
revoked_at
approval_reason
created_at
updated_at
```

Suggested statuses:

```text
not_requested
ready_candidate
ready_to_take
revoked
```

Only one active approval row is required for now.

## Approval history

Create:

```text
ticket_approval_history
```

Suggested fields:

```text
id
ticket_id
action
actor
reason
created_at
```

Actions:

```text
approved
revoked
reapproved
```

## API

Add:

```text
GET /tickets/{ticket_id}/approval
POST /tickets/{ticket_id}/approve
POST /tickets/{ticket_id}/revoke-approval
```

Rules:

- approve returns 409 if ticket is not `ready_candidate`
- approving twice is idempotent
- revoking twice is idempotent

## Frontend

Add a new panel:

```text
Ticket Approval
```

Display:

- current approval status
- approver
- approval date
- reason
- history

Actions:

```text
Approve For Execution
Revoke Approval
```

When approved, display:

```text
READY TO TAKE
```

badge.

## Human workflow

This workflow is intentionally manual.

Future versions may allow:

- automatic approval policies
- low-risk ticket auto-approval
- rule-based approvals

Those are excluded from this ticket.

## Acceptance criteria

- Tickets can be approved only when `readiness_status == ready_candidate`.
- Approval status is persisted.
- Approval history is persisted.
- Approving twice is idempotent.
- Revoking twice is idempotent.
- Dashboard displays approval information and history.
- `READY_TO_TAKE` badge is visible when approved.
- Existing scheduler and execution pipeline remain unchanged.
- No ticket execution starts automatically.
- Existing test suite continues to pass.
