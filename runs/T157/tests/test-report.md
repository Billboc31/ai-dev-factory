---

## Test Report — T157

**Verdict: CONDITIONAL PASS**

### Acceptance criteria results

| # | Criterion | Status |
|---|---|---|
| AC1 | Ticket branch deploy fetches latest remote commit before sandbox creation | **PASS** |
| AC2 | Sandbox worktree HEAD equals fetched remote branch HEAD | **PASS** |
| AC3 | Subsequent deploy after new push uses the new commit | **PASS** |
| AC4 | Non-existent branch fails loudly, no silent fallback to `main` | **PASS** |
| AC5 | Sandbox state exposes `requested_ref`, `resolved_ref`, `commit_sha` | **PASS** |
| AC6 | Runtime UI can display the deployed commit/ref | **PARTIAL FAIL** |
| AC7 | Existing deploys from `main` still work | **PASS** |
| AC8 | Existing sandbox isolation guarantees remain intact | **PASS** |

### Issue found — non-blocking

**`runtime_dashboard.py:203`** — the dashboard parses `ref` from `raw.get("ref") or raw.get("branch") or raw.get("commit")`, but T157's state stores `requested_ref`, `resolved_ref`, `commit_sha`. The dashboard overview will show `ref: null` for all T157-deployed sandboxes.

One-line fix: add `or raw.get("requested_ref")` to the fallback chain. The full state is accessible via `GET /sandboxes/{id}` so the data exists — it just isn't surfaced by the overview endpoint.

### Test suite

All 16 sandbox worktree tests pass (including 5 new tests added for T157). The 52 failures in the full suite are all pre-existing on `main` (unregistered routes from T151/T156, and test isolation issues) — none overlap with T157's changed files.
