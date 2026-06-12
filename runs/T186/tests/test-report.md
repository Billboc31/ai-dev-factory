Here is the test report summary:

---

## T186 Test Report

**Verdict: VALIDATION ACCEPTED with notes**

### Tests run

| Suite | Result |
|---|---|
| New T186 tests (`test_git_root.py`, `test_auto_bootstrap.py`) | **13/13 pass** |
| Existing project tests (bootstrap, registry, endpoints, scoped routes) | **39/39 pass** |
| Full suite vs main | **0 new failures** (71 pre-existing on both branches) |

### Acceptance criteria

| AC | Status |
|---|---|
| Auto-appears in `/projects` | PASS |
| No manual import required | PASS |
| Sidebar visibility | Cannot verify (no UI) |
| Ticket workflows (`GET /projects/ai-dev-factory/tickets`) | PASS |
| Daemon controls (`GET /projects/ai-dev-factory/daemon/status`) | PASS |
| Imported projects unaffected | PASS |
| No duplicate registration across restarts | PASS |

### Issues found

**ISSUE-1 (Medium, pre-existing):** `runtime_root` and `stack` are `null` in the `/projects` HTTP response. Root cause: `providers.py` has a competing `GET /projects` route registered at line 132 of `main.py`, before `projects.py` at line 149. FastAPI dispatches to the first match, so the enriched version in `projects.py` is never reached. This existed on `main` before T186 — the enrichment code was already dead. The underlying runtime directories are correctly created; only the HTTP response is incomplete. Project-scoped routes (`/projects/{id}/tickets`, daemon, etc.) all work correctly.

**ISSUE-2 (Low, edge case):** When `create_app` is called with an explicit worktree path, both the worktree name (`T186`) and `ai-dev-factory` appear in the registry. This does not occur in production (env-var-driven startup uses the workspace-file path, not `from_single_root`).

The core T186 logic — `auto_bootstrap`, `resolve_git_root`, idempotency — is correct and well-tested. ISSUE-1 should be tracked as a follow-up fix to the route registration order.
