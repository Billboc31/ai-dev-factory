# PLAN_FIX_REQUIRED

## Summary

The revised plan still does not explicitly separate the read-only preparation phase from the post-confirmation execution phase. This is required so the user confirms the exact recovery operations before any mutation occurs.

## Required fixes

1. Add an explicit read-only preparation step, for example `_prepare_recovery_action(...)`, that:
   - resolves the active ticket;
   - runs diagnostics without mutation;
   - classifies the blocker;
   - builds the exact allowlisted recovery operations;
   - stores a structured recovery proposal;
   - returns the exact operations in `proposed_action` for the confirmation card.

2. Add a separate post-confirmation execution step, for example `_execute_recovery_action(...)`, that:
   - loads the stored proposal by action/session id;
   - ignores operation definitions supplied by the frontend;
   - revalidates the ticket state before execution;
   - executes only the operations that were prepared and confirmed.

3. Add a `RecoveryProposal` or equivalent structure containing at least:
   - `project_id`;
   - `ticket_id`;
   - `blocker_class`;
   - exact ordered operations and validated parameters;
   - current ticket state and blocked stage;
   - a state/artifact fingerprint or version;
   - creation timestamp.

4. Revalidate the proposal fingerprint at confirmation time. If the ticket state or relevant artifacts changed after preparation, reject execution with a structured conflict response and require a new diagnosis.

5. Document the exact `proposed_action` schema rendered by the confirmation card, including operation name, description, risk level, and safe validated parameters.

6. Add tests proving that:
   - preparation performs no mutation;
   - the confirmation card receives the exact stored operations;
   - frontend-supplied operation changes are ignored;
   - stale proposals are rejected after ticket state changes;
   - only the confirmed stored proposal can be executed.

## Decision

PLAN_FIX_REQUIRED
