Now I have everything I need. Here is the implementation plan:

---

## Objective

Enrich `_log_proxy_backend_diagnostics` to return a structured dict that includes backend URLs, DNS aliases, Traefik container networks, and API container runtime state (status, restarts, health), so `validation.json` contains enough context to distinguish a DNS/network failure from a backend crash loop without relying on logs alone.

## Included

### `tools/agent_runner/run_sandbox.py`

**`_log_proxy_backend_diagnostics(sandbox_id, log_path) -> dict`**

Change the return type from the flat `dict[str, str]` (Traefik probe results only) to a structured dict:

```python
{
    "backend_urls":      {"api": "http://sandbox-<slug>-api:8080", "web": "http://..."},
    "aliases":           {"api": "sandbox-<slug>-api", "web": "sandbox-<slug>-web"},
    "traefik_probe":     {"api": "reachable" | "failed: ...", "web": ...},
    "traefik_networks":  ["ai-dev-factory-runtime", ...],  # or [] / None if unavailable
    "api_container": {
        "name":     "sandbox-<slug>-api-1",
        "status":   "running" | "exited" | ...,
        "restarts": 0,
        "health":   "healthy" | "unhealthy" | "none",
        "networks": ["ai-dev-factory-runtime", ...]
    },
    "failure_type": "dns_network" | "crash_loop" | "backend_app" | "unknown"
}
```

Concrete changes inside the function:

1. Retrieve `backend_urls` from `sandbox_backend_urls(sandbox_id)` and `aliases` from `sandbox_dns_aliases(sandbox_id)` — already computed, just add them to the dict instead of only logging.
2. Move the existing `probe_backend_from_traefik_container` result under key `traefik_probe` instead of returning it as the whole result.
3. Add a `docker inspect <traefik_cid>` call to extract `NetworkSettings.Networks` keys → `traefik_networks`. Log the result. Skip silently if Docker unavailable or container id is `None`.
4. Promote the existing `docker inspect <api_container>` data (status, restarts, health, networks) from log-only to also stored in the returned `api_container` sub-dict.
5. Compute `failure_type` after probe + container inspect:
   - `"crash_loop"` if `api_container.restarts > 0` AND `api_container.status != "running"`
   - `"dns_network"` if `traefik_probe.api` starts with `"failed:"` AND `api_container.status == "running"`
   - `"backend_app"` if `traefik_probe.api == "reachable"` AND container is running but `/health` returned non-2xx (no direct signal here — leave as `"backend_app"` when probe succeeds but route returns 502 in the outer context)
   - `"unknown"` otherwise

**`_wait_for_proxy_url(url, log_path, *, timeout_s)`**

Add a clarifying comment (one line) making the retry contract explicit: retries here check route/Traefik reachability only (any HTTP response = Traefik is forwarding); backend readiness retries are handled in `healthcheck.sh` via `HEALTHCHECK_RETRIES`/`HEALTHCHECK_DELAY`.

### `tests/test_log_proxy_diagnostics.py` (new file)

Add unit tests for `_log_proxy_backend_diagnostics` covering:
- returned dict contains `backend_urls`, `aliases`, `traefik_probe`, `api_container` keys
- `failure_type == "crash_loop"` when restarts > 0 and container exited
- `failure_type == "dns_network"` when probe fails and container running
- `traefik_networks` present when `docker inspect` succeeds
- `traefik_networks` absent or `[]` when Docker unavailable (no exception raised)

## Excluded

- Fixing the actual root cause of 502 (network architecture, Traefik attachment timing, backend startup ordering)
- Changes to `proxy_network.py` — alias normalization already implemented
- Changes to `proxy_route_files.py` — probe function already implemented
- Changes to `proxy_manager.py` — registration logging already complete
- Changes to `sandbox_runtime_deploy.py` — already calls diagnostics on both success/failure branches
- Changes to `healthcheck.sh` — retries, HTTP code reporting, and proxy-infra separation already in place
- Changes to `_write_validation_json` — already accepts and persists `backend_diagnostics` as-is
- Docker Compose generation or network alias generation changes

## Acceptance criteria

- `validation.json` written on any deploy (success or failure) contains `backend_diagnostics.backend_urls`, `backend_diagnostics.aliases`, `backend_diagnostics.traefik_probe`, `backend_diagnostics.api_container` (with `status`, `restarts`, `health`, `networks`), and `backend_diagnostics.failure_type`
- `validation.json` contains `backend_diagnostics.traefik_networks` when the Traefik container is running and `docker inspect` succeeds
- A crash-loop scenario (container exited, restarts > 0) produces `failure_type == "crash_loop"` in `validation.json`
- A DNS/network failure scenario (Traefik probe fails, container running) produces `failure_type == "dns_network"` in `validation.json`
- All existing `tests/test_proxy_backend_probe.py` tests continue to pass (no changes to `probe_backend_from_traefik_container`)
- New tests in `tests/test_log_proxy_diagnostics.py` pass
- Existing deployer and environment flows are unaffected (no breaking change to `_write_validation_json` signature or `validation.json` schema for callers that don't read `backend_diagnostics`)
