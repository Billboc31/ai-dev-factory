I have reviewed all the relevant files. Here is the full review.

---

# T170 — Implementation Review

## Summary

The implementation addresses the root cause identified in the ticket: API/Web containers not joining the `ai-dev-factory-runtime` Docker network, preventing Traefik DNS resolution.

Two changes were made:
1. **Primary fix** — post-compose network attachment block in `start.sh`
2. **Defensive fix** — `ensure_runtime_network()` called before `_run_compose` in `SandboxManager.start()`

---

## Correctness vs. Ticket Acceptance Criteria

| Criterion | Status |
|---|---|
| API container attached to `ai-dev-factory-runtime` | ✅ — `docker network connect --alias sandbox-${SANDBOX_ID}-api` |
| Web container attached to `ai-dev-factory-runtime` | ✅ — same for web |
| API/Web retain sandbox default network | ✅ — `docker network connect` only adds, never removes |
| Aliases use correct SANDBOX_ID | ✅ — `sandbox-${SANDBOX_ID}-{api,web}` |
| Traefik can resolve aliases | ✅ — follows from correct attachment |
| Deployment fails clearly if attachment fails | ✅ — post-attach validation block (lines 188–199 in start.sh) |
| Multiple sandboxes coexist without alias collision | ✅ — SANDBOX_ID is per-sandbox unique |

---

## Plan-Fix-v1 Requirements (Required for Approval)

The plan review (PLAN_APPROVED) required specific implementation behaviours:

1. **Fallback framed clearly, not as primary path** — ✅ The comment at `start.sh:136–143` explicitly states "a safety net for older branches/worktrees where the declaration may be absent."

2. **Post-attachment validation with clear error output** — ✅ Lines 188–199 re-inspect both containers and `exit 1` with diagnostic output if either is still unattached.

3. **Log message when repair fires** — ✅ Line 184 emits `"start: runtime network attachment repaired for legacy compose config"` exactly as specified.

---

## Code Quality

**`start.sh`**:
- Idempotency is handled at two levels: pre-connect inspect (skip if already on the network) and post-connect error matching (`already exists|endpoint with name`).
- The `|| true` on the connect command correctly absorbs the exit code, then stderr is parsed explicitly. Logic is: empty output → success; "already exists" pattern → idempotent; any other output → fatal error. This covers all real Docker error modes.
- The compose opts array correctly includes `--env-file deploy/.env` when present, so `COMPOSE_PROJECT_NAME` is conveyed to `docker compose ps` for project scoping. This is consistent with the pre-existing `docker compose up` call pattern in the same script.

**`sandbox_manager.py`**:
- `ensure_runtime_network` is already imported (`line 23`). Addition of the call at line 351 is minimal and placed correctly — before `_run_compose`, preventing the "declared as external but could not be found" hard failure.

---

## Test Coverage

**`test_start_sh_network_attach.py`** — 3 tests via a stateful fake docker binary:
- Missing container → connect called with correct alias for both services — ✅
- Already connected → connect NOT called, idempotent — ✅
- Connect returns "already exists" error → treated as success — ✅

The fake docker implementation correctly uses marker files to simulate per-container state across calls, allowing the post-attach validation to pass or fail realistically.

**`test_sandbox_manager.py`** — 1 new test:
- `test_start_calls_ensure_runtime_network_before_compose_up` verifies ordering via `call_order` list. Correctly patches `ensure_runtime_network` in `sandbox_manager`'s namespace (where it's imported). — ✅

---

## Minor Observations (Non-blocking)

1. **`-p` flag not used in compose opts** — the plan mentioned `docker compose -p "$COMPOSE_PROJECT_NAME" ps -q api`, but the implementation uses `--env-file` to convey project name. This works correctly (Compose reads `COMPOSE_PROJECT_NAME` from env-file) and is consistent with the existing `docker compose up` call. Not a regression.

2. **Existing `mgr.start()` tests now silently call docker** — the unpatched `ensure_runtime_network()` will invoke `docker network create` in `test_lifecycle_transitions` etc. The function never raises and the "already exists" case is silently swallowed, so tests remain green. This is a minor test-cleanliness concern but not a correctness issue.

3. **Post-attach validation skips missing containers** — if a service container never started (compose up failure), the post-attach loop skips it rather than failing. This is acceptable: `set -euo pipefail` would already have exited if compose up returned non-zero. A container that starts and immediately crashes is an edge case outside T170's scope.

---

IMPLEMENTATION_APPROVED
