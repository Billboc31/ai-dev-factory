# T204 — T204 - Add Ticket Operations panel for guarded manual recovery actions

**Source**: GitHub Issue #264

## Description

# T204 - Add Ticket Operations panel for guarded manual recovery actions

## Context

AI Dev Factory now has diagnostic capabilities for stuck tickets.

T203 explains why a ticket is stuck and recommends safe recovery actions, but it does not execute those actions.

The next step is to add a dedicated Ticket Operations panel where a human operator can trigger selected manual recovery actions with explicit safeguards.

This is an operator console for recovery, not an automation engine.

## Goal

Add a Ticket Operations panel to the ticket detail page that exposes guarded manual actions for recovering or managing a ticket.

The panel should use diagnostics as input when available and display only relevant actions.

Initial supported actions should be conservative and explicit.

## Non-goals

Do not:

- add automatic recovery
- dispatch new tickets
- change scheduler behavior
- change worker reservation behavior
- introduce parallel execution logic
- auto-delete anything without confirmation
- bypass human approval rules
- merge PRs automatically
- silently reset ticket state

## New concept

Create a service:

```text
tools/agent_runner/ticket_operations.py
```

It should expose guarded operations for a ticket.

Each operation must:

1. validate preconditions
2. return a structured result
3. write an audit log entry if an audit mechanism exists
4. avoid destructive changes unless explicitly confirmed
5. never run automatically

## Operation safety levels

Every operation must have a safety level:

```text
low
medium
high
destructive
```

Rules:

- `low` actions can run after a normal click confirmation.
- `medium` actions require a confirmation modal.
- `high` actions require typing the ticket id.
- `destructive` actions require typing the ticket id and a second explicit confirmation.

## Initial operations

### Re-run advisory analyzers

These actions are safe and should call the existing API/service flows:

```text
rerun_intelligence
rerun_readiness
rerun_rules
rerun_diagnostics
```

They should not mutate ticket execution state.

### Approval actions

Expose existing human approval actions:

```text
approve_execution
reject_execution
```

They must use the existing Human Approval Workflow and must not duplicate approval logic.

### Mark ticket blocked

Action:

```text
mark_blocked
```

Purpose:

Allow a human to mark a ticket as blocked with a reason.

Requirements:

- requires reason text
- appends or persists the blocking reason
- does not delete worktree
- does not cancel runs unless a separate action is explicitly triggered

### Reset ticket to planning

Action:

```text
reset_to_planning
```

Purpose:

Recover from a bad/stale/invalid plan.

Requirements:

- high safety level
- requires typed ticket id
- must preserve previous artifacts in an archive/history folder if possible
- must record why the reset happened
- must not delete the worktree by default
- must not run the planner automatically

### Reset ticket to coding

Action:

```text
reset_to_coding
```

Purpose:

Recover when implementation needs to be regenerated but the plan is still valid.

Requirements:

- high safety level
- requires typed ticket id
- must preserve previous code/review/test artifacts where possible
- must not delete plan artifacts
- must not run the coder automatically

### Clear stuck transient state

Action:

```text
clear_stuck_state
```

Purpose:

Clear stale transient runtime markers when no active worker/daemon is actually running.

Requirements:

- medium or high safety level depending on existing state
- must verify no active process/worker heartbeat exists before clearing
- must not touch artifacts or worktree
- must record what was cleared

### Delete ticket worktree

Action:

```text
delete_worktree
```

Purpose:

Remove a broken ticket worktree after a ticket is cancelled, reset, archived, or confirmed stuck.

Requirements:

- destructive safety level
- requires typed ticket id
- requires explicit confirmation
- refuses to run if a worker is active or if the worktree has uncommitted changes unless force is explicitly confirmed
- must never delete outside the configured worktrees root
- must record deleted path

### Archive ticket

Action:

```text
archive_ticket
```

Purpose:

Move a ticket out of the active workflow without deleting data.

Requirements:

- medium safety level
- requires reason text
- must preserve all artifacts
- should mark the ticket as archived/cancelled using existing board conventions if available

## API

Add Control API endpoints:

```text
GET /tickets/{ticket_id}/operations
POST /tickets/{ticket_id}/operations/{operation_key}
```

Project-scoped variants:

```text
GET /projects/{project_id}/tickets/{ticket_id}/operations
POST /projects/{project_id}/tickets/{ticket_id}/operations/{operation_key}
```

`GET` returns available operations for the current ticket:

```json
{
  "ticket_id": "T204",
  "operations": [
    {
      "operation_key": "rerun_diagnostics",
      "label": "Re-run diagnostics",
      "safety_level": "low",
      "enabled": true,
      "disabled_reason": null,
      "requires_reason": false,
      "requires_typed_ticket_id": false,
      "requires_double_confirmation": false
    }
  ]
}
```

`POST` executes one operation after validating confirmation payload.

Suggested request:

```json
{
  "reason": "Plan is stale after main changed",
  "typed_ticket_id": "T204",
  "confirm": true,
  "force": false
}
```

Suggested response:

```json
{
  "ticket_id": "T204",
  "operation_key": "reset_to_planning",
  "status": "completed",
  "message": "Ticket reset to planning and previous artifacts archived.",
  "details": {}
}
```

## Database / audit

Prefer using an existing audit log if available.

If no generic audit mechanism exists, add a lightweight table:

```text
ticket_operation_audit
```

Suggested fields:

```text
id
ticket_id
project_id
operation_key
status
reason
requested_by
details_json
created_at
```

Every operation attempt should be recorded, including rejected attempts.

## Frontend

Add a panel:

```text
Ticket Operations
```

Location:

```text
apps/dashboard/src/pages/TicketDetailPage.jsx
```

Suggested component:

```text
apps/dashboard/src/components/TicketOperationsPanel.jsx
```

Display:

- operation groups:
  - Advisory re-runs
  - Approval actions
  - Recovery actions
  - Dangerous actions
- enabled/disabled state
- disabled reason
- safety level badge
- confirmation modal
- reason input when required
- typed ticket id confirmation when required
- operation result message

If T203 diagnostics are available, display a small hint:

```text
Recommended by diagnostics
```

next to actions matching `recommended_actions`.

## Safety requirements

The operations service must be defensive.

It must:

- never delete outside the configured project/worktree roots
- verify paths with resolved absolute paths before deleting
- refuse destructive actions while a worker heartbeat is active
- require explicit confirmation payload for high/destructive actions
- record every attempted operation
- return clear errors instead of partially mutating state

## Tests

Add tests for:

- available operations API
- confirmation validation
- safety-level requirements
- rerun diagnostics operation
- approval operations delegate to existing approval service
- reset to planning preserves previous artifacts or records why it cannot
- clear stuck state refuses when active heartbeat exists
- delete worktree refuses outside worktrees root
- delete worktree refuses dirty worktree unless force confirmed
- archive ticket preserves artifacts
- audit log records successful and rejected operations
- UI renders operations grouped by safety level
- UI requires typed ticket id for high/destructive actions

## Acceptance criteria

- Ticket detail page displays a Ticket Operations panel.
- Available operations are returned by API with safety metadata.
- Low-risk advisory re-run operations can be triggered manually.
- Approval actions reuse the existing approval workflow.
- Recovery actions validate preconditions and confirmation requirements.
- Destructive actions are guarded by typed ticket id and explicit confirmation.
- Every operation attempt is audited.
- No operation runs automatically.
- Scheduler, dispatcher, worker allocation, and parallel execution remain unchanged.
- Existing tests continue to pass.
