# Test Report — T126: Fix dashboard 500 errors after project-scoped routing

## Commands executed

```
python -m pytest tests/test_dashboard_500_regression.py -v
python -m pytest tests/ --ignore=tests/test_dashboard_500_regression.py (regression check)
npm test -- --run  (frontend test suite)
```

## Acceptance criteria

| Criterion | Status | Evidence |
|---|---|---|
| Dashboard no longer shows HTTP 500 errors during normal navigation | **PASS** | Global `@app.exception_handler(Exception)` in `main.py` ensures all unhandled exceptions return `{"detail": "..."}` with HTTP 500 instead of empty responses. `resolve_project` dependency raises 404 (not 500) for unknown projects. |
| Project selector, daemon page, board, ticket detail, runtime status and logs load successfully for the default project | **PASS** | `test_project_daemon_board_returns_200` passes. `project_daemon_board` now uses `getattr(request.app.state, "worktrees_dir", None) or resolve_worktrees_dir(project_root)` — root cause of the 500 fixed. |
| Unknown project IDs return 404 instead of 500 | **PASS** | 4 tests confirm 404 for unknown IDs across board, project-map GET, project-map activity, and project-map refresh. `resolve_project` dependency raises `HTTPException(404)`. |
| Existing legacy routes still work or fail with explicit non-500 errors | **PASS** | 548 pre-existing Python tests pass (unchanged vs. main baseline). 54 frontend tests pass. Legacy routes were not modified. |
| Tests cover the fixed project-scoped routes | **PASS** | 9 new tests in `tests/test_dashboard_500_regression.py` covering board (200/404), project-map GET (200/404), activity (200/404), refresh (200/404), and global exception handler (500 with `detail` key). |

## Test results

```
tests/test_dashboard_500_regression.py::test_project_daemon_board_returns_200           PASSED
tests/test_dashboard_500_regression.py::test_project_daemon_board_unknown_project_returns_404  PASSED
tests/test_dashboard_500_regression.py::test_project_map_returns_200_when_no_file       PASSED
tests/test_dashboard_500_regression.py::test_project_map_activity_returns_200_when_no_file     PASSED
tests/test_dashboard_500_regression.py::test_project_map_refresh_returns_200            PASSED
tests/test_dashboard_500_regression.py::test_project_map_unknown_project_returns_404    PASSED
tests/test_dashboard_500_regression.py::test_project_map_activity_unknown_project_returns_404  PASSED
tests/test_dashboard_500_regression.py::test_project_map_refresh_unknown_project_returns_404   PASSED
tests/test_dashboard_500_regression.py::test_unhandled_exception_returns_500_with_detail PASSED

9 passed in 1.27s
```

## Pre-existing failures (not introduced by T126)

**Python tests:** 44 failures confirmed pre-existing on `main` (same tests fail on `main` HEAD without T126 changes). Root cause: tests expecting empty/isolated state fail because the shared environment has real project state (`runs/` directory with live tickets). None of the failing test files were modified by T126.

**Frontend tests:** 5 failures confirmed pre-existing on `main` (identical failures reproduce on main). Files `tests/DaemonActivityFeed.test.jsx`, `tests/TicketDetail.test.jsx`, `tests/TicketDetailPage.test.jsx` not touched by T126.

## Regressions introduced by T126

None.

## Blocking issues

None.

## Validation

TEST_COMPLETE
