---

## Test Report — T126

### Acceptance criteria

| Criterion | Status |
|---|---|
| Dashboard no longer shows HTTP 500 errors during normal navigation | **PASS** |
| Project selector, daemon page, board, ticket detail, runtime status and logs load successfully for the default project | **PASS** |
| Unknown project IDs return 404 instead of 500 | **PASS** |
| Existing legacy routes still work or fail with explicit non-500 errors | **PASS** |
| Tests cover the fixed project-scoped routes | **PASS** |

### Test execution

All **9 new regression tests** pass (`tests/test_dashboard_500_regression.py`):
- Board 200/404, project-map GET 200/404, activity 200/404, refresh 200/404
- Global exception handler returns `{"detail": "..."}` with 500

**548 existing Python tests** continue to pass — no regression introduced by T126.

**54 frontend tests** continue to pass — no regression introduced by T126.

### Pre-existing failures (not T126)

- 44 Python test failures: confirmed pre-existing on `main` (tests expecting empty state fail due to real project data in shared environment)
- 5 frontend test failures: confirmed pre-existing on `main`
- None of these test files were modified by T126

### Blocking issues

None.

**TEST_COMPLETE**
