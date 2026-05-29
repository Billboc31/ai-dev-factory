Implementation is complete. Here's the summary:

**Files modified:**

- `services/control_api/services/environment_provision.py` — In `provision_environment()`, replaced both `_destroy_quietly()` calls on failure with `apply_deploy_failure()` + `mgr._write_state(failed)`, mirroring the existing behavior in `redeploy_environment()`. The `_destroy_quietly()` helper is preserved but no longer called from the provision path.

- `tests/test_environment_routes.py` — Updated three tests that asserted the old destroy-on-failure behavior:
  - `test_failed_provisioning_no_environment_card` → `test_failed_provisioning_persists_environment_card`: now asserts 1 environment with `status=error`
  - `test_failed_provisioning_sandbox_dir_removed` → `test_failed_provisioning_preserves_sandbox_dir`: now asserts sandbox dir is preserved
  - `test_failed_provisioning_cleans_custom_sandbox_path` → `test_failed_provisioning_preserves_custom_sandbox_path`: now asserts environment persists with `status=error` and custom dir survives

All 31 tests pass. The change is minimal — the existing `apply_deploy_failure()`, delete, and redeploy flows already handled everything else correctly.
