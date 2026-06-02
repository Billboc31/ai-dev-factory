I now have a complete picture of the codebase. Let me produce the plan.

---

## Objective

Confirm and test that Environment create/redeploy flows call the canonical infra bootstrap (`run_sandbox._ensure_required_infra` → `ensure_required_infra` → `ensure_runtime_network` + `TraefikManager.ensure_running`) before route registration and healthchecks — exactly as the standalone Deployer pipeline does — and add tests that verify this behavior when Traefik is initially stopped.

## Included

**Code audit (read-only, no changes unless gaps are found)**

- `services/control_api/services/sandbox_runtime_deploy.py` line ~278: confirm `rs._ensure_required_infra(log_path)` is called before `_register_proxy_routes_after_compose()` and before any `_run_scripts()` call.
- Confirm `ProxyManager(auto_ensure_infra=False)` is used in `_register_proxy_routes_after_compose()` (no duplicate bootstrap).
- Confirm `infra_service_manager._ensure_traefik_reverse_proxy()` calls both `ensure_runtime_network()` and `TraefikManager().ensure_running()`.
- Check the supervisor (`services/supervisor/main.py`) for any environment `start` endpoint that bypasses `deploy_operational_runtime()`. If one exists, add an `rs._ensure_required_infra()` call there too.
- Confirm `provision_environment()` and `redeploy_environment()` in `environment_provision.py` both reach `deploy_operational_runtime()` without an early return that could skip the infra step.

**New file: `tests/test_environment_infra_bootstrap.py`**

Three test classes or groups:

1. `TestInfraBootstrappedOnProvision` — patches `run_sandbox._ensure_required_infra` and asserts it is called with a log-path argument during a `deploy_operational_runtime()` invocation in `"environment"` mode.

2. `TestTraefikInitiallyStopped` — patches `TraefikManager.ensure_running` to return `True` on first call (simulating stopped → auto-started), patches the rest of the pipeline (supervisor, scripts, route file, proxy URL probe); assert `deploy_operational_runtime()` returns `success=True` and `route_registered=True`.

3. `TestNoduplicateBootstrap` — calls `deploy_operational_runtime()` twice in sequence on the same sandbox; assert `_ensure_required_infra` is called exactly once per invocation (idempotent, no stacking).

Each test must use the same `_sample_state` helper pattern already used in `test_sandbox_runtime_deploy.py`.

**`tests/test_sandbox_runtime_deploy.py`** (minor addition)

- In `test_deploy_operational_runtime_success`, add an assertion that the `_ensure_required_infra` mock was called at least once (currently it is patched but the call count is never asserted).

**`tests/test_environment_supervisor.py`** (minor addition)

- Add a test that calls `POST /environments/provision` with a real (non-mocked) `deploy_operational_runtime` stub that asserts `_ensure_required_infra` is triggered, confirming the full call chain from HTTP endpoint → `provision_environment_from_body` → `deploy_operational_runtime` → infra bootstrap.

## Excluded

- Changes to `deployer_runner.py` — the Deployer flow is unchanged and not in scope.
- Changes to `traefik_manager.py` or `infra_service_manager.py` — the bootstrap logic itself is correct.
- Adding a new `POST /environments/{env_id}/start` endpoint — the ticket does not require a new endpoint; if none exists, the plan confirms there is no gap.
- Integration tests that actually run Docker or a live Traefik container — all tests remain unit tests with mocked subprocess and Docker calls.
- Changes to `sandbox_manager.start()` or `restart()` — these are used for sandboxes, not named environments.
- Refactoring `run_sandbox.py` pipeline order.

## Acceptance criteria

- `tests/test_environment_infra_bootstrap.py` exists and `pytest tests/test_environment_infra_bootstrap.py` passes with no failures.
- The test `TestTraefikInitiallyStopped` asserts `TraefikManager.ensure_running` is called once per `deploy_operational_runtime()` and the overall result is `success=True`.
- The test `TestNoduplicateBootstrap` asserts `_ensure_required_infra` call count equals exactly 1 per `deploy_operational_runtime()` invocation.
- `tests/test_sandbox_runtime_deploy.py::test_deploy_operational_runtime_success` asserts `_ensure_required_infra` mock call count ≥ 1.
- `pytest tests/test_environment_supervisor.py` passes — the new endpoint-level test asserts infra bootstrap is triggered.
- Code audit confirms `sandbox_runtime_deploy.py` calls `rs._ensure_required_infra()` before `_register_proxy_routes_after_compose()` with no intervening route writes or healthcheck calls.
- Code audit confirms there is no environment `start` endpoint that bypasses `deploy_operational_runtime()`.
- All pre-existing tests remain green (`pytest tests/` with no regressions).
