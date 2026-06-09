I now have enough context to write the plan. Here it is:

---

## Objective

Make manual environment deployment (the "main" named environment provisioned via `deploy_operational_runtime`) succeed end-to-end: API and web containers must stay running after compose up, proxy routes must resolve to healthy backends, and when a container crashes the pipeline must fail early with container logs instead of silently running `healthcheck.sh` against dead backends.

## Included

**1. Investigate the container crash (prerequisite — Coder must do this first)**

Run against the `cf23c1149f36` sandbox containers:
```bash
docker ps -a | grep cf23c1149f36
docker logs <compose-project>-api-1 --tail=200
docker logs <compose-project>-web-1 --tail=200
docker inspect <compose-project>-api-1
```
Identify exit code and the exact error. Then fix the root cause (candidates: missing env var, volume mount path wrong, app import error, port conflict). The fix may be in `docker-compose.yml`, `services/control_api/main.py`, `deploy/.env.example`, or `sandbox_runtime_deploy.py:_extra_env_for_state()`.

**2. `.ai-dev-factory/scripts/start.sh` — add post-compose container liveness check**

After `docker compose up -d` and before the network attachment block, verify that each routed service (`api`, `web`) is in `running` state:
- Use `docker compose ps --format json` or `docker inspect` to check `State.Status`
- If a container is `exited`, print its recent logs (`docker logs --tail 50`) and `exit 1`
- This makes `start.sh` fail immediately when containers crash, rather than silently proceeding to network attachment

**3. `tools/agent_runner/run_sandbox.py:_log_proxy_backend_diagnostics()` — add container logs**

When the API container status is `exited` (or `restarting`), capture recent container logs via `docker logs --tail 30` and include them in the returned diagnostics dict under key `api_container_logs`. This feeds directly into `validation.json` and the environment logs UI.

**4. `tools/agent_runner/run_sandbox.py:_after_start()` — fail early on `crash_loop`**

Currently only `dns_network` is treated as fatal. Add `crash_loop` as a second fatal failure type: when `_proxy_diagnostics[0].get("failure_type") == "crash_loop"`, log a summary (container status, exit code, recent logs from diagnostics dict), then `return False`. This prevents `healthcheck.sh` from running against a crashed backend.

**5. `services/control_api/services/sandbox_runtime_deploy.py:_register_proxy_routes_after_compose()` — same crash_loop early exit**

Mirror fix #4 for the environment provisioning path: when `_backend_diag.get("failure_type") == "crash_loop"`, return an actionable error string (include container exit code and the first lines of container logs from the diagnostics) instead of `return None`.

**6. Tests**

- `tests/test_sandbox_runtime_deploy.py`: add test that `_register_proxy_routes_after_compose()` returns a non-None error when `failure_type == "crash_loop"`
- `tests/test_run_sandbox.py` (or `test_proxy_route_wait.py`): add test that `_after_start()` returns `False` when diagnostics shows `crash_loop`

## Excluded

- Changes to `deployer_runner.py` (deployer-managed CI/CD deployments — must remain unchanged)
- Changes to healthcheck timing parameters (`HEALTHCHECK_RETRIES`, `HEALTHCHECK_DELAY`)
- Changes to `_wait_for_proxy_url()` — its semantics (any HTTP = Traefik alive) are correct and must stay
- Changes to the Traefik configuration or route file format
- Refactoring `_run_scripts()` callback interface
- Any work on the web container's startup logic unless investigation shows it is the failure source

## Acceptance criteria

- Running the environment provisioning for "main" (sandbox `cf23c1149f36` or a fresh equivalent) results in all 4 healthcheck probes passing
- `start.sh` exits non-zero and prints container logs if `api` or `web` container has `Status: exited` after `docker compose up -d`
- When `failure_type == "crash_loop"` is detected, the pipeline stops before `healthcheck.sh` and the `run.log` includes container exit code and recent container output
- `validation.json` includes an `api_container_logs` field when the backend is unhealthy
- Deployer-managed deployments (`deployer_runner.py` path) are unchanged and continue to pass existing tests
- `pytest tests/test_sandbox_runtime_deploy.py tests/test_proxy_route_wait.py` passes with the new test cases added
