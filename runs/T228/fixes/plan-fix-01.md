# PLAN_FIX_REQUIRED

## Summary

The recovery concept is strong, but the plan must be revised so that the user confirms an exact, immutable recovery plan before any mutating operation is executed.

## Required fixes

### 1. Separate preparation from execution

Add a read-only preparation phase such as `_prepare_recovery_action(...)` that:

- resolves the active ticket;
- runs diagnostics without mutation;
- classifies the blocker;
- builds the exact ordered recovery plan;
- stores the validated plan in the pending action;
- returns the blocker class and exact operations in `proposed_action`.

Add a separate execution phase such as `_execute_recovery_action(...)` that runs only after confirmation and executes only the stored allowlisted operations.

The confirmation card must display the exact operations, descriptions, parameters and risk levels before the user confirms.

### 2. Reject stale recovery plans

Store a compact ticket-state fingerprint with the pending action, including at least:

- project id;
- ticket id;
- current state;
- blocked stage;
- state artifact timestamp, hash or equivalent version;
- observed artifact set;
- exact recovery operations.

At confirmation time, re-read the current ticket state. If it no longer matches the prepared snapshot, return a conflict response and require a new diagnosis. Do not execute the stale plan.

### 3. Define every allowlisted operation precisely

For each operation, document:

- accepted parameters and closed enums;
- internal service or API invoked;
- preconditions;
- expected effects;
- success criteria;
- retry policy;
- verification rule.

No operation may accept arbitrary paths, service names, commands or other free-form execution values from the LLM or frontend.

Examples:

- `regenerate_artifact` must accept only supported artifact types and use the normal workflow.
- `restart_service` must resolve a configured service identifier through an allowlist.
- `retry_stage` must target only the diagnosed stage stored in the confirmed plan.

### 4. Use an asynchronous recovery job

The confirmed action should return a `recovery_id` and run in the background so the Supervisor remains responsive.

Provide a polling endpoint exposing stages such as:

- `APPLYING_FIX`;
- `RETRYING_STAGE`;
- `VERIFYING`;
- `RECOVERED`;
- `NEEDS_USER_INPUT`;
- `BUG_REPORTED`;
- `FAILED`.

Persist the final recovery report long enough for the frontend to retrieve it after the active-session lock is released.

### 5. Make concurrency protection atomic

Add a dedicated lock around `_active_recovery_sessions`.

The check and insertion for a ticket must occur in one critical section. Session cleanup and lock release must be guaranteed in `finally`, including unexpected exceptions.

Concurrent recovery for the same ticket must return a structured conflict response, not HTTP 500.

### 6. Make bug deduplication deterministic

Define a stable bug signature from structured fields such as:

- configured project repository;
- blocker class;
- failed stage;
- normalized error code;
- affected component.

Do not use unrestricted LLM-generated text as the deduplication key. The GitHub repository must be resolved from trusted project configuration.

### 7. Add missing tests

Add tests proving that:

- preparation performs no mutation;
- the confirmation payload contains the exact stored recovery plan;
- ticket-state changes before confirmation cause a conflict;
- frontend-supplied operation or parameter changes are ignored or rejected;
- concurrent preparation/execution creates only one active session per ticket;
- locks and sessions are cleaned after exceptions;
- arbitrary operation parameters are refused;
- intermediate asynchronous stages can be polled;
- `missing_approval` never approves automatically;
- an existing matching bug issue prevents duplicate creation.

## Decision

PLAN_FIX_REQUIRED
