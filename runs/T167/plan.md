I now have a complete picture. Here is the implementation plan:

---

## Objective

Fix Traefik's inability to resolve routed backend containers by correcting the shared ingress network ownership in `docker-compose.traefik.yml` (root cause), and surface DNS/network failures as deployment failures instead of silent warnings in both deploy flows.

## Included

**`deploy/infra/docker-compose.traefik.yml`** — root cause fix  
- Remove `name: ai-dev-factory-runtime` and `driver: bridge` from the network block  
- Replace with `external: true` so Traefik joins the network created by `ensure_runtime_network()` instead of managing it independently  

**`tools/agent_runner/run_sandbox.py`** — validation fix (host-side flow)  
- In `_after_start()`, after `_log_proxy_backend_diagnostics()` populates `_proxy_diagnostics[0]`, check `failure_type == "dns_network"` (backend is running but Traefik probe fails)  
- If true, append a clear log message and return `False` to fail deployment  

**`services/control_api/services/sandbox_runtime_deploy.py`** — validation fix (container-side flow)  
- In `_register_proxy_routes_after_compose()`, after both `_wait_for_proxy_url()` and `_log_proxy_backend_diagnostics()` calls, check `_backend_diag.get("failure_type") == "dns_network"`  
- If true, return an explicit error string: `"DNS/network failure: backend is running but unreachable from Traefik — check shared ingress network"`  

**`tests/test_traefik_compose_network.py`** (new file)  
- Parse `deploy/infra/docker-compose.traefik.yml` with PyYAML  
- Assert `networks["ai-dev-factory-runtime"]["external"] is True`  
- Assert `"driver"` and `"name"` keys are absent from the network block  

## Excluded

- `docker-compose.yml` — already correct (`external: true`, aliases using `${SANDBOX_ID}`)  
- `proxy_network.py` — already correct (lowercase Docker-safe alias generation)  
- `proxy_manager.py` — probe is already called; no change to register() probe behavior  
- `infra_service_manager.py` — `ensure_runtime_network()` already called before Traefik starts  
- `_wait_for_proxy_url()` timing or retry behavior  
- Dynamic `docker network connect/disconnect` workarounds  
- `healthcheck.sh` or `start.sh` script changes  
- Multiple-environment load testing  

## Acceptance criteria

- `docker-compose.traefik.yml` declares `ai-dev-factory-runtime` with `external: true` only; no `driver` or `name` keys present  
- `pytest tests/test_traefik_compose_network.py` passes  
- `docker exec <traefik> wget http://sandbox-<slug>-api:8080/health` succeeds after deploy (Traefik and backend containers are on the same network)  
- A deployment where `failure_type == "dns_network"` is classified (backend running, probe fails) results in `success=False` and an explicit log message in both the host-side and container-side deploy flows  
- `pytest tests/` passes without regressions  
