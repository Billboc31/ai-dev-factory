36/36 tests pass. Here's a summary of what was implemented for T148:

---

## Changes summary

**Files created:**
- `services/control_api/services/undeploy_runner.py` — new generic undeploy/cleanup module with `run_undeploy()` and `run_cleanup()` functions; idempotent, step failures log warnings without aborting
- `tests/test_undeploy_runner.py` — 12 tests covering reverse-order execution, fallback without deploy.yml, stale pid/lock removal, cleanup hooks, stop.sh execution

**Files modified:**
- `services/control_api/models/schemas.py` — added `undeploy: list[DeployComponent]` and `cleanup: list[DeployComponent]` fields to `DeployProfile`
- `services/control_api/services/deployer_runner.py` — updated `_load_deploy_profile()` to parse the new `undeploy` and `cleanup` sections from `deploy.yml`
- `services/control_api/services/sandbox_manager.py` — rewrote `destroy()` to: terminate supervisor first, load deploy profile, call `run_undeploy()` + `run_cleanup()`, remove worktree, release port slot, then `rmtree`; added `_pid_alive()` helper; fixed `status()` to transition dead supervisor PIDs from `running` → `stopped`
- `tools/agent_runner/run_sandbox.py` — added `_run_stop_script()` function and called it in the `finally` block after the validation pipeline (success or failure path), before stopping the supervisor
- `tests/test_sandbox_manager.py` — added 5 tests: compose down on destroy, SIGTERM ordering before rmtree, worktree removal, idempotency, recreate-after-cleanup
