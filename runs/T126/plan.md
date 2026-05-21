I have enough information to write the implementation plan. Here is the plan based on thorough code analysis:

---

## Objective

Fix HTTP 500 errors on the dashboard that were introduced by the project-scoped routing added in T125, by hardening route handlers against unhandled service exceptions, aligning the frontend API calls with the current project context, and adding regression tests for the affected endpoints.

## Included

### Backend — `services/control_api/`

**`main.py`**
- Add a global exception handler (`@app.exception_handler(Exception)`) that catches any unhandled exception, logs the traceback, and returns a structured JSON 500 response with an informative `detail` field — prevents FastAPI returning an opaque 500 with no body.

**`routes/daemon.py`**
- Fix `project_daemon_board`: inject `request: Request` alongside the `resolve_project` dependency, and pass `worktrees_dir = getattr(request.app.state, "worktrees_dir", None) or resolve_worktrees_dir(project_root)` — matches the pattern used in the legacy `daemon_board` handler.

**`routes/project_map.py`**
- Fix `project_refresh_project_map`: inject `request: Request` and pass `worktrees_dir = getattr(request.app.state, "worktrees_dir", None) or resolve_worktrees_dir(project_root)` — aligns with the legacy `refresh_project_map` handler.

**`services/project_map_service.py`** (read first to audit)
- Verify that `get_project_map` and `get_project_map_activity` are resilient to missing or malformed files (i.e., they do not raise unexpected exceptions when the project map files don't exist yet). Add defensive try-except where missing.

### Frontend — `apps/dashboard/src/`

**`pages/IssueMapperActivityPage.jsx`**
- Accept and use a `projectId` prop (consistent with every other page).
- Change the call from `mapApi.getProjectMapActivity()` to `mapApi.getProjectMapActivity(projectId)` so it goes through the project-scoped prefix when a project is active.

**`App.jsx`**
- Pass `projectId={activeProject}` to `<IssueMapperActivityPage />` in the route definition, matching the pattern used for `DaemonPage`, `BoardPage`, and `ProjectMapPage`.

### Tests — `tests/`

Add `test_dashboard_500_regression.py` covering:
- `GET /projects/{id}/daemon/board` returns 200 for a known project (with an empty `runs/` dir).
- `GET /projects/{id}/project-map` returns 200 for a known project (no map file present yet).
- `GET /projects/{id}/project-map/activity` returns 200 for a known project (no activity file present yet).
- `POST /projects/{id}/project-map/refresh` returns 200 (background task enqueued).
- An unhandled exception in a service function is caught and returns 500 with a non-empty `detail` field (verifies the global handler works).

## Excluded

- New multi-project features.
- Redesign of the project selector or sidebar.
- Issues intake endpoint project-scoping (not called by the affected pages).
- Deployer implementation.
- Ticket mapper redesign.
- Any migration or change to the `ProjectRegistry` resolution logic.

## Acceptance criteria

- `GET /projects/{id}/daemon/board`, `GET /projects/{id}/project-map`, `GET /projects/{id}/project-map/activity`, and `POST /projects/{id}/project-map/refresh` all return 2xx for a valid registered project; none return 500.
- `GET /projects/no-such-id/...` for the above endpoints returns 404, not 500 (already true for other routes; must also hold for board and project-map refresh).
- An unhandled internal exception returns a structured JSON 500 `{ "detail": "..." }` body rather than an empty response.
- `IssueMapperActivityPage` calls `/projects/{id}/project-map/activity` when a project is active, and `/project-map/activity` when none is selected — confirmed by inspecting the network tab or test assertions.
- All new and existing tests in `tests/` pass (`pytest tests/`).
- The dashboard navigates through Tickets, Daemon, Board, Project Map, and Mapper Activity pages for the default project without any HTTP 500 in the browser console.
