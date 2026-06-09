I have all the information needed. Let me write the review.

---

## Review — T180: Healthcheck failure logs must prioritize actionable Traefik and proxy diagnostics

### Context

This is a second-attempt review. The first review (IMPLEMENTATION_FIX_REQUIRED) identified two blocking issues:
1. `backend_diagnostics` was fetched from the API but silently ignored in the UI
2. No unit tests for `_parse_healthcheck_output`

The latest commit (cc270788) addresses both. This review covers the full implementation.

---

### Acceptance Criteria Verification

| Criterion | Status |
|---|---|
| Healthcheck failures surface actionable diagnostics immediately | ✅ `HealthcheckDiagnostics` renders before raw logs |
| Traefik/proxy routing issues visible without raw logs | ✅ `traefik_probe` table in `BackendDiagnostics` |
| Tested URLs and HTTP codes displayed clearly | ✅ Probe table with URL + HTTP columns |
| validation.json diagnostics surfaced in UI | ✅ `failure_type` with labels, container status, networks |
| Raw full logs still accessible | ✅ Polling and `<pre>` block unchanged, rendered below diagnostics |
| Existing step summary behavior unchanged | ✅ No changes to step summary logic |

---

### Backend — `run_sandbox.py`

**`_parse_healthcheck_output`** (lines 138–169): Clean regex parsing of healthcheck stdout into structured `probes` array. Returns `passed`, `failed`, `exit_code`, `raw_stderr`. The exception guard at the call site (`except Exception: pass`, line 790) prevents any parse failure from killing the run — correct.

**`_log_proxy_backend_diagnostics`** (lines 359–489): Comprehensive, never-raises function. Docker inspect calls have 10s timeouts and catch `FileNotFoundError`, `TimeoutExpired`, `JSONDecodeError`. Import failures return `{}` gracefully. Failure classification (`crash_loop`, `dns_network`, `backend_app`, `unknown`) covers the main real-world cases.

**Timing concern — resolved by design**: Backend diagnostics are captured in the `_after_start` callback (after `start.sh`, before healthcheck). This is intentional and correct — the proxy state must be captured at the moment routing is established, so that if `healthcheck.sh` fails, the diagnostic snapshot reflects the actual network state at that time. Waiting until after healthcheck would capture a potentially different or degraded state.

**One minor observation**: When `start.sh` succeeds and healthcheck passes, `backend_diagnostics` are still written to `validation.json` unnecessarily. Not a bug — `backend_diagnostics or None` suppresses it if empty, and in the success path the diagnostics are harmless noise. Out of scope to fix here.

---

### Backend — `/diagnostics` endpoint (`runtime_dashboard.py`, lines 284–302)

- Input sanitized with `re.fullmatch(r"[a-zA-Z0-9_\-]+", sandbox_id)` — path traversal protected
- Returns 404 for missing sandbox, empty `DiagnosticsResponse()` for missing `validation.json` — both correct
- Reading only `validation.json` inside the sandbox dir — no file access beyond intended scope

---

### Frontend — `LogViewerDrawer.jsx`

**State reset** (lines 162–168): Correctly resets `diagnostics`, `backendDiagnostics`, `diagLoaded` when `sandboxId` changes — no stale state between drawer opens.

**Conditional fetch** (lines 170–181): Diagnostics fetched only when `isHealthcheckFailure === true` — no unnecessary API calls for other failure types. `.catch(() => setDiagLoaded(true))` prevents infinite "Loading…" spinner on API error.

**`BackendDiagnostics`** component (lines 23–91): Renders all five fields previously missing:
- `failure_type` with human-readable labels
- `backend_urls` key-value table
- `traefik_probe` with green/red reachability coloring
- `api_container` status/restarts/health
- `traefik_networks`

All sub-fields default safely (`= {}`, `= []`) if absent. `if (!bd) return null` guards the whole component.

**`HealthcheckDiagnostics`** (lines 94–151): Guards `!loaded` state, falls back to "No probe data captured" when probes array is empty, shows stderr in `<details>` toggle. Delegates to `BackendDiagnostics` for infrastructure data.

**One minor observation**: When `loaded` is false and diagnostics haven't arrived yet, the loading indicator shows even if `diagnostics` and `backendDiagnostics` end up both null (API returned empty). The drawer will flicker briefly to "No probe data captured" — acceptable UX for this ticket's scope, not a correctness issue.

---

### Tests

**`test_parse_healthcheck_output.py`**: 8 tests covering PASS/FAIL parsing, summary line extraction, multi-probe, empty stdout, unknown line ignoring, stderr capture, and missing HTTP code. Good coverage of the regex logic.

**`test_sandbox_runtime_deploy.py`**: 8 mocks updated from 3-tuple to 4-tuple `_run_scripts` return — mechanically correct, no functional regression.

---

### Scope Compliance

Changes are correctly bounded:
- `run_sandbox.py`: parsing + diagnostics collection + 4-tuple return
- `sandbox_runtime_deploy.py`: call site updates only
- `runtime_dashboard.py`: one new endpoint
- Frontend: new components + one API function
- Tests: new test file + mock updates

No unrelated modifications, no feature creep, no silent behavior changes.

---

### Summary

Both blocking issues from the previous review are resolved. All six acceptance criteria are satisfied. No new blocking issues. The two minor observations (backend_diagnostics written on success path; brief loading flicker) are cosmetic and outside the ticket scope.

IMPLEMENTATION_APPROVED
