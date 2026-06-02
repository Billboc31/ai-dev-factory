The plan is written to `runs/T169/prompts/planner-attempt-2.md`. Here's a summary:

---

## Objective

Make Docker Compose interpolation deterministic by replacing shell-env inheritance with an explicit per-invocation runtime env file and adding a `docker compose config` pre-flight validation that fails deployment early if the wrong alias is resolved.

## Included

**`.ai-dev-factory/scripts/start.sh`**
- Write `${RUN_DIR}/.env.compose` containing `SANDBOX_ID=${SANDBOX_ID}` after the variable is resolved
- Replace `SANDBOX_ID="$SANDBOX_ID" docker compose --env-file deploy/.env up -d` with `docker compose --env-file deploy/.env --env-file "${RUN_DIR}/.env.compose"` for both the config validation and the `up -d`
- Fail immediately if `SANDBOX_ID` is empty or if config validation shows the wrong alias

**`.ai-dev-factory/scripts/stop.sh`**
- Same dual `--env-file` pattern, reading the pre-existing runtime env file

**`services/control_api/services/sandbox_manager.py`**
- `_run_compose()`: add `deploy/.env` as the first `--env-file` and keep the sandbox-specific env file second (so its `SANDBOX_ID=<uuid>` wins)
- Validate with `docker compose config` before `up -d`; return error state if alias is wrong

**`services/control_api/services/deployer_runner.py`**
- `_inject_compose_flags()`: also prepend `--env-file deploy/.env` before the sandbox env file
- Add config validation helper called before any `docker compose up` component

**Tests**: 4 new unit tests covering env-file ordering and early-failure on wrong alias.

## Excluded
Traefik/ProxyManager, `.env.example`, `build.sh`, `docker-compose.yml` alias syntax, UUID generation, multi-file compose.

## Acceptance criteria
- `docker compose config` shows correct `sandbox-{SANDBOX_ID}-api/web` aliases before any container starts, in both the environment flow and sandbox isolation flow
- Empty or wrong SANDBOX_ID causes `start.sh` to exit 1 and `sandbox_manager.start()` to return error, no container started
- All existing tests continue to pass; 4 new tests pass
