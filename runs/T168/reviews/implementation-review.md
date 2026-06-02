Now I have everything I need. Let me write the structured review.

---

## PR Review — T168: Fix SANDBOX_ID Mismatch

### Summary of changes

Two files changed against the plan's 5 items:

| Plan item | Expected file | Status |
|-----------|--------------|--------|
| 1. Snapshot/restore SANDBOX_ID | `start.sh` | Done |
| 2. Explicit SANDBOX_ID in `docker compose` call | `start.sh` | Done |
| 3. Pre-flight consistency check | `sandbox_runtime_deploy.py` | Done |
| 4. Log expected alias in `ProxyManager.register()` | `proxy_manager.py` | Pre-existing — no change needed |
| 5. Verify probe uses canonical alias | `proxy_route_files.py` | Pre-existing — no change needed |

Plan items 4 and 5 were already implemented before this ticket. Correct that the coder made no change.

---

### Correctness vs. ticket requirements

**Root cause addressed — YES.** The actual bug was `start.sh` sourcing `deploy/.env` after SANDBOX_ID had been injected from the process env, which could overwrite (or not re-apply) the caller-supplied value. The snapshot/restore pattern (`__SB_SANDBOX_ID` → restore after source) is the right fix and mirrors the existing pattern for all other injected env vars.

**Canonical propagation — YES.** `_extra_env_for_state()` has always set `"SANDBOX_ID": state.id` (line 75), which feeds into `start.sh`. The new snapshot/restore ensures `deploy/.env` cannot shadow it.

**Fail-fast on missing SANDBOX_ID — PARTIAL.**

- `start.sh`: The guard at lines 66–71 fires when `COMPOSE_PROJECT_NAME` is set but `SANDBOX_ID` is empty. This is correct for named-environment mode. The main/default runtime (no `COMPOSE_PROJECT_NAME`) is intentionally not guarded, preserving the `${SANDBOX_ID:-default}` compose fallback for non-sandboxed runs.
- `sandbox_runtime_deploy.py`: The pre-flight at lines 347–371 catches an empty `SANDBOX_ID` before any script runs, with a clear error message and proper supervisor cleanup.

**Pre-flight mismatch check is logically dead code.** Lines 361–371 check `sandbox_id_env != state.id`. But `extra_env` is always built by `_extra_env_for_state(state, ...)` on line 221, which sets `"SANDBOX_ID": state.id` verbatim. In the current call graph, these two values are always identical — this branch can never fire.

The dead branch causes no incorrect behavior (the logic is sound), but it introduces code that can never be exercised by tests and creates false confidence. It should either be removed or moved to a call site where the mismatch is actually possible (e.g. a future API where callers supply `extra_env` directly).

**Acceptance criteria coverage:**

| Criterion | Met? |
|-----------|------|
| `docker inspect` shows `sandbox-main-api` | Yes — aliases follow SANDBOX_ID from start.sh |
| Route file points to `sandbox-main-api` | Yes — pre-existing `sandbox_backend_urls()` in proxy_manager |
| `wget http://sandbox-main-api:8080/health` succeeds | Yes — probe uses `sandbox_dns_aliases(sandbox_id)` |
| No `sandbox-default-*` unless env id is `default` | Yes — upstream propagation now correct |
| Fail early on missing SANDBOX_ID | Yes (both layers) |
| Multiple concurrent environments | Yes — no global state, per-`state.id` isolation |
| No 502 after deploy | Yes — alias and route now consistent |

---

### Code quality

**`start.sh`** — The change integrates cleanly into the existing snapshot/restore block. SANDBOX_ID is exported alongside other env vars, the unset block cleans up the temp variable, and the guard provides a clear error message to stderr. Well-scoped.

**`sandbox_runtime_deploy.py`** — Pre-flight check follows the existing error-return pattern: log, stop supervisor, persist failed phase, return `OperationalDeployResult(success=False)`. The error messages are precise and include the expected alias dictionary in the mismatch case — genuinely useful for debugging.

Minor placement concern: the supervisor is started before the pre-flight check (line 262 vs. line 347). If the pre-flight fails, the supervisor is correctly cleaned up, but we paid to start it unnecessarily. This is a minor efficiency issue, not a correctness issue. Moving the pre-flight above `_start_sandbox_supervisor` would be cleaner but is not blocking.

---

### Issues

**Blocking:** None.

**Non-blocking:**

1. **Dead code (lines 361–371 in `sandbox_runtime_deploy.py`).** The `sandbox_id_env != state.id` branch is unreachable in the current call graph. Either remove it or add a comment explaining it is a defensive guard for future callers that may supply a custom `extra_env`.

2. **Supervisor started before pre-flight.** Minor resource waste on a pre-flight failure. Consider reordering if the function is refactored later.

3. **No new unit tests.** The pre-flight logic is simple and low-risk, but a test exercising the empty-SANDBOX_ID path would prevent regressions if `_extra_env_for_state` is ever changed. Not required by the ticket but recommended.

---

### Security / safety

No security concerns. The fix reduces the attack surface by eliminating a silent env-var override path. No secrets are logged. Error messages contain only the sandbox slug (not credentials or tokens).

---

### Conclusion

The implementation correctly fixes the root cause — SANDBOX_ID being lost during `deploy/.env` sourcing in `start.sh` — and adds a defensive pre-flight layer in the Python deploy flow. The two-layer approach (shell + Python) is appropriate. Scope is tightly bounded to the ticket. The one dead-code branch (pre-flight mismatch check) is a minor code quality issue, not a functional defect.

IMPLEMENTATION_APPROVED
