Implementation complete. Here's a summary:

## Changes made

**Backend — `services/control_api/`**

- **`main.py`** — Added `import traceback` + `from fastapi.responses import JSONResponse`, and a global `@app.exception_handler(Exception)` that logs the traceback and returns `{"detail": "<message>"}` with HTTP 500. Prevents opaque empty 500s.

- **`routes/daemon.py`** — `project_daemon_board` now injects `request: Request` and uses `getattr(request.app.state, "worktrees_dir", None) or resolve_worktrees_dir(project_root)` — consistent with the legacy handler and avoids a redundant resolution call.

- **`routes/project_map.py`** — `project_refresh_project_map` now injects `request: Request` and uses the same `app.state.worktrees_dir` pattern for the background task.

**Frontend — `apps/dashboard/src/`**

- **`pages/IssueMapperActivityPage.jsx`** — Component now accepts `{ projectId }` prop and passes it to `mapApi.getProjectMapActivity(projectId)`, with `projectId` in the `useCallback` dependency array. Calls now go to `/projects/{id}/project-map/activity` when a project is active.

- **`App.jsx`** — Route updated to `<IssueMapperActivityPage projectId={activeProject} />`, matching the pattern of every other page.

**Tests — `tests/test_dashboard_500_regression.py`** (new, 9 tests)

- Board, project-map, activity, and refresh return 200 for a valid project.
- Unknown project ID returns 404 on all four endpoints.
- Injected `RuntimeError` in a service returns `{"detail": "..."}` with HTTP 500 via the global handler.
