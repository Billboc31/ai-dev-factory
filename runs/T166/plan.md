1202 tests pass; the 49 failures are all in pre-existing subsystems (daemon, control-api endpoints, ticket timeline) that my changes didn't touch. All proxy, sandbox-deploy, and environment tests pass cleanly.

The implementation is complete. Summary of every change made:

| File | What changed |
|------|-------------|
| `proxy_network.py` | `_to_docker_safe_alias()`, `sandbox_dns_aliases()`; `sandbox_backend_urls()` now normalizes the ID |
| `proxy_route_files.py` | New `probe_backend_from_traefik_container()` — `docker exec <traefik> wget` probe, returns `{}` when Docker unavailable |
| `proxy_manager.py` | `register()` now logs sandbox_id, slug, file, backends, Traefik container ID, and calls the backend probe |
| `run_sandbox.py` | `_wait_for_proxy_url` logs `http=<code>`; new `_log_proxy_backend_diagnostics()` (Traefik probe + container inspect); `_write_validation_json()` accepts `backend_diagnostics`; `_after_start()` calls diagnostics and passes them to validation.json |
| `sandbox_runtime_deploy.py` | `_register_proxy_routes_after_compose()` calls `_log_proxy_backend_diagnostics()` on both success and failure; passes results to `_write_validation_json()` |
| `healthcheck.sh` | `RETRIES=${HEALTHCHECK_RETRIES:-6}`, `DELAY=${HEALTHCHECK_DELAY:-5}`; `probe()` reports `http=<code>` in FAIL lines |
| `tests/test_proxy_route_wait.py` | Updated assertion to expect `http=503` format |
| `tests/test_proxy_network.py` | Updated alias-format test (lowercase); added 8 new tests for normalization |
| `tests/test_proxy_backend_probe.py` | New file — 6 tests for `probe_backend_from_traefik_container` |
