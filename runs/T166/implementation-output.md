All tests green. Here's a summary of what was changed:

**Files modified:**

`tools/agent_runner/run_sandbox.py`
- `_log_proxy_backend_diagnostics` (lines 314–432): Changed return type from `dict[str, str]` (raw probe results) to a structured `dict` containing:
  - `backend_urls` — canonical Traefik target URLs from `sandbox_backend_urls()`
  - `aliases` — Docker DNS alias names from `sandbox_dns_aliases()`
  - `traefik_probe` — the existing probe results (moved to sub-key instead of top-level return)
  - `traefik_networks` — Traefik container's network membership from `docker inspect`; `[]` if Docker unavailable
  - `api_container` — API container status, restarts, health, networks (promoted from log-only to returned dict)
  - `failure_type` — `"crash_loop"` / `"dns_network"` / `"backend_app"` / `"unknown"` based on probe + container state
- `_wait_for_proxy_url`: Added doc comment clarifying that these retries check Traefik reachability only; backend readiness is handled by `healthcheck.sh`

**Files created:**

`tests/test_log_proxy_diagnostics.py` — 5 new tests covering: required dict keys, `failure_type == "crash_loop"`, `failure_type == "dns_network"`, `traefik_networks` populated on success, `traefik_networks == []` when Docker unavailable.
