# T230 Plan Fix 01

Revise `runs/T230/plan.md` to close the readiness-visibility gap identified in `runs/T230/reviews/plan-review-01.md`.

## Required corrections

### 1. Define readiness blocking semantics

The plan must explicitly define how the backend determines which tickets are blocking the batch during readiness-related stages.

Do not make the frontend infer blocking from raw statuses.

Specify the source of truth and deterministic rules used to populate, per ticket:

- `is_blocking`
- `blocking_reason`

Cover at least:

- missing / incomplete Ticket Intelligence while the batch is frozen;
- failed Ticket Intelligence when it prevents progression;
- readiness states that prevent the batch from progressing to dispatch;
- states that are informational only and must not be treated as blockers.

### 2. Extend batch-level waiting summary rules for readiness

The plan must cover the issue requirement that operators can see which tickets are blocking readiness when applicable.

Add a readiness-specific waiting-summary rule such as:

`Waiting on readiness: T003, T006`

when individual blocking tickets can be identified.

If the lifecycle has a state where readiness is merely executing and no individual blocker can yet be determined, `Readiness evaluation running` is acceptable for that specific situation, but the plan must clearly distinguish the two cases.

The summary must remain derived from backend workflow state rather than duplicated frontend logic.

### 3. Add explicit tests for blocking/waiting computation

Update the plan to include backend tests for the pipeline-status computation and frontend tests for rendering the resulting states.

At minimum cover:

- frozen + incomplete intelligence → blocking ticket IDs are named;
- frozen + all intelligence completed → `Ready for dependency analysis`;
- readiness stage with identifiable blocking tickets → readiness summary names those tickets;
- missing intelligence/readiness rows remain visible with `not_started` / `—` as appropriate;
- failed intelligence or readiness state produces an explicit visible blocking reason where it blocks progression;
- completed/non-blocking tickets are not incorrectly flagged as blockers.

## Constraints

- Keep the existing architecture proposed by the plan unless a concrete repository constraint requires adjustment.
- Do not change the batch lifecycle state machine or dispatcher behaviour as part of this fix.
- Do not add frontend-side workflow inference that duplicates backend business logic.
- Do not expand scope into retries/requeue actions, WebSocket/SSE updates, or ticket detail views.

After applying these corrections, update `runs/T230/plan.md` itself so the revised plan is the new source of truth for the next review.
