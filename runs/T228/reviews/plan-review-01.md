# PLAN_FIX_REQUIRED

## Summary

The recovery concept is strong, but the plan must be revised before implementation to guarantee that the user confirms the exact recovery operations that will run, that stale recovery plans cannot be executed, and that long-running recovery remains observable and concurrency-safe.

## Required fixes

### 1. Separate preparation from execution

Introduce two explicit phases:

- `_prepare_recovery_action(...)`: read-only diagnostics, blocker classification, recovery-plan construction, and pending-action creation.
- `_execute_recovery_action(...)`: revalidate the ticket snapshot and execute only the operations stored in the confirmed pending action.

The `proposed_action` returned to the frontend must include the exact ticket id, blocker class, and ordered operations before confirmation.

### 2. Add stale-plan protection

Store a minimal ticket snapshot/fingerprint in the pending action, including at least:

- ticket id;
- current state;
- blocked stage;
- state artifact timestamp or hash;
- observed relevant artifacts;
- exact recovery operations.

At confirmation time, re-read the ticket state. If the snapshot changed, return a conflict and require a new diagnosis instead of executing the stale plan.

### 3. Define every allowlisted operation precisely

For each recovery operation, document:

- allowed parameters;
- internal API or service invoked;
- preconditions;
- expected effects;
- success criteria;
- retry behavior;
- definition of ticket progress.

Do not accept arbitrary paths, service names, commands, or artifact names from the LLM or frontend. Use closed enums and configured identifiers only.

### 4. Use an asynchronous recovery job

Recovery can span diagnostics, fixes, retries, verification, and up to three iterations. Confirm should return a `recovery_id` and `RUNNING` status immediately. Add a polling endpoint exposing intermediate stages and terminal results:

- `DIAGNOSING`
- `PLAN_READY`
- `APPLYING_FIX`
- `RETRYING_STAGE`
- `VERIFYING`
- `RECOVERED`
- `NEEDS_USER_INPUT`
- `BUG_REPORTED`
- `FAILED`

### 5. Make concurrency handling atomic

Add a dedicated lock around `_active_recovery_sessions`. The check-and-create operation must be atomic. Cleanup must happen in `finally`, while terminal reports remain available in a separate result registry for frontend polling.

### 6. Make bug deduplication deterministic

Define `bug_signature` from structured normalized fields such as:

- project id;
- blocker class;
- failed stage;
- normalized error code;
- affected component.

Search only the configured repository for the active project. Never use free-form LLM text as the deduplication key.

## Required tests

Add tests proving that:

- preparation performs no mutation;
- the confirmed operation list exactly matches the presented plan;
- changed ticket state between proposal and confirmation returns a conflict;
- frontend-supplied or modified operations are ignored;
- two concurrent recoveries cannot start for the same ticket;
- locks and active-session state are released after exceptions;
- arbitrary operation parameters are rejected;
- intermediate recovery stages can be polled;
- `missing_approval` never causes automatic approval;
- an existing matching bug issue prevents duplicate creation.

## Decision

PLAN_FIX_REQUIRED
