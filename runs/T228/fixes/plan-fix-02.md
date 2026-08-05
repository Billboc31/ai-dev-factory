# Plan Fix 02 — Separate recovery preparation from execution

Update `runs/T228/plan.md` to make the recovery workflow explicitly two-phase and confirmation-safe.

## Required architecture

### Phase 1 — Prepare recovery proposal (read-only)

Introduce `_prepare_recovery_action(project_id, ...)` or an equivalent function.

It must:

1. Resolve the active ticket.
2. Read current ticket state, artifacts and diagnostics.
3. Classify the blocker.
4. Build the exact ordered recovery operations using only `ALLOWLISTED_RECOVERY_OPS`.
5. Validate and normalize every operation parameter.
6. Compute a stable snapshot/fingerprint from the relevant ticket state and artifacts.
7. Persist a structured `RecoveryProposal` associated with the pending workspace action.
8. Return the exact proposal to the frontend for confirmation.
9. Perform no state mutation, retry, service restart, artifact regeneration or issue creation.

The proposed action should expose a safe schema such as:

```json
{
  "capability": "recover_ticket",
  "action_id": "...",
  "ticket_id": "T123",
  "blocker_class": "STALE_READINESS",
  "operations": [
    {
      "name": "refresh_readiness",
      "description": "Recompute readiness from the current ticket artifacts",
      "risk": "low",
      "params": {}
    }
  ],
  "state_fingerprint": "..."
}
```

Do not expose arbitrary paths, commands, service names or unvalidated LLM parameters.

### Phase 2 — Execute confirmed proposal

Introduce `_execute_recovery_action(...)` or an equivalent function called only after confirmation.

It must:

1. Load the stored `RecoveryProposal` from server-side state using the pending action/session id.
2. Ignore operation names or parameters supplied by the frontend during confirmation.
3. Re-read the ticket state and relevant artifacts.
4. Recompute the fingerprint.
5. Return a structured conflict response when the fingerprint differs, without executing any operation.
6. Execute only the ordered operations stored in the confirmed proposal.
7. Revalidate each operation against `ALLOWLISTED_RECOVERY_OPS` immediately before execution.
8. Verify ticket progress and produce the recovery report.

## RecoveryProposal structure

Define a dataclass or equivalent structure containing at least:

- proposal/session id;
- project id;
- ticket id;
- blocker class;
- exact validated ordered operations;
- original ticket state;
- blocked stage;
- artifact/state fingerprint;
- creation timestamp.

## Tests to add

- preparation is strictly read-only;
- the confirmation payload contains the exact stored operations;
- operation modifications sent by the frontend are ignored;
- an unknown operation or arbitrary parameter is rejected;
- a ticket state/artifact change between preparation and confirmation returns a conflict;
- no operation runs when the proposal is stale;
- execution uses only the server-side confirmed proposal.

The regenerated plan must clearly describe this prepare/confirm/revalidate/execute sequence instead of assigning diagnosis, planning and mutation to one generic `_execute_recover_ticket()` flow.
