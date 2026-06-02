## Objective

Make Docker Compose interpolation deterministic by replacing fragile shell-env inheritance with an explicit per-invocation env file carrying the runtime `SANDBOX_ID`, and add a `docker compose config` pre-flight validation that fails deployment early if the wrong alias is resolved.

## Included

### `.ai-dev-factory/scripts/start.sh`
- After `SANDBOX_ID` is resolved and exported, write a runtime override file at `${RUN_DIR}/.env.compose` containing `SANDBOX_ID=${SANDBOX_ID}`.
- Replace the current invocation:
  ```bash
  SANDBOX_ID="$SANDBOX_ID" docker compose --env-file deploy/.env up -d
  ```
  with:
  ```bash
  docker compose --env-file deploy/.env --env-file "${RUN_DIR}/.env.compose" config | grep "sandbox-${SANDBOX_ID}-"
  # fail if the above grep exits non-zero
  docker compose --env-file deploy/.env --env-file "${RUN_DIR}/.env.compose" up -d
  ```
- Log: env files used, resolved `SANDBOX_ID`, alias snippet, compose project name.
- If `SANDBOX_ID` is empty at this point, emit an explicit error and exit 1 (do not fall through to the compose invocation).

### `.ai-dev-factory/scripts/stop.sh`
- Apply the same dual `--env-file` pattern when stopping:
  ```bash
  docker compose --env-file deploy/.env --env-file "${RUN_DIR}/.env.compose" down
  ```
  Use the pre-existing `${RUN_DIR}/.env.compose` if present; fall back to `--env-file deploy/.env` only if the runtime file was never written.

### `services/control_api/services/sandbox_manager.py` — `_run_compose()`
- Add `deploy/.env` as the **first** `--env-file` when the file exists at `{sandbox.project_root}/deploy/.env`, so all base config (ports, paths) is present.
- Keep the sandbox-specific env file as the **second** `--env-file` so its `SANDBOX_ID={sandbox_id}` overrides any value that might appear in `deploy/.env`.
- For any invocation where the first element of `*args` is `"up"`, run a `docker compose config` validation step before the actual `up` call:
  - Parse the output to confirm `sandbox-{sandbox.id}-` appears in the alias list.
  - If not, log a warning and return a non-zero exit code immediately (do not proceed with `up -d`).
- Add `logger.info` lines reporting: env files used, resolved `SANDBOX_ID`, effective compose project name.

### `services/control_api/services/deployer_runner.py` — `_inject_compose_flags()`
- When building the injected command, also prepend `--env-file deploy/.env` before `--env-file {env_file}` (the sandbox-specific file), provided `(cwd / "deploy" / ".env").exists()`.
- Add a helper `_validate_compose_config(cmd_prefix, cwd, sandbox_id, log_path)` that runs `docker compose config` with the same flags and greps for the expected alias; returns `False` if the alias is missing.
- Call this helper inside `_do_deploy()` immediately before executing `docker compose up` components, log the result, and return an `ActionResult(ok=False, ...)` if validation fails.

### Tests — `tests/test_sandbox_manager.py`
- Add `test_run_compose_uses_both_env_files`: mock `subprocess.run`, call `manager.start(sandbox_id)`, assert the command list contains both `--env-file deploy/.env` and `--env-file <sandbox.env>` in the correct order (deploy/.env first).
- Add `test_start_validates_compose_config_before_up`: mock compose so that the config call succeeds but contains wrong aliases; assert `start()` returns an error state without calling `up -d`.

### Tests — `tests/test_sandbox_runtime_deploy.py`
- Add `test_deploy_inject_flags_includes_deploy_env`: assert `_inject_compose_flags` produces a command containing `--env-file deploy/.env` before `--env-file <sandbox.env_file>`.
- Add `test_deploy_fails_early_on_wrong_compose_alias`: mock compose config to return `sandbox-default-api`; assert `_do_deploy` returns `ok=False` before any `up` component runs.

## Excluded

- Changes to Traefik route files or the ProxyManager.
- Changes to `deploy/.env.example` or any static env file content.
- Changes to `build.sh` (does not involve SANDBOX_ID interpolation).
- Changes to the UUID-based `sandbox_id` generation logic.
- Multi-compose-file (`--file`) support or changes to `docker-compose.yml` alias syntax.
- Any refactoring of unrelated sandbox lifecycle methods.

## Acceptance criteria

- `docker compose config | grep sandbox-` confirms correct aliases (`sandbox-{SANDBOX_ID}-api`, `sandbox-{SANDBOX_ID}-web`) before any container starts, for both the environment flow (`start.sh`) and the sandbox isolation flow (`sandbox_manager._run_compose`).
- If `SANDBOX_ID` is empty or resolves to "default" when it shouldn't, `start.sh` exits with code 1 and `sandbox_manager.start()` returns `SandboxStatus.error` — no container is brought up.
- `stop.sh` uses the same runtime env file so `docker compose down` tears down the correct project.
- New unit tests pass: `test_run_compose_uses_both_env_files`, `test_start_validates_compose_config_before_up`, `test_deploy_inject_flags_includes_deploy_env`, `test_deploy_fails_early_on_wrong_compose_alias`.
- Existing test suite (`pytest tests/`) continues to pass without modification to any existing test.
- Multiple named environments (e.g., "main" and "feature-x") continue to run concurrently without alias collisions.
