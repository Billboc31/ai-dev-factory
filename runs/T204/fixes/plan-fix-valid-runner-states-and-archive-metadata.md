# Plan fix — use valid runner states and explicit archive metadata

## Required plan update

Update `runs/T204/plan.md` before starting implementation.

The plan is directionally correct, but it must be corrected in three areas:

1. Do not write unsupported runner states.
2. Correct the operation count from 10 to 12.
3. Make `archive_ticket` behavior explicit and non-ambiguous.

## 1. Valid runner states only

T204 must not introduce new runner states.

Do not write these values to `state.json`:

```text
PLANNING
CODING
CANCELLED
```

They are not currently valid runner states.

Use only existing runner states.

Recommended mappings for this ticket:

```text
reset_to_planning -> PLAN_FIX_REQUIRED
reset_to_coding -> IMPLEMENTATION_FIX_REQUIRED
```

Rationale:

- `PLAN_FIX_REQUIRED` safely sends the ticket back to the planner path without pretending no prior plan existed.
- `IMPLEMENTATION_FIX_REQUIRED` safely sends the ticket back to the coder path while preserving the approved/current plan context.
- Both are existing states already understood by the runner.

If the implementer chooses the alternative mapping below, it must be explicitly justified in the final implementation notes:

```text
reset_to_planning -> INIT
reset_to_coding -> PLAN_APPROVED
```

In all cases, the implementation must use one explicit mapping and tests must assert the exact state written.

## 2. Archive current artifacts before reset

Before changing state, reset operations must archive affected artifacts into:

```text
runs/<ticket_id>/archive/<timestamp>/
```

`reset_to_planning` should archive plan/review/test/conflict/retry artifacts according to the corrected plan.

`reset_to_coding` should preserve `plan.md` and archive implementation/review/test/conflict/retry artifacts according to the corrected plan.

Each reset archive must include metadata:

```json
{
  "operation": "reset_to_planning",
  "ticket_id": "T204",
  "requested_by": "operator",
  "reason": "...",
  "previous_state": "...",
  "new_state": "PLAN_FIX_REQUIRED",
  "created_at": "..."
}
```

or:

```json
{
  "operation": "reset_to_coding",
  "ticket_id": "T204",
  "requested_by": "operator",
  "reason": "...",
  "previous_state": "...",
  "new_state": "IMPLEMENTATION_FIX_REQUIRED",
  "created_at": "..."
}
```

## 3. Explicit archive_ticket behavior

`archive_ticket` must not use or create a `CANCELLED` runner state.

Use archive metadata instead.

Required `state.json` fields:

```json
{
  "archived": true,
  "archived_reason": "...",
  "archived_by": "...",
  "archived_at": "..."
}
```

Do not delete artifacts.

Do not remove the worktree.

Do not invoke planner/coder/reviewer/tester.

Do not change scheduler or worker behavior.

## 4. Correct operation count

The plan currently says `ten operation keys`, but the registry contains 12 operations.

Correct the acceptance criteria to say:

```text
all 12 operation keys
```

The 12 keys are:

```text
rerun_intelligence
rerun_readiness
rerun_rules
rerun_diagnostics
approve_execution
reject_execution
mark_blocked
reset_to_planning
reset_to_coding
clear_stuck_state
delete_worktree
archive_ticket
```

## 5. Tests to add/update

Add or update tests so that:

- `reset_to_planning` writes only the chosen valid state.
- `reset_to_coding` writes only the chosen valid state.
- no test expects `PLANNING`, `CODING`, or `CANCELLED`.
- `archive_ticket` writes archive metadata, not a new runner state.
- the operation registry contains exactly the 12 expected keys.
- every operation attempt is audited, including rejected attempts.

## 6. Non-goals reminder

This fix must not introduce:

- new runner states
- scheduler changes
- dispatcher changes
- worker allocation changes
- worker reservation changes
- auto-triggered operations
- automatic PR merging
- bulk ticket operations

T204 remains a guarded manual operations panel only.
