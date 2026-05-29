Now I have everything needed. The bug is clear and the fix is minimal. Here's the plan:

---

## Objective

Persist failed environment deployments in the runtime state instead of silently destroying them, giving users the ability to inspect logs, review failure context, retry provisioning, and manually delete — mirroring the behavior that already exists for redeploy failures.

## Included

- **`services/control_api/services/environment_provision.py` — `provision_environment()` (lines 165–182)**:
  - Remove both `_destroy_quietly()` calls on failure (exception path at lines 172–174 and failed-result path at lines 175–179).
  - Replace with `apply_deploy_failure()` + `mgr._write_state(failed)` — identical to what `redeploy_environment()` does on failure (lines 220–233).
  - The raised `RuntimeError` is preserved so the API caller receives the failure.

- No other backend changes are needed. All required fields (`lifecycle_error`, `lifecycle_steps`, `lifecycle_phase=failed`, `status=error`, `last_step`, `healthcheck_status`, `smoke_status`) already exist on `SandboxState` and are already populated by `apply_deploy_failure()`. Logs (`run.log`, `supervisor.log`) already survive on disk. The delete endpoint already works for error-state environments. The redeploy endpoint already handles re-running from an existing environment record.

- **`services/control_api/services/environment_provision.py` — `_destroy_quietly()`**: Keep the helper (it may still be used or useful for cleanup edge cases) but stop calling it on provision failure.

- **Tests** (if an existing test suite covers provision failures): Update any test that asserts the environment is destroyed on provision failure to instead assert it remains in `status=error` / `lifecycle_phase=failed`.

## Excluded

- UI changes: The dashboard `EnvironmentCard.jsx` already renders `lifecycle_error`, red badges for `error`/`failed` status, hides URLs when not running, and shows a Redeploy button. No card UI work is in scope.
- Adding a new "Retry Deploy" button distinct from the existing Redeploy button — the existing `POST /environments/{env_id}/redeploy` endpoint is sufficient and already works from any state.
- Any changes to the delete flow — it already handles error-state environments correctly.
- Any changes to log collection or `format_environment_logs()` — already aggregates all phases including failed ones.
- Cleaning up sandbox filesystem artifacts on provision failure — best-effort cleanup becomes the responsibility of the explicit Delete action, not the failure handler.
- Any UI changes to add a new "failed" badge distinct from the existing `error` status — out of scope.

## Acceptance criteria

- After a first-time `POST /environments` that fails at any lifecycle step (bootstrap, build, start, healthcheck, supervisor, route), `GET /environments` returns the environment record with `status=error` and `lifecycle_phase=failed`.
- `GET /environments/{env_id}/logs` returns the lifecycle logs (run.log, supervisor.log, lifecycle steps, lifecycle_error) for a failed initial-provision environment.
- `POST /environments/{env_id}/redeploy` succeeds on a failed initial-provision environment (reuses same metadata, re-runs full pipeline).
- `DELETE /environments/{env_id}` succeeds on a failed initial-provision environment, removing the record and sandbox directory.
- A successful `POST /environments` deploy continues to return `status=running` and valid URLs — no regression.
- The `_destroy_quietly()` call is no longer reachable from the provision happy-or-sad path (verify by code inspection).
