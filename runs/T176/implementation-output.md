Everything looks correct. Here's a summary of what was implemented:

---

## Changes delivered

### `services/control_api/models/sandbox.py`
Added 3 fields to `SandboxState`: `runtime_root` (user override input), `effective_runtime_root` (resolved at deploy time), `force_source_refresh` (triggers reclone).

### `services/control_api/routes/environments.py`
Added `runtime_root` and `force_source_refresh` to `CreateEnvironmentRequest`. Added API-boundary validation rejecting non-absolute or `..`-containing paths with HTTP 400. Passed both fields to `provision_environment`.

### `services/control_api/services/environment_provision.py`
Added `runtime_root` and `force_source_refresh` params to `provision_environment` and `provision_environment_from_body`. Fields are applied to `SandboxState` after `mgr.create()` so they persist for the deploy and future redeploys.

### `services/control_api/services/sandbox_runtime_deploy.py`
Three new helpers:
- `_is_source_clone_valid`: checks `.git` and `.ai-dev-factory/scripts` exist
- `_rehydrate_source_clone`: emits the required diagnostic log lines then delegates to `_clone_fresh_source`; logs "restored successfully" on success
- `_resolve_runtime_root`: validates the override (absolute, no `..`, descends from root), derives new `sandbox_dir`, returns `(sandbox_dir, "auto"|"override")`

In `deploy_operational_runtime`:
- Removed the hard-fail check that blocked redeploy when source was missing
- Calls `_resolve_runtime_root` first (supports runtime root override end-to-end)
- Logs `runtime_root_source=auto|override`
- Persists `effective_runtime_root` to state
- Chooses `_rehydrate_source_clone` when source is invalid or `force_source_refresh` is set; otherwise uses the normal `_clone_fresh_source` path

### `apps/dashboard/src/components/CreateEnvironmentModal.jsx`
Added `runtime_root` and `force_source_refresh` to form state. Added a collapsible "Advanced runtime options" section (collapsed by default) with a runtime root text input and force-refresh checkbox. The "Runtime target" preview now updates live to show the derived sandbox path when an override is provided. Both fields are included in the create payload.
