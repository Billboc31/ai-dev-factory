# Test Report — T124

**Date**: 2026-05-21  
**Branch**: ticket/T124-t124-multi-project-runtime-boards-and-project-isol  
**Verdict**: PASS (V1 scope)

---

## Scope note

The plan review (PLAN_FIX_REQUIRED → re-plan) explicitly reduced T124 to a **V1 read-only** delivery:
project registry service, `GET /api/projects`, dashboard sidebar, active project name in header, and tests.
Project-scoped runtime operations (daemon, tickets, board, artifacts per project) were deferred to a follow-up ticket.
Criteria below are evaluated against both the ticket and the approved V1 plan.

---

## Acceptance criteria — ticket

| # | Criterion | Status | Notes |
|---|-----------|--------|-------|
| 1 | Dashboard can display multiple independent projects | **PASS** | `ProjectSidebar` renders one entry per project from `GET /api/projects`; `useProjects` polls every 10 s |
| 2 | Each project has isolated runtime state and worktrees | **DEFERRED** | Explicitly excluded from V1 by plan review; `ProjectRegistry.resolve()` is wired in for follow-up |
| 3 | Switching project updates the visible board/runtime context | **PARTIAL** | Header name updates on click ✓; board/tickets/daemon pages still call global endpoints (deferred) |
| 4 | Runtime actions only affect the selected project | **DEFERRED** | All runtime routes remain global per V1 scope |
| 5 | Existing `ai-dev-factory` workflows continue to function | **PASS** | `from_single_root` backward compat preserved; `/health`, `/daemon/status`, `/tickets`, `/project-map` unchanged |
| 6 | Project-scoped runtime APIs are covered by tests | **PARTIAL** | `GET /projects` covered by 19 tests (10 unit + 9 integration); project-scoped runtime APIs deferred |
| 7 | Runtime garbage files are not shared across project runtimes | **DEFERRED** | Not addressed in V1 scope per plan review |

---

## Acceptance criteria — plan (committed V1 scope)

| Criterion | Status |
|-----------|--------|
| `GET /api/projects` single-root returns `[{name, root, tickets_count}]` | PASS |
| `GET /api/projects` multi-root (2 git subdirs) returns both entries | PASS |
| Pre-existing routes (`/health`, `/daemon/status`, `/tickets`, etc.) unchanged | PASS |
| Dashboard sidebar renders one item per project | PASS |
| Active project name displayed in header (not hardcoded) | PASS |
| Clicking a sidebar entry updates the header name | PASS |
| `pytest tests/test_project_registry.py tests/test_projects_endpoint.py` | PASS — 19/19 |
| `pytest tests/` no regressions introduced | PASS — 0 new failures |

---

## Test execution

### New tests (19/19 pass)

```
tests/test_project_registry.py  ✓ 10/10
tests/test_projects_endpoint.py ✓  9/9
```

### Full suite

```
574 collected → 530 passed, 44 failed
```

All 44 failures are **pre-existing** (confirmed by running against the baseline branch state before T124 commits). None of the failing test files were modified by T124.

Pre-existing failing files:
- `test_control_api_artifacts.py` — 13 failures (test isolation issue: artifact_reader reads real repo `runs/`)
- `test_control_api_endpoints.py` — 8 failures (same isolation issue + shared daemon activity state)
- `test_control_api_subprocess.py` — 5 failures
- `test_daemon_checkpoint.py` — 4 failures
- `test_daemon_issue_polling.py` — 1 failure
- `test_run_daemon.py` — 2 failures
- `test_ticket_timeline.py` — 2 failures (+ intermittent)

No regressions introduced by T124.

---

## Regressions

None.

---

## Blocking issues

None.

---

## Observations (non-blocking)

1. **`eslint-disable` in `App.jsx:40`** — `activeProject` is absent from the `useEffect` dependency array; noted in implementation review as a code smell to fix in follow-up.
2. **Sidebar shows no loading/error state** — UX degrades silently if API is unavailable on startup; acceptable for V1.
3. **Registry scanned once at startup** — projects added at runtime require an API restart; documented behavior for V1.
4. **Pre-existing test isolation failures** — `test_control_api_artifacts.py` and `test_control_api_endpoints.py` read from the live repository `runs/` directory instead of `tmp_path`; worth fixing in a dedicated maintenance ticket.
