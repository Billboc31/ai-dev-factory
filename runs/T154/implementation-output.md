Good — `HOST_RUNTIME_ROOT` is monkeypatched to `tmp_path`, so the test never touches the real directory.

All acceptance criteria from the plan are satisfied. Here's the summary:

**All implementation is complete and was delivered in a prior coder attempt.** The T154 plan required:

1. **`_wait_for_proxy_url()`** in `run_sandbox.py` (lines 277–298) — polls the sandbox API URL, returns `True` on any HTTP response, `False` only on connection-level errors. Wired at line 1005 between `_register_proxy_route()` and `_run_scripts()`. ✓

2. **`healthcheck.sh`** (line 74) — when `SANDBOX_API_URL` is set, probes `http://traefik.ai-dev-factory.localhost` first and emits `PROXY_INFRA_FAIL` on failure before app probes. ✓

3. **`tests/test_proxy_route_wait.py`** — 3 tests covering true/false return and log message. All pass. ✓

4. **`tests/test_healthcheck_classification.py`** — integration test with fake `curl` binary, asserts `PROXY_INFRA_FAIL` in stdout. Passes. ✓

The 54 failures in the full suite are pre-existing in unrelated test files (`test_ticket_timeline.py`, `test_run_daemon.py`, `test_environment_routes.py`), confirmed by running them without any local changes.

**Files delivered (no changes needed — already committed):**
- `tools/agent_runner/run_sandbox.py` — `_wait_for_proxy_url()` added and wired
- `.ai-dev-factory/scripts/healthcheck.sh` — `PROXY_INFRA_FAIL` classification
- `tests/test_proxy_route_wait.py` — new test file
- `tests/test_healthcheck_classification.py` — new test file
