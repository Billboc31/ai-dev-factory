# Plan review — T199 approval idempotency

The T199 plan is broadly aligned with the issue goal: it introduces human execution approval, the `ready_to_take` lifecycle state, an approval API, an approval UI, and an append-only approval history while leaving scheduler and worker behavior unchanged.

However, one blocking issue must be fixed before implementation starts.

## Blocking issue — approve/reject endpoints are not idempotent

The issue explicitly requires:

```text
- approving twice is idempotent
- revoking twice is idempotent
```

The current plan says:

```text
approve_execution(...)
Preconditions: ticket_readiness.readiness_status == 'ready_candidate'
```

and also plans tests where approving when the state is already `ready_to_take` raises `ValueError`.

That means this sequence would fail:

```text
POST /tickets/T199/approve-execution
→ readiness_status = ready_to_take

POST /tickets/T199/approve-execution again
→ 409 / ValueError
```

This is not idempotent.

The same issue exists for rejection:

```text
POST /tickets/T199/reject-execution
→ readiness_status = blocked

POST /tickets/T199/reject-execution again
→ 409 / ValueError
```

This is risky because users can double-click buttons, retry requests, refresh pages, or clients can retry network calls.

## Required behavior

`approve_execution(...)` must be idempotent:

- If the latest execution approval is already `approved`, return the existing latest approval and do not insert a duplicate row.
- If readiness is already `ready_to_take`, return success with the existing approval state.
- Do not raise an error for repeated approval.

`reject_execution(...)` must be idempotent:

- If the latest execution approval is already `rejected`, return the existing latest rejection and do not insert a duplicate row.
- If readiness is already `blocked` because of the same execution rejection, return success with the existing rejection state.
- Do not raise an error for repeated rejection.

## Conflict behavior

Conflicts should only occur when the requested action contradicts the current latest decision.

Examples:

```text
latest approval = approved
POST reject-execution
→ 409 Conflict, unless a future explicit revoke/reopen workflow exists
```

```text
latest approval = rejected
POST approve-execution
→ 409 Conflict, unless a future explicit reapproval workflow exists
```

For this ticket, do not implement reapproval or revocation unless explicitly planned. Keep the workflow simple and safe.

## History behavior

The plan currently says approval history is append-only, which is good. But idempotent duplicate requests should not create duplicate rows.

Append-only means each real state transition creates a row; retries of the same already-applied decision should not.

## Required correction

Update `runs/T199/plan.md` so that:

1. Repeated approve is idempotent and returns the existing approved decision.
2. Repeated reject is idempotent and returns the existing rejected decision.
3. Duplicate requests do not append duplicate history rows.
4. Tests cover repeated approve and repeated reject.
5. 409 is reserved for contradictory state transitions, not same-action retries.

## Review verdict

PLAN_FIX_REQUIRED until approval and rejection idempotency are correctly specified.
