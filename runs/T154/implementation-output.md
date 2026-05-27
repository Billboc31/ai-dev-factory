All 5 tests pass. Here's what was changed:

**`tools/agent_runner/run_sandbox.py`**
- `_register_proxy_route()` now returns `str | None` — returns `urls.get("api")` on success, `None` on failure (Fix 1)
- `_wait_for_proxy_url()` signature changed from `sandbox_id: str` to `url: str`, removing the hardcoded domain (Fix 1)
- Log messages now distinguish `"proxy: route active (backend healthy)"` (HTTP 200) from `"proxy: route active (backend not healthy yet)"` (HTTP 4xx/5xx) (Fix 3)
- Call site captures `api_url = _register_proxy_route(...)` and only calls `_wait_for_proxy_url(api_url, log_path)` if registration succeeded

**`.ai-dev-factory/scripts/healthcheck.sh`**
- `probe "proxy-infra"` now probes `${SANDBOX_API_URL}` instead of the hardcoded `http://traefik.ai-dev-factory.localhost` (Fix 2)

**`tests/test_proxy_route_wait.py`**
- Updated to pass a URL directly to `_wait_for_proxy_url()`, added a separate test for the HTTP 200 (`backend healthy`) path, updated assertions to match the new log messages
