# Plan fix — make execution approval and rejection idempotent

## Required plan update

Update `runs/T199/plan.md` before starting implementation.

The current plan is directionally correct, but it conflicts with the issue acceptance criteria because approval and rejection are not idempotent.

## 1. Approve execution must be idempotent

Change `approve_execution(db_path, ticket_id, approved_by, comment=None)` behavior to:

```text
1. Load current readiness row.
2. Load latest execution approval.
3. If latest execution approval is already approved:
   - return the existing approval row
   - do not insert a new row
   - do not change readiness
   - do not raise
4. Else if readiness_status == ready_candidate:
   - insert approved row
   - set readiness_status = ready_to_take
   - return the new approval row
5. Else:
   - raise ValueError / return 409
```

Repeated approval must therefore succeed.

Example:

```text
POST /tickets/T199/approve-execution
→ 200 approved

POST /tickets/T199/approve-execution again
→ 200 approved, same latest approval, no duplicate history row
```

## 2. Reject execution must be idempotent

Change `reject_execution(db_path, ticket_id, approved_by, comment=None)` behavior to:

```text
1. Load current readiness row.
2. Load latest execution approval.
3. If latest execution approval is already rejected:
   - return the existing rejection row
   - do not insert a new row
   - do not append duplicate blocking reasons
   - do not raise
4. Else if readiness_status == ready_candidate:
   - insert rejected row
   - set readiness_status = blocked
   - append reason "Execution approval rejected by <approved_by>"
   - return the new rejection row
5. Else:
   - raise ValueError / return 409
```

Repeated rejection must therefore succeed.

Example:

```text
POST /tickets/T199/reject-execution
→ 200 rejected

POST /tickets/T199/reject-execution again
→ 200 rejected, same latest rejection, no duplicate history row
```

## 3. Contradictory transitions return conflict

The API should return `409 Conflict` only when the requested action contradicts the latest decision.

Examples:

```text
latest execution approval = approved
POST /tickets/T199/reject-execution
→ 409 Conflict
```

```text
latest execution approval = rejected
POST /tickets/T199/approve-execution
→ 409 Conflict
```

Do not implement reapproval, revoke, or reopen in this ticket unless the plan explicitly adds a separate workflow.

## 4. History semantics

Approval history remains append-only for real state transitions.

However, idempotent retries do not represent a new state transition and must not create extra rows.

Correct behavior:

```text
approve once
approve retry
GET approvals
→ one approved row
```

```text
reject once
reject retry
GET approvals
→ one rejected row
```

## 5. Test updates

Update the planned tests:

- Remove the expectation that approving when already `ready_to_take` raises `ValueError` if latest execution approval is already `approved`.
- Remove the expectation that rejecting when already `blocked` raises `ValueError` if latest execution approval is already `rejected`.
- Add tests:

```text
approve_execution is idempotent
reject_execution is idempotent
repeated approve does not duplicate history
repeated reject does not duplicate history
approve after rejected returns conflict
reject after approved returns conflict
```

## 6. API acceptance criteria additions

Add or update acceptance criteria:

- Repeated `POST /tickets/{id}/approve-execution` returns 200 and does not duplicate history when the latest execution approval is already approved.
- Repeated `POST /tickets/{id}/reject-execution` returns 200 and does not duplicate history when the latest execution approval is already rejected.
- Contradictory transitions return 409 Conflict.
- Approval history is append-only for real state transitions, not for duplicate retries.

## Non-goals reminder

This fix must still not change:

- scheduler behavior
- worker dispatch
- daemon state machine
- execution queue ordering
- automatic execution start
