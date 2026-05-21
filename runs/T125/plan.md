Now I have enough context to produce the plan.

## Objective

Extend the T124 multi-project `ProjectRegistry` so every runtime API route is scoped to a specific project, and update the React dashboard to pass the active project to all API calls and refresh runtime state on project switch.

## Included

**Backend — shared project-resolution dependency**
- `services/control_api/dependencies.py` (new): FastAPI `Depends` function `resolve_project(project_id: str, registry: ProjectRegistry) → Path`. Raises HTTP 404 if `project_id` is unknown. Injected via `request.app.state.project_registry`.

**Backend — project-scoped route prefixes**
- `routes/daemon.py`: duplicate existing routes under `/projects/{project_id}/daemon/*`, replacing `app.state.project_root` with the resolved path from the dependency. Keep the old `/daemon/*` routes pointing at the default project for backward compatibility (single-root mode).
- `routes/tickets.py`: same pattern — add `/projects/{project_id}/tickets/*` routes.
- `routes/project_map.py`: add `/projects/{project_id}/project-map/*` route.
- `main.py`: register the new routers with the `/projects/{project_id}` prefix.

**Backend — daemon isolation per project**
- `services/daemon_manager.py`: verify all path helpers (`resolve_runs_dir`, `resolve_logs_dir`, `resolve_state_dir`) are called with the per-project root — no global state leaks. Confirm PID file, log file, and `workers.json` paths are computed from the passed `project_root`, not from a module-level variable.
- `services/artifact_reader.py`: same audit — all artifact lookups must use the received `project_root`.

**Frontend — project-aware API clients**
- `apps/dashboard/src/api/daemon.js`: accept optional `projectId` parameter; prefix URL with `/projects/{projectId}` when provided.
- `apps/dashboard/src/api/tickets.js`: same.
- `apps/dashboard/src/api/projectMap.js`: same.

**Frontend — active project propagation**
- `apps/dashboard/src/App.jsx`: pass `activeProject.id` down to page components that consume runtime data (daemon panel, board, ticket list, project map).
- Relevant page components (e.g. `DaemonPanel`, `BoardView`, `TicketList`, `RuntimeStatus`): accept `projectId` prop and forward it to API calls.
- On project switch (`activeProject` change), trigger a data refresh for all runtime hooks (invalidate cache / re-fetch).

**Tests**
- `tests/test_project_scoped_routes.py` (new): integration tests that spin up two fake project roots, call `/projects/{id}/daemon/status` for each, and assert responses are independent.
- `tests/test_project_isolation.py` (new): unit tests verifying `daemon_manager`, `artifact_reader`, and `runtime_resolver` functions never read from a project root other than the one passed in, using two separate temp dirs.
- Extend `tests/test_project_registry.py`: cover `resolve()` returning `None` for unknown IDs (maps to HTTP 404).

## Excluded

- Multi-user authentication or per-user project access control.
- Cross-project orchestration or ticket dependencies across projects.
- Distributed or remote daemon execution.
- Kubernetes / container orchestration.
- Migrating existing single-root deployments — the old `/daemon/*` routes stay intact.
- Changing the daemon process model (one daemon per project is out of scope; this ticket scopes the API, not daemon spawning).
- Any new frontend pages or layout changes beyond wiring `projectId` through existing components.

## Acceptance criteria

- `GET /projects/{project_id}/daemon/status` returns HTTP 404 for an unknown `project_id`.
- `GET /projects/A/daemon/status` and `GET /projects/B/daemon/status` return independent data when projects A and B have separate `project_root` directories.
- `GET /projects/{project_id}/tickets` returns only tickets whose `runs/` directory lives under that project's root.
- `GET /projects/{project_id}/project-map` returns only the map artifact for that project.
- Switching the active project in the dashboard sidebar triggers a re-fetch of daemon status, board, and ticket list without a full page reload.
- The legacy `/daemon/*`, `/tickets/*`, and `/project-map/*` routes still respond correctly for the default single-root configuration.
- `tests/test_project_scoped_routes.py` passes with two isolated project roots.
- `tests/test_project_isolation.py` passes, confirming no cross-project state access in service functions.
- No existing test suite (`pytest tests/`) regressions.
