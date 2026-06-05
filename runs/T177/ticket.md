# T177 — T177 - Fix environment runtime root override propagation

**Source**: GitHub Issue #206

## Description

Bug: the environment creation form exposes a runtime root override, but deploy still runs in automatic runtime-root mode.

Observed in deploy logs:
- runtime_root_source is auto
- runtime_root remains the generated sandbox runtime path

Expected:
- when the form provides runtime_root, the deploy flow uses it
- logs show override mode
- the chosen runtime root affects the deploy target

Check the full propagation chain:
- CreateEnvironmentModal payload
- environment creation API request model
- SandboxState persistence
- redeploy and deploy runtime state loading
- runtime root resolution in sandbox_runtime_deploy

Acceptance criteria:
- the request payload contains the selected runtime root
- the backend persists it
- deploy reads the persisted value
- logs clearly show whether auto or override mode was used
- invalid runtime root values fail validation instead of being ignored
