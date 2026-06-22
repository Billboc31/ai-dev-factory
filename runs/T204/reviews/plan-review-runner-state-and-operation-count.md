# Plan review — T204 runner states and operation count

The T204 plan is aligned with the product direction: it adds a manual Ticket Operations panel with explicit confirmation, audit logging, recovery actions, dangerous-action safeguards, and no automatic scheduler or worker-triggered behavior.

However, the plan must be fixed before implementation starts.

## Blocking issue 1 — invalid runner states

The plan currently says:

```text
reset_to_planning -> updates state.json to PLANNING
reset_to_coding -> updates state.json to CODING
archive_ticket -> set state.json to CANCELLED if supported
```

These states are not part of the current runner state machine.

The current valid runner states are:

```text
INIT
PLAN_REVIEW_NEEDED
PLAN_FIX_REQUIRED
PLAN_APPROVED
IMPLEMENTATION_REVIEW_NEEDED
IMPLEMENTATION_FIX_REQUIRED
IMPLEMENTATION_APPROVED
TEST_COMPLETE
CONFLICT_RESOLUTION_NEEDED
CONFLICT_RESOLVING
CONFLICT_RESOLVED_REVIEW_NEEDED
CONFLICT_RESOLUTION_FAILED
```

T204 must not invent new runner states unless the ticket explicitly updates the state machine, transitions, UI, and tests. This ticket should not do that.

Required correction:

- `reset_to_planning` must reset to an existing planning-compatible state.
- `reset_to_coding` must reset to an existing coding-compatible state.
- `archive_ticket` must not introduce `CANCELLED` as a runner state.

Recommended mapping for T204:

```text
reset_to_planning -> PLAN_FIX_REQUIRED
reset_to_coding -> IMPLEMENTATION_FIX_REQUIRED
archive_ticket -> archived flag in state.json, not a new runner state
```

Alternative acceptable mapping:

```text
reset_to_planning -> INIT
reset_to_coding -> PLAN_APPROVED
```

But the plan must choose one explicit mapping and justify it.

## Blocking issue 2 — inconsistent operation count

The plan says:

```text
covering all ten operation keys
```

but the registry actually lists 12 operations:

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

The acceptance criteria must say 12 operation keys, not 10.

## Blocking issue 3 — archive_ticket behavior is ambiguous

The plan says:

```text
set state.json to a recognized terminal like CANCELLED if already supported, otherwise add archived: true
```

This is too ambiguous and risks creating inconsistent behavior.

T204 must choose one behavior.

Recommended behavior:

```json
{
  "archived": true,
  "archived_reason": "...",
  "archived_by": "...",
  "archived_at": "..."
}
```

Do not change the runner state to `CANCELLED` in T204.

The ticket should preserve all artifacts and prevent accidental execution only by UI/API operation availability, not by inventing a new runner state.

## Required correction

Update `runs/T204/plan.md` so that:

1. No unsupported runner states are written.
2. `reset_to_planning` and `reset_to_coding` map to explicitly chosen valid states.
3. `archive_ticket` uses explicit archive metadata and does not use `CANCELLED`.
4. The operation count is corrected from 10 to 12.
5. Tests assert that no invalid state value is written.
6. Scheduler, dispatcher, worker allocation, worker reservation, and automatic execution paths remain untouched.

## Review verdict

PLAN_FIX_REQUIRED until runner state mappings, archive behavior, and operation count are corrected.
