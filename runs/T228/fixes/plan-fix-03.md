# PLAN_FIX_REQUIRED — iteration 3

The current `runs/T228/plan.md` is still the original plan and has not incorporated the previous plan-fix artifacts. Regenerate and replace `runs/T228/plan.md`; do not merely acknowledge this artifact.

## Mandatory architecture correction

The recovery workflow must be explicitly split into four distinct phases:

1. **Prepare (read-only)**
   - Resolve the active ticket.
   - Run diagnostics without mutating ticket state.
   - Classify the blocker.
   - Build an exact allowlisted recovery plan.
   - Create and persist a `RecoveryProposal` snapshot.
   - Return a `proposed_action` containing the exact operations that will require confirmation.

2. **Confirm**
   - The confirmation card must display the exact ticket id, blocker class, operations, operation parameters, descriptions, and risk levels.
   - The frontend confirms only by `action_id`; it must not resend or alter operations or parameters.

3. **Revalidate**
   - Before execution, reload the ticket state and compare it to the stored proposal fingerprint.
   - The fingerprint must include at least ticket id, current state, blocked stage, relevant artifact metadata, and a state/artifact version or deterministic hash.
   - If the ticket changed after preparation, return HTTP 409 and require a new diagnostic. Do not execute a stale plan.

4. **Execute**
   - Execute only the immutable operations stored in the confirmed `RecoveryProposal`.
   - Revalidate every operation name and parameter against the Supervisor allowlist.
   - Never accept operation names, paths, services, repositories, commands, or parameters supplied by the frontend at confirmation time.

## Required data structures

Define a structured `RecoveryProposal` containing at least:

- `proposal_id`
- `project_id`
- `ticket_id`
- `blocker_class`
- `operations`
- `state_fingerprint`
- `created_at`
- `status` (`AWAITING_CONFIRMATION`, `EXECUTING`, `COMPLETED`, `INVALIDATED`)

Each proposed operation must contain only closed, validated fields such as:

- `name`
- `description`
- `risk_level`
- `params`

## Operation contracts

For every allowlisted operation, document:

- accepted parameter schema;
- internal service/function invoked;
- preconditions;
- mutation performed;
- success condition;
- retry policy;
- prohibited arbitrary values.

Examples:

- `regenerate_artifact` must accept a closed artifact type enum, never a free filesystem path.
- `restart_service` must resolve a configured service identifier, never a free service name or shell command.
- `create_bug_issue` must resolve the configured project repository server-side.

## Concurrency and lifecycle

- Protect proposal/session creation with a dedicated lock so check-and-create is atomic.
- Guarantee cleanup in `finally` after execution errors.
- Preserve terminal recovery results in a separate result registry long enough for frontend polling.
- Long-running recovery must use a background job with `recovery_id` and a polling endpoint, unless the regenerated plan rigorously proves all operations are short and non-blocking.

## Deterministic bug deduplication

Build the bug signature from structured fields such as:

- `project_id`
- `blocker_class`
- `failed_stage`
- normalized error code
- affected component

Do not use free-form LLM text as the deduplication key.

## Required tests

Add tests proving that:

- preparation performs no mutation;
- the confirmation card receives the exact stored operations;
- the frontend cannot alter operations or params;
- a changed ticket state invalidates the proposal with HTTP 409;
- only the stored immutable proposal is executed;
- concurrent preparation/execution for the same ticket is rejected atomically;
- locks are released after exceptions;
- arbitrary paths, services, repositories, commands, and operation names are rejected;
- missing approval never triggers automatic approval;
- duplicate product bugs never create a second GitHub issue;
- intermediate asynchronous stages are available through polling.

## Expected output

Replace `runs/T228/plan.md` with a new plan that explicitly implements the architecture above. The new `plan.md` must have different content and a different Git blob SHA from the original plan.