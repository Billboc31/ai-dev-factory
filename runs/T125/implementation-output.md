All tasks complete. Here is a summary of all changes made.

---

## Summary

### Files created
- **`services/control_api/dependencies.py`** — FastAPI `Depends` function `resolve_project(project_id, request) → Path`. Raises HTTP 404 for unknown project IDs by querying `app.state.project_registry`.

- **`tests/test_project_scoped_routes.py`** — 9 integration tests: unknown project → 404, daemon status isolated per project, tickets isolated per project, ticket not visible in wrong project, runtime-status isolated, legacy routes still work.

- **`tests/test_project_isolation.py`** — 8 unit tests: `resolve_runs/logs/worktrees_dir` returns separate paths per root, `daemon_manager.get_status/activity/runtime_status` reads only from the given project root, `artifact_reader.list_tickets/get_ticket/logs` reads only from the given project root.

### Backend files modified
- **`routes/daemon.py`** — Added `project_router = APIRouter(prefix="/projects")` with all 8 daemon endpoints under `/{project_id}/daemon/*`, using `Depends(resolve_project)`.
- **`routes/tickets.py`** — Added `project_router` with all 17 ticket endpoints (read + workflow actions) under `/{project_id}/tickets/*`.
- **`routes/project_map.py`** — Added `project_router` with 3 project-map endpoints under `/{project_id}/project-map/*`.
- **`main.py`** — Registered `daemon.project_router`, `tickets.project_router`, `project_map.project_router`.

### Frontend files modified
- **`api/daemon.js`**, **`api/tickets.js`**, **`api/projectMap.js`** — All functions accept optional `projectId`; prefix URL with `/projects/{projectId}` when provided, otherwise fall back to legacy routes.
- **`App.jsx`** — Passes `projectId={activeProject}` to `TicketsPage`, `DaemonPage`, `BoardPage`, `ProjectMapPage`.
- **`TicketsPage.jsx`**, **`DaemonPage.jsx`**, **`BoardPage.jsx`**, **`ProjectMapPage.jsx`** — Accept `{ projectId }` prop, pass it to API calls, use `projectId` as `key` in `usePolling` to trigger re-fetch on project switch.
- **`RuntimeStatusPanel.jsx`**, **`DaemonActivityFeed.jsx`** — Accept `{ projectId }` prop, use `useCallback` with `projectId` in deps, pass `projectId` as polling key.
