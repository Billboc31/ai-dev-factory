All 83 tests related to the changed files pass. The failures elsewhere are pre-existing and unrelated to this ticket.

Here's a summary of what was implemented:

---

**Files modified:**

1. **`deploy/infra/docker-compose.traefik.yml`** — Root cause fix. Replaced `name: ai-dev-factory-runtime` + `driver: bridge` with `external: true`. Traefik now joins the network created by `ensure_runtime_network()` instead of independently recreating it (which would silently disconnect backend containers).

2. **`tools/agent_runner/run_sandbox.py`** — Host-side validation fix. After diagnostics run in `_after_start()`, if `failure_type == "dns_network"` (backend running but unreachable from Traefik), logs an explicit message and returns `False` to fail the deployment.

3. **`services/control_api/services/sandbox_runtime_deploy.py`** — Container-side validation fix. In `_register_proxy_routes_after_compose()`, consolidated the two separate `_log_proxy_backend_diagnostics()` calls into one, then checks for `dns_network` failure type and returns an explicit error string before falling through to the generic proxy reachability error.

**Files created:**

4. **`tests/test_traefik_compose_network.py`** — 3 tests pinning that `ai-dev-factory-runtime` is declared with `external: true` and no `driver` or `name` keys.
