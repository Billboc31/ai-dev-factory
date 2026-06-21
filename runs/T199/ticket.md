# T199 — Add Human Approval Workflow and READY_TO_TAKE lifecycle

**Source**: GitHub Issue #255

## Description

# Add Human Approval Workflow and READY_TO_TAKE lifecycle

## Context

AI Dev Factory now provides:

```text
Ticket Intelligence
↓
Ticket Readiness Evaluation
```

A ticket can now become:

```text
ready_candidate
blocked
```

However, the system still lacks an explicit human approval workflow before a ticket is allowed to enter execution.

We want to introduce a dedicated human validation step.

The objective is to allow humans to decide which tickets may actually be executed by AI agents.

## Goal

Introduce a human approval workflow and a new lifecycle state:

```text
ready_to_take
```

Workflow:

```text
Ticket created
↓
Ticket Intelligence
↓
Ticket Readiness Evaluation
↓
READY_CANDIDATE
↓
Human approval
↓
READY_TO_TAKE
```

Only READY_TO_TAKE tickets will eventually be eligible for automatic execution.

Execution behavior itself is not implemented in this ticket.

## Non-goals

Do not:

- modify scheduler behavior
- automatically start execution
- dispatch workers
- enforce execution rules
- automatically approve tickets
- implement parallel execution

This ticket only introduces the approval workflow.

## Database

Create a new table:

```text
ticket_approvals
```

Suggested columns:

```text
id
project_id
ticket_id
approval_type
approval_status
approved_by
approval_comment
approved_at
created_at
updated_at
```

Canonical statuses:

```text
pending
approved
rejected
```

Approval types:

```text
execution
plan
code
```

For this ticket only `execution` approval is required.

## Ticket lifecycle additions

Introduce new ticket lifecycle state:

```text
ready_to_take
```

Rules:

```text
ready_candidate
+ execution approval approved
→ ready_to_take
```

Otherwise:

```text
ready_candidate
+ no approval
→ remains ready_candidate
```

Rejected approval:

```text
approval_status = rejected
```

must return the ticket to:

```text
blocked
```

with a visible reason.

## Approval service

Create:

```text
tools/agent_runner/ticket_approval_service.py
```

Responsibilities:

- create approval requests
- approve tickets
- reject tickets
- retrieve approval history
- compute effective execution eligibility

Suggested API:

```python
request_execution_approval(...)
approve_execution(...)
reject_execution(...)
get_ticket_approvals(...)
```

## API

Add endpoints:

```text
GET /tickets/{ticket_id}/approvals
POST /tickets/{ticket_id}/approve-execution
POST /tickets/{ticket_id}/reject-execution
```

Approval endpoints should:

- verify ticket currently has `ready_candidate`
- persist approval record
- update effective readiness state

## Frontend

Add a new section on the ticket page:

```text
Human Approval
```

Display:

- approval status
- approval history
- approver
- approval date
- comments

Buttons:

```text
Approve for execution
Reject execution
```

Buttons are enabled only when:

```text
readiness_status == ready_candidate
```

## Board UI

Display clear badges:

```text
READY CANDIDATE
READY TO TAKE
BLOCKED
```

Add filtering by approval state.

## Audit requirements

All approvals and rejections must be persisted.

Nothing should be overwritten.

Approval history must remain visible.

Example:

```text
2026-06-21
Pierre
Approved execution
Comment: Safe backend-only ticket
```

## Acceptance criteria

- Tickets may be approved or rejected for execution.
- Approval history is persisted.
- READY_TO_TAKE lifecycle state exists.
- Only READY_CANDIDATE tickets can be approved.
- Rejected approvals move the ticket back to BLOCKED.
- API exposes approval history.
- Dashboard exposes approval actions and history.
- Scheduler and worker behavior remain unchanged.
- Existing tests continue to pass.
