I have a complete picture of the implementation. Let me write the review.

---

## Review — T167: Fix Traefik DNS/service discovery

### Summary

The implementation addresses the root cause cleanly and stays within the ticket's scope. Four files were changed or created.

---

### Root cause fix — `deploy/infra/docker-compose.traefik.yml`

**Correct.** The 4-line change from:

```yaml
networks:
  ai-dev-factory-runtime:
    name: ai-dev-factory-runtime
    driver: bridge
```

to:

```yaml
networks:
  ai-dev-factory-runtime:
    external: true
```

directly addresses the root cause. When Docker Compose managed the network with an explicit `name:` + `driver:` declaration, it could silently recreate or shadow the network on `docker compose up`, disconnecting backend containers from Traefik's DNS scope. `external: true` forces Compose to only join, never own. This is the correct fix.

---

### Validation improvements

**`services/control_api/services/sandbox_runtime_deploy.py`**

The refactor of `_register_proxy_routes_after_compose()` (lines 307–316) is correct. Diagnostics now always run (not only on failure), and a `dns_network` failure type produces a specific, actionable error message before falling through to the generic reachability failure. Logic is sound.

One minor observation: `proxy_reachable = True` and `failure_type == "dns_network"` is a logically contradictory state (Traefik reaching the backend is incompatible with a DNS failure). In practice it cannot happen, but the check fires even when `proxy_reachable` is `True`, which means a bug in the diagnostics function could mask a success. Non-blocking — the conservative behavior (fail on any DNS anomaly) is safer than the alternative.

**`tools/agent_runner/run_sandbox.py`** (lines 1189–1195)

Same pattern, host-side flow. Correct. The early `return False` correctly fails the deployment when the backend is running but Traefik can't reach it.

---

### Test suite — `tests/test_traefik_compose_network.py`

Three regression tests pin the fix:
- `external: true` is present
- `driver` key is absent
- `name` key is absent

All 3 pass. This is an appropriate pinning approach for a configuration-level fix. The tests are readable and the assertion messages are clear.

---

### Ticket requirements coverage

| Requirement | Status |
|---|---|
| Traefik compose uses `external: true` | Fixed ✓ |
| Sandbox services attach to shared network with DNS aliases | Already correct in `docker-compose.yml` — `external: true`, `sandbox-${SANDBOX_ID:-default}-{api,web}` aliases ✓ |
| `ensure_runtime_network()` sole owner | Pre-existing, not regressed ✓ |
| Route backend URLs use DNS aliases (not host ports) | Pre-existing via `sandbox_backend_urls()` + `_to_docker_safe_alias()` ✓ |
| Deploy validation fails clearly on DNS/network issues | Added in both deploy flows ✓ |
| No `host.docker.internal` workarounds | Correct ✓ |
| No dynamic `docker network connect/disconnect` | Correct ✓ |
| Multiple concurrent environments supported | Preserved ✓ |

---

### Scope compliance

The coder correctly left unchanged: `docker-compose.yml` (already correct), `proxy_network.py` (already correct), `proxy_manager.py` (already uses `sandbox_backend_urls()`), `infra_service_manager.py` (already calls `ensure_runtime_network()` first). The changeset is minimal and bounded to the ticket.

---

### Findings

**Blocking:** None.

**Minor observations:**
1. The `dns_network` failure check in both deploy flows fires unconditionally (even when `proxy_reachable == True`). In practice this state cannot occur, but it creates a latent logical inconsistency with the diagnostics function. Could be guarded with `if not proxy_reachable and _backend_diag.get(...) == "dns_network":` — but current behavior is conservative and not harmful.
2. No regression test covers `docker-compose.yml` network attachment. The coder documents that it was already correct, which is verifiable, but a pinning test would be additional protection.

Neither observation is blocking.

---

### Conclusion

The implementation is minimal, correct, and correctly scoped. The root cause is addressed. Both deploy flows surface DNS failures clearly. The test suite pins the regression. No blocking issues.

IMPLEMENTATION_APPROVED
