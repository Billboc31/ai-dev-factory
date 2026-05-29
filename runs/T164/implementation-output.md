All 108 networking/proxy tests pass. Here is a summary of every file changed:

---

## Changes summary

### Infrastructure
| File | Change |
|------|--------|
| `deploy/infra/docker-compose.traefik.yml` | Declares + creates `ai-dev-factory-runtime` bridge network; connects Traefik service to it — Traefik now belongs to the shared ingress network permanently |
| `docker-compose.yml` | Declares `ai-dev-factory-runtime` as external; attaches `api` and `web` services to it with per-sandbox aliases `sandbox-${SANDBOX_ID:-default}-api` / `sandbox-${SANDBOX_ID:-default}-web` |

### Services
| File | Change |
|------|--------|
| `services/control_api/services/proxy_network.py` | **Rewritten**: removed `attach_traefik_to_compose_project`, `detach_traefik_from_compose_project`, `resolve_route_backends`, `host_port_backend_urls`, `compose_service_backend_urls`, `compose_default_network_name`, and all Docker subprocess helpers. Added `RUNTIME_NETWORK_NAME` constant and `sandbox_backend_urls(sandbox_id)` returning deterministic alias URLs |
| `services/control_api/services/proxy_manager.py` | Removed `compose_project` param from `register()` and `unregister()`; replaced `resolve_route_backends(ports, compose_project)` call with `sandbox_backend_urls(sandbox_id)`; removed `detach_traefik_from_compose_project` import and call |
| `services/control_api/services/infra_service_manager.py` | Added `ensure_runtime_network()` (idempotent `docker network create`); called from `_ensure_traefik_reverse_proxy()` so the ingress network is guaranteed before Traefik starts |
| `services/control_api/services/sandbox_manager.py` | Removed `compose_project=` kwarg from both `_proxy.register()` and `_proxy.unregister()` calls |
| `services/control_api/services/sandbox_runtime_deploy.py` | Removed `compose_project=` kwarg from `ProxyManager.register()` call |
| `tools/agent_runner/run_sandbox.py` | Removed `compose_project` param from `_register_proxy_route()` and its call site |

### Tests
| File | Change |
|------|--------|
| `tests/test_proxy_network.py` | **Rewritten**: 6 new tests for `RUNTIME_NETWORK_NAME` and `sandbox_backend_urls()` |
| `tests/test_proxy_manager.py` | Replaced port-content assertions with alias-URL assertions; removed `compose_project` args; renamed `test_register_custom_host_still_writes_port` → `test_register_custom_host_writes_alias_backends` |
| `tests/test_proxy_route_files.py` | Removed the mock for `attach_traefik_to_compose_project` and `compose_project` args; fixed alias-URL assertion in redeploy test |
| `tests/integration/test_multi_env_networking.py` | **New**: 5 tests — concurrent sandboxes have unique aliases, separate route files, no cross-contamination, no `host.docker.internal` |
| `tests/integration/test_redeploy_stability.py` | **New**: 4 tests — repeated register leaves single file with stable alias backend and no tmp files |
| `tests/integration/test_env_cleanup.py` | **New**: 4 tests — destroy one sandbox leaves other untouched, infra dashboard preserved, stale cleanup correct |
