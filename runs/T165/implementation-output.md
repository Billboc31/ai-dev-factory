## Summary

**Code audit confirmed** — no production code changes needed. The infra bootstrap chain was already correctly wired:
- `sandbox_runtime_deploy.py:278` calls `rs._ensure_required_infra(log_path)` before any route registration or scripts
- Both `provision_environment()` and `redeploy_environment()` reach `deploy_operational_runtime()` with no early exits
- No bypass endpoints exist in the supervisor
- `ProxyManager(auto_ensure_infra=False)` prevents any duplicate bootstrap

**Test changes made** (all already committed):

| File | Change |
|------|--------|
| `tests/test_environment_infra_bootstrap.py` | New file — `TestInfraBootstrappedOnProvision` (infra called with Path arg), `TestTraefikInitiallyStopped` (Traefik.ensure_running called once, result success), `TestNoDuplicateBootstrap` (exactly 1 call per invocation) |
| `tests/test_sandbox_runtime_deploy.py` | Added `mock_infra.assert_called_once()` to `test_deploy_operational_runtime_success` |
| `tests/test_environment_supervisor.py` | Added `test_provision_endpoint_triggers_infra_bootstrap` — endpoint → `deploy_operational_runtime` → infra bootstrap end-to-end |

All 12 targeted tests pass. Pre-existing failures in `test_supervisor.py` and `test_daemon_issue_polling.py` are unrelated to T165.
