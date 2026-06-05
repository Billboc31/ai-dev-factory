# T178 — T178 - Supervisor runtime_root override fix not applied in active runtime

**Source**: GitHub Issue #207

## Description

The runtime_root override is still ignored after T177.

Deploy logs still show:

runtime_root_source=auto

and the effective runtime_root remains the auto-generated sandbox runtime path.

This strongly suggests the active supervisor/runtime is still running old code or the fix was not applied to the runtime actually launching deployments.

Observed behavior:
- source clone rehydration now works correctly
- deploy reaches build/start successfully
- runtime_root override still ignored
- logs still show auto mode

Need to verify:
- the active runtime clone contains the T177 changes
- EnvironmentProvisionRequest actually declares runtime_root
- the correct supervisor process/runtime is restarted
- deployments are using the updated runtime clone

Recommended diagnostics:
- grep runtime_root in services/supervisor/main.py inside the active runtime clone
- log loaded EnvironmentProvisionRequest fields at supervisor startup
- log runtime build/version/commit during deploy startup
- verify the running supervisor process path matches the updated runtime

Acceptance criteria:
- active runtime contains T177 changes
- supervisor restart picks up the new model fields
- runtime_root override works end-to-end
- logs show runtime_root_source=override when override is provided
