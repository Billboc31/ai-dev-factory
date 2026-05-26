Now I have a thorough picture of the system. Let me produce the plan.

## Objective

Introduce a generic undeploy and cleanup lifecycle for sandbox runtimes so that sandbox deletion stops all runtime services, releases all resources, and removes all stale state before filesystem removal — eliminating orphan processes, compose projects, and stale registry entries.

## Included

### 1. Extend `deploy.yml` schema — `services/control_api/services/deployer_runner.py`
- Add optional `undeploy:` section mirroring the `components` list (executed in reverse order)
- Add optional `cleanup:` section for post-undeploy hooks (data dir removal, volume pruning)
- Each step supports same `type: docker | host` structure as deploy components
- Extend `DeployProfile` dataclass and `_load_deploy_profile()` to parse the new sections

### 2. Generic `UndeployRunner` class — `services/control_api/services/undeploy_runner.py` (new file)
- `run_undeploy(profile, compose_project, env_file, project_root, sandbox_id)` — execute undeploy steps sequentially with per-step timeout (mirrors component execution in `deployer_runner.py`)
- `run_cleanup(profile, sandbox_dir, runtime_root, sandbox_id)` — execute cleanup hooks, then remove stale pid files (`*.pid`), stale lock files (`*.lock`), and clear sandbox state entries
- Both methods must be idempotent: failure on a step logs a warning but does not abort the remaining steps
- For `type: docker` undeploy steps: `docker compose -p {compose_project} --env-file {env_file} down --remove-orphans`
- For `type: host` undeploy steps: execute shell command from project root with same subprocess pattern (stdin=DEVNULL, start_new_session=True, timeout)
- Port slot release happens only after cleanup completes

### 3. Enhance `SandboxManager.destroy()` — `services/control_api/services/sandbox_manager.py`
- Before removing any files: call `UndeployRunner.run_undeploy()` then `UndeployRunner.run_cleanup()`
- If deploy.yml is absent or has no undeploy section: fall back to current `docker compose down` + supervisor termination (preserves backwards compatibility)
- Terminate supervisor process before executing undeploy steps (supervisor should not interfere with undeploy)
- After undeploy: release port slot, prune worktree (`git worktree remove --force`), then `shutil.rmtree` sandbox dir
- `SandboxStatus.destroyed` set only after full cleanup sequence

### 4. Add `stop.sh` to the required scripts pattern — `tools/agent_runner/scripts_validator.py`
- Add `.ai-dev-factory/scripts/stop.sh` to `REQUIRED_FILES`
- `run_sandbox.py`: execute `stop.sh` as a cleanup step after the validation pipeline (success or failure), before removing the per-run sandbox directory and worktree
- `stop.sh` execution must be non-blocking to final cleanup: if `stop.sh` exits non-zero, log the error and continue cleanup

### 5. Stale state cleanup — `services/control_api/services/sandbox_manager.py` + `UndeployRunner`
- Remove `{sandbox_runtime_root}/supervisor.pid` after supervisor termination
- Remove any `*.pid` and `*.lock` files under `sandbox_runtime_root` and `sandbox_dir`
- Clear sandbox entry from port registry (`port-registry.json`) only after compose is confirmed down
- Remove per-run state files: `state/sandbox-{project_id}.json`, `state/deploy-state.json` if they reference this sandbox

### 6. Fix "already running" false-positive — `services/control_api/services/deployer_runner.py`
- In the deploy lock check: verify the pid in the existing lock is still alive (`os.kill(pid, 0)`) before returning "already running"; if dead, release the lock and proceed
- Same check in sandbox status lookup: if `supervisor_pid` is set but process is dead, transition status to `stopped` rather than `running`

### 7. Tests — `tests/test_undeploy_runner.py` (new), `tests/test_sandbox_manager.py` (extended)
- `test_compose_project_stopped_on_destroy`: verify `docker compose down` called with correct project before file removal
- `test_stop_script_executed_on_sandbox_cleanup`: verify `stop.sh` is called and its exit code is tolerated
- `test_runtime_process_terminated_before_file_removal`: supervisor SIGTERM before rmtree
- `test_worktree_removed_after_undeploy`: worktree gone after destroy
- `test_cleanup_idempotency`: calling destroy twice does not raise
- `test_stale_pid_removed`: `.pid` files absent after cleanup
- `test_stale_lock_removed`: `.lock` files absent after cleanup
- `test_recreate_sandbox_after_cleanup`: new sandbox creation succeeds and does not return "already running" after prior destroy
- `test_undeploy_steps_executed_in_reverse_order`: component order reversed vs deploy
- `test_cleanup_without_deploy_yml`: graceful fallback when no deploy.yml present

## Excluded

- AI auto-fix loops or automated remediation
- Cloud or distributed deployment targets
- Monitoring or alerting integration for orphan detection
- Changes to `docker-compose.yml` main stack definition
- Refactoring the deploy pipeline beyond adding the undeploy/cleanup sections
- Migrating existing sandboxes to the new lifecycle retroactively

## Acceptance criteria

- `DELETE /sandboxes/{id}` causes `docker compose down` (or project-defined undeploy steps) to run before `shutil.rmtree`
- After destroy, `docker ps --filter label=com.docker.compose.project={compose_project}` returns no containers
- After destroy, `port-registry.json` contains no entry for the deleted sandbox
- After destroy, no `*.pid` or `*.lock` files remain under the former sandbox runtime root
- After destroy, `GET /sandboxes/{id}` returns 404 (state entry removed)
- Creating a new sandbox for the same project after a full destroy never returns "already running"
- Calling destroy on an already-destroyed sandbox does not raise (idempotent)
- `run_sandbox.py` executes `stop.sh` at the end of each validation run (success or failure path)
- All 10 new tests pass
- No hardcoded `docker`-only logic added to the orchestrator layer; project-agnostic path uses `deploy.yml` undeploy steps
- `deploy.yml` without an `undeploy:` section triggers the generic fallback without error
