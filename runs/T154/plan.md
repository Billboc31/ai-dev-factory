I have a complete picture. Here is the implementation plan:

---

## Objective

Stabilize the Traefik dynamic route lifecycle so that proxy URLs are confirmed reachable before the healthcheck runs and proxy infrastructure failures are reported separately from application failures. Most defensive primitives (atomic write, idempotent unregister, stale cleanup, test isolation) are already in place; the two remaining gaps are a post-registration readiness wait and failure classification.

## Included

### `tools/agent_runner/run_sandbox.py`

- Add `_wait_for_proxy_url(sandbox_id, log_path, *, timeout_s: int = 15) -> bool` after `_register_proxy_route()`:
  - Polls `http://api.sandbox-{sandbox_id}.ai-dev-factory.localhost` with `urllib.request` (no extra dep)
  - Returns `True` as soon as any HTTP response is received (200, 4xx, 502, 503 all count — any response means Traefik has loaded the route)
  - Returns `False` if every attempt gets a `ConnectionError` or `URLError` within `timeout_s` (Traefik itself is not reachable — infra failure)
  - Poll interval: 1 s; up to `timeout_s` attempts
  - Logs "proxy: route active" on success, "proxy: infra unreachable after Xs" on timeout, with result recorded in the log file
- Wire it in the main flow between `_register_proxy_route()` and `_run_scripts()` (line 977)
- The return value (bool) is used only for logging; it does **not** abort the run — healthcheck.sh performs the authoritative pass/fail judgment

### `.ai-dev-factory/scripts/healthcheck.sh`

- When `SANDBOX_API_URL` is set, probe Traefik availability before app probes:
  - Derive the Traefik entry point from the sandbox pretty URL's host:port (`http://traefik.ai-dev-factory.localhost`)
  - Probe it with `probe "proxy-infra" "http://traefik.ai-dev-factory.localhost"` (reuses existing `probe()`)
  - If that probe fails, emit `"PROXY_INFRA_FAIL"` to stdout before proceeding to app probes (app probes still run — `|| true` already prevents early exit)
- No change to exit logic (`[ "$FAIL" -eq 0 ]` at the end remains the authoritative exit criterion)

### `tests/test_proxy_route_wait.py` (new file)

- `test_wait_returns_true_when_traefik_responds`: mock `urllib.request.urlopen` to return HTTP 503 on first call → assert returns `True`
- `test_wait_returns_false_on_connection_error`: mock `urlopen` to always raise `URLError` → assert returns `False` after timeout
- `test_wait_logs_infra_failure`: verify log file contains "proxy: infra unreachable" when all attempts fail

### `tests/test_healthcheck_classification.py` (new file, or add to existing test_proxy_manager.py)

- `test_healthcheck_emits_proxy_infra_fail`: run healthcheck.sh in a subprocess with `SANDBOX_API_URL` set but Traefik not running (use `nc` mock or inject fake `curl` via `PATH`); assert stdout contains `PROXY_INFRA_FAIL`
- This test may be skipped in CI environments that don't support subprocess bash execution; mark with `pytest.mark.integration`

## Excluded

- HTTPS/TLS and cloud ingress
- Replacing or reconfiguring the global Traefik container
- Changing `ProxyManager` atomic write, idempotent unregister, or stale cleanup (already correct)
- Changing test fixtures that already use `tmp_path` for route directory isolation
- Changing the healthcheck exit code meaning (0 = all pass, non-zero = any fail)
- Modifying `sandbox_manager.py` or undeploy runner

## Acceptance criteria

- `run_sandbox.py` calls `_wait_for_proxy_url()` between `_register_proxy_route()` and `_run_scripts()`; log file records the outcome
- `healthcheck.sh` emits `PROXY_INFRA_FAIL` to stdout when `SANDBOX_API_URL` is set and Traefik is unreachable, before reporting app probe results
- `test_wait_returns_true_when_traefik_responds` passes
- `test_wait_returns_false_on_connection_error` passes
- `test_wait_logs_infra_failure` passes
- No existing test in `tests/test_proxy_manager.py` or `tests/test_sandbox_manager.py` touches the real `~/runtime/ai-dev-factory/proxy/routes` directory (verified by `grep -r "resolve_proxy_routes_dir\|HOST_RUNTIME_ROOT"` in test files — all usages must be mocked or patched)
- `pytest tests/` passes with no regression
