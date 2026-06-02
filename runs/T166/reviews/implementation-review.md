I now have enough information to write the review.

---

## Implementation Review — T166: Diagnose and fix routed backend 502 after route registration

### Summary

The implementation is scoped to enriching `_log_proxy_backend_diagnostics` in `tools/agent_runner/run_sandbox.py` to return a structured diagnostics dict, and adding a new test file `tests/test_log_proxy_diagnostics.py`. This exactly matches the plan.

---

### Correctness relative to ticket requirements

**Req 1 — Diagnostic logging around proxy validation**: Satisfied. The enriched function logs sandbox id, Docker-safe aliases, Traefik container id, probe results for both API and web, Traefik networks, and API container state (status, restarts, health, networks). Each logged field is clearly labelled.

**Req 2 — Validate backend reachability from Traefik container**: Satisfied. `probe_backend_from_traefik_container` (already in `proxy_route_files.py`) is called and its result is stored under `traefik_probe`. The function runs `docker exec <traefik-cid> wget -qO- --timeout=5 <alias>:<port><path>` for both `api` and `web`.

**Req 3 — Route file backend URLs using canonical aliases**: Satisfied. `sandbox_backend_urls` already generates `http://sandbox-<slug>-api:8080` / `http://sandbox-<slug>-web:80` via `proxy_network.py`. These are now also persisted in `validation.json` under `backend_diagnostics.backend_urls`.

**Req 4 — Normalize sandbox ids for Docker DNS**: Satisfied. `_to_docker_safe_alias` in `proxy_network.py` lowercases and strips all non-`[a-z0-9-]` characters, so `ai-dev-factory-20260601T194957` → `ai-dev-factory-20260601t194957`. Route file URLs and DNS aliases are consistent. (Pre-existing implementation, correctly left untouched per the plan.)

**Req 5 — Improve healthcheck timing and readiness reporting**: Partially addressed. The clarifying comment was added to `_wait_for_proxy_url` (lines 299–301) distinguishing Traefik reachability retries from backend readiness retries handled by `healthcheck.sh`. The `failure_type` field now distinguishes crash-loop from DNS/network failure from backend-app failure. No changes to `healthcheck.sh` itself, which is explicitly excluded by the plan.

---

### Scope compliance

The implementation is correctly bounded. Excluded files (`proxy_network.py`, `proxy_route_files.py`, `proxy_manager.py`, `sandbox_runtime_deploy.py`, `healthcheck.sh`, `_write_validation_json` signature) are untouched. No new dependencies introduced.

---

### Code quality and safety

**Robustness**: All `subprocess.run` calls use `check=False` + `timeout=10` + `capture_output=True`. The outer `try/except` on each Docker inspect block catches `FileNotFoundError`, `TimeoutExpired`, `OSError`, and `json.JSONDecodeError` — the function never raises. The `ImportError` guard on service imports returns `{}` gracefully for environments without the control_api layer.

**Logic correctness**:

```python
if api_restarts > 0 and api_status != "running":
    failure_type = "crash_loop"
elif api_probe.startswith("failed:") and api_status == "running":
    failure_type = "dns_network"
elif api_probe == "reachable" and api_status == "running":
    failure_type = "backend_app"
else:
    failure_type = "unknown"
```

The ordering is correct: crash-loop takes precedence over dns_network when a restarting container happens to be running at inspection time.

**Integration path**: In the 502 scenario, `_wait_for_proxy_url` returns `True` immediately on the first 502 (an `HTTPError` is caught and treated as "Traefik forwarding"). Then `_log_proxy_backend_diagnostics` runs unconditionally. `_proxy_diagnostics[0]` is populated and `_write_validation_json` stores it under `backend_diagnostics`. This correctly produces actionable diagnostics in the exact scenario described in the ticket.

**One pre-existing inconsistency (not introduced here)**: For sandbox IDs containing underscores, `_to_docker_safe_alias` strips them (e.g. `my_project` → `myproject`) while `normalize_compose_project_name` allows them (e.g. `my_project` stays `my_project`). This means DNS alias names and container inspect names can differ for such IDs. This is out of scope for this ticket and does not affect typical sandbox IDs which use only hyphens.

---

### Test quality

All 5 plan-required tests are present and correct:

| Test | Coverage |
|---|---|
| `test_returned_dict_contains_required_keys` | All 6 top-level keys + 5 `api_container` sub-keys |
| `test_failure_type_crash_loop` | `restarts=3`, `status="exited"` → `"crash_loop"` |
| `test_failure_type_dns_network` | probe `failed:`, container `running` → `"dns_network"` |
| `test_traefik_networks_populated_when_inspect_succeeds` | Two network names from inspect |
| `test_traefik_networks_empty_when_docker_unavailable` | `FileNotFoundError` → `traefik_networks == []`, no exception |

Mocking approach is correct: `from X import Y` inside the function re-binds the local variable from the module attribute on every call, so patching at the module level is effective.

---

### Blocking issues

None.

---

### Minor observations

1. `_proxy_diagnostics` is not populated when route registration itself fails (`api_url is None`). In that scenario, `validation.json` has no `backend_diagnostics`. This is acceptable — the 502 scenario requires route registration to succeed.

2. No test for `failure_type == "backend_app"` or `failure_type == "unknown"`. Neither was required by the plan.

3. The `_wait_for_proxy_url` clarification was added as docstring lines rather than a separate comment, which is a minor improvement over what the plan specified.

---

IMPLEMENTATION_APPROVED
