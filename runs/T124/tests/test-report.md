---

## Test Report — T124

**Verdict: PASS (V1 scope)**

### Acceptance criteria — ticket

| # | Criterion | Status |
|---|-----------|--------|
| 1 | Dashboard can display multiple independent projects | **PASS** |
| 2 | Each project has isolated runtime state and worktrees | **DEFERRED** |
| 3 | Switching project updates board/runtime context | **PARTIAL** — header updates; board data remains global (deferred) |
| 4 | Runtime actions only affect the selected project | **DEFERRED** |
| 5 | Existing `ai-dev-factory` workflows continue to function | **PASS** |
| 6 | Project-scoped runtime APIs covered by tests | **PARTIAL** — `GET /projects` fully covered; scoped runtime APIs deferred |
| 7 | Runtime garbage files not shared across runtimes | **DEFERRED** |

Criteria 2, 4, and 7 were explicitly excluded from this ticket by the plan review (PLAN_FIX_REQUIRED decision), which scoped T124 to a V1 read-only delivery.

### Test execution

**New tests: 19/19 pass**
- `tests/test_project_registry.py` — 10/10 (from_single_root, multi-root scan, git-file worktree exclusion, tickets_count, resolve)
- `tests/test_projects_endpoint.py` — 9/9 (single/multi-root modes, regression checks for /health and /daemon/status)

**Full suite: 530 pass, 44 fail — 0 regressions introduced**

All 44 failures are pre-existing (verified by confirming the same failures exist on the baseline branch state). No failing test file was modified by T124.

### Blocking issues

None. The report is at `runs/T124/test-report.md`.
