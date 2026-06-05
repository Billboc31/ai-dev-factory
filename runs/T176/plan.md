Now I have enough context to write the plan.

## Objective

Make environment redeploy self-healing when the sandbox source clone is missing or incomplete: automatically detect, log, and recreate the source clone before continuing deployment. Additionally, expose an optional collapsed "Advanced runtime options" section in the environment creation UI for path and clone refresh overrides.

## Included

### Backend — `services/control_api/services/sandbox_runtime_deploy.py`

- Add `_is_source_clone_valid(source_path: Path) -> bool` — returns `True` only if `source_path/.git` and `source_path/.ai-dev-factory/scripts` both exist.
- Add `_rehydrate_source_clone(source_path: Path, project_root: Path, ref: str, log_fn) -> None` — removes any broken `source_path`, re-clones from `project_root` at `ref` (same logic as the existing `_clone_fresh_source`), and emits the required log lines:
  - `"source clone missing or invalid"`
  - `"rehydrating sandbox source clone repo=<repo> branch=<branch> source_path=<path>"`
  - `"sandbox source clone restored successfully"`
- Before the `script_source` assignment (currently line 326), call `_is_source_clone_valid(source_path)` and invoke `_rehydrate_source_clone` if the check fails **or** if `force_source_refresh=True`.
- Add `force_source_refresh: bool = False` parameter to `deploy_operational_runtime()` and thread it down to the check site.

### Backend — `services/control_api/services/environment_provision.py`

- In `redeploy_environment()`, read `force_source_refresh` from the environment's `SandboxState` and forward it to `deploy_operational_runtime()`.

### Backend models — `services/control_api/models/sandbox.py`

- Add `force_source_refresh: bool = False` field to `SandboxState` (persisted in `state.json`; controls whether every redeploy forces a fresh clone).

### Backend API — `services/control_api/routes/environments.py` (and `CreateEnvironmentRequest`)

- Add optional fields to `CreateEnvironmentRequest`:
  - `runtime_root: str | None = None`
  - `force_source_refresh: bool = False`
- Populate `SandboxState.force_source_refresh` from the request when creating an environment.

### UI — `apps/dashboard/src/components/CreateEnvironmentModal.jsx`

- Add `advancedOpen: boolean` to form state (default `false`).
- Add a toggle button/link "Advanced runtime options" below the main fields.
- When `advancedOpen` is true, render a collapsed-by-default section containing:
  - **Runtime root override** — maps to `runtime_root` (text input, optional).
  - **Force source clone refresh** — maps to `force_source_refresh` (checkbox, default unchecked).
- Include these two fields in the API payload unconditionally (empty/false values are safe defaults).
- Keep the existing `sandbox_path` field in its current location (not moved to advanced section).

## Excluded

- Automated tests for rehydration logic.
- UI for triggering `force_source_refresh` on an already-created environment (the advanced section is only on the create modal; redeploy self-healing is automatic).
- Backend wiring of `runtime_root` beyond storing it in the request model (path override runtime behavior is a follow-up).
- Any change to the initial (non-redeploy) deploy path; `_clone_fresh_source` already handles first-time creation.
- Changes to `_validate_runtime_consistency()`; existing cross-path mismatch guards remain intact.

## Acceptance criteria

- `redeploy_environment()` completes successfully when `sandbox_dir/source` is absent, incomplete (no `.git`), or missing `.ai-dev-factory/scripts` — the source clone is recreated automatically.
- The log stream for a rehydration event contains the three prescribed lines (missing/invalid, rehydrating with repo/branch/path, restored successfully).
- Redeployment of a healthy environment (source clone intact) produces no rehydration log lines and behaves identically to today.
- `SandboxState.force_source_refresh = true` causes every redeploy to reclone source even when the existing clone is valid.
- The create modal renders an "Advanced runtime options" toggle; the advanced section is hidden until the toggle is clicked.
- The advanced section exposes `runtime_root` (text) and `force_source_refresh` (checkbox); both are sent in the create payload.
- Existing `_validate_runtime_consistency()` checks still fire and still reject invalid path combinations.
