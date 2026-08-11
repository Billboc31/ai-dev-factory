# T230 Plan Review 01

## Verdict

`PLAN_FIX_REQUIRED`

## Summary

The plan is directionally correct and covers the main visibility gap for frozen batches: per-ticket Ticket Intelligence/readiness/runtime state, a batch-level waiting summary, and a dedicated dashboard panel.

However, one important part of the ticket is not fully specified yet: **readiness blocking visibility**.

The ticket explicitly requires the batch UI to explain what the batch is waiting on, including readiness when applicable, and to show a short blocking reason per ticket. The current plan introduces `readiness_status`, `is_blocking`, and `blocking_reason`, but does not define the rules that make readiness-blocked tickets identifiable or reflected in the batch waiting summary.

## Blocking issues

### 1. Readiness blockers are not fully represented in `waiting_summary`

The plan defines:

- `readiness_running` → `"Readiness evaluation running"`

but does not define how to surface the actual tickets that are still blocking readiness progression when that information is available.

This leaves a gap versus the expected UX from the issue, which explicitly calls for messages such as:

- `Waiting on readiness: T003, T006`

The plan must explain how readiness-blocking tickets are detected and when the batch-level summary names them.

### 2. `is_blocking` / `blocking_reason` rules are underspecified

The response model contains:

- `is_blocking`
- `blocking_reason`

but the plan does not define deterministic rules for populating them across relevant pipeline stages.

At minimum, the plan should specify blocking semantics for:

- missing / incomplete Ticket Intelligence while the batch is frozen;
- failed Ticket Intelligence where it prevents progression;
- readiness states that prevent dispatch/progression;
- non-blocking runtime states, so runtime display does not accidentally become a second source of workflow truth.

The UI should not have to infer blocking logic from raw statuses.

### 3. Tests do not explicitly cover the new blocking logic

Because the core value of this ticket is making workflow waiting reasons trustworthy, the plan should explicitly include backend tests for the summary/blocking computation and frontend tests for the visible readiness-blocked state.

Important cases include:

- frozen + one or more incomplete intelligence rows;
- frozen + all intelligence complete;
- readiness stage with one or more blocking tickets;
- missing pipeline rows shown as `not_started` rather than omitted;
- failed intelligence/readiness state producing a visible blocking reason;
- completed/non-blocking states not being incorrectly marked as blockers.

## Risks if implemented as currently planned

- The batch may still look ambiguous once it reaches readiness, reproducing the same operational problem this ticket is intended to solve.
- Different frontend/backend code paths may derive blocking state differently because the rules are not defined centrally.
- `is_blocking` and `blocking_reason` could become inconsistent or effectively cosmetic fields.
- Regressions in waiting-state calculation may go unnoticed without explicit tests.

## Non-blocking observations

The plan's use of existing runtime DB helpers and polling architecture is reasonable. A possible N+1 pattern from per-ticket lookups is worth keeping in mind, but it is not a blocker for this ticket unless batch sizes make it materially expensive.
