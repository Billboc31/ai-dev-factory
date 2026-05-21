Now I have a complete picture of the codebase. Let me write the plan.

## Objective

Introduce project-scoped backend APIs and a project-aware dashboard so multiple independent `ai-dev-factory` projects can be orchestrated from a single control surface, with each project's runtime state, daemon, workers, tickets, and board fully isolated.

## Included

**Backend — project registry service**

- `services/control_api/services/project_registry.py` (new): discovers projects by scanning `AI_DEV_FACTORY_PROJECTS_ROOT` for subdirectories that are git repositories containing an `ai/` directory; maps `project_id` (dirname) → absolute `project_root`; exposes `list_projects()` and `resolve(project_id) → Path | None`.
- `services/control_api/main.py`: accept `--projects-root` CLI flag and `AI_DEV_FACTORY_PROJECTS_ROOT` env var; store `ProjectRegistry` instance in `app.state.registry`; fall back to existing single-project mode (`app.state.project_root`) when the env var is absent, preserving backward compatibility.

**Backend — project-scoped routing**

- `services/control_api/routes/projects.py` (new): `GET /projects` (list all discovered projects with `name`, `root`, `tickets_count`); all existing `daemon`, `tickets`, and `project_map` routers re-mounted under `/projects/{project_id}/` using a FastAPI `APIRouter` prefix.
- `services/control_api/routes/daemon.py`, `routes/tickets.py`, `routes/project_map.py`, `routes/issues.py`: replace the direct read of `request.app.state.project_root` with a shared FastAPI dependency `get_project_root(project_id: str, request: Request) → Path` that resolves via the registry; unknown `project_id` returns HTTP 404.
- `services/control_api/routes/providers.py`: update `GET /projects` to delegate to the registry instead of returning the hardcoded single-project list.
- `services/control_api/models/schemas.py`: extend `ProjectInfo` with `active_workers_count: int` field.

**Frontend — project selector**

- `apps/dashboard/src/hooks/useProjects.js` (new): fetches `/api/projects`, returns `{ projects, loading, error }` with simple refresh.
- `apps/dashboard/src/components/ProjectSidebar.jsx` (new): renders the project list from `useProjects`; highlights the currently active project; emits `onSelect(projectId)`.
- `apps/dashboard/src/App.jsx`: add `/:projectId` prefix to all existing routes (`/:projectId/board`, `/:projectId/tickets`, `/:projectId/tickets/:id`, `/:projectId/daemon`, `/:projectId/project-map`, `/:projectId/mapper-activity`); render `ProjectSidebar`; replace the hardcoded "ai-dev-factory" span in the header with the active project name from the URL param; add root `/` redirect to the first project returned by `GET /api/projects`.

**Frontend — API clients**

- `apps/dashboard/src/api/daemon.js`, `apps/dashboard/src/api/tickets.js`, `apps/dashboard/src/api/projectMap.js`: add a `projectId` parameter to every exported function; rewrite all URL strings from `/api/daemon/...` → `/api/projects/{projectId}/daemon/...` (and equivalently for tickets and project-map).

**Tests**

- `tests/test_project_registry.py` (new): unit tests for `project_registry.py` — discover valid projects, ignore non-git subdirectories, handle missing `projects_root`, handle empty directory, resolve known and unknown project_ids.
- `tests/test_project_scoped_routes.py` (new): integration tests using two temporary project roots with distinct `runs/` and `state.json` fixtures; assert `GET /projects/{project_id}/tickets` returns only that project's tickets; assert `GET /projects/{project_id}/daemon/board` returns only that project's board; assert project A data does not appear in project B responses.
- `apps/dashboard/tests/ProjectSidebar.test.jsx` (new): renders project list, highlights active project, fires `onSelect` on click.
- Update `apps/dashboard/tests/api.test.js` and existing page tests to use project-prefixed URLs.

## Excluded

- Multi-user authentication or per-user project access control.
- Cross-project orchestration (shared workers, cross-project dependencies).
- Distributed or remote runtimes (Kubernetes, remote SSH hosts).
- SaaS billing or account management.
- Plugin or extension architecture.
- Changes to the daemon CLI itself or its internal state machine — the daemon remains a per-project process invoked unchanged; only the API layer learns to dispatch to multiple daemons.
- Responsive/mobile layout changes beyond accommodating the sidebar in the existing layout.
- Migrating existing `runs/` state files when `AI_DEV_FACTORY_PROJECTS_ROOT` is newly configured.

## Acceptance criteria

- `GET /api/projects` returns a JSON list containing at least the `ai-dev-factory` project with correct `tickets_count`.
- `GET /api/projects/ai-dev-factory/daemon/status` returns the same data as the current `GET /api/daemon/status` for that project.
- `GET /api/projects/ai-dev-factory/daemon/board` returns only tickets under the `ai-dev-factory` `runs/` directory.
- With two projects A and B configured (separate `runs/` dirs, each with a distinct ticket), `GET /api/projects/A/tickets` returns A's ticket only, and `GET /api/projects/B/tickets` returns B's ticket only — no cross-contamination.
- `GET /api/projects/unknown-project` returns HTTP 404.
- Dashboard sidebar lists all discovered projects.
- Clicking a project in the sidebar navigates to `/:projectId/board` and all visible data refreshes to that project.
- Browser URL path reflects the selected project on every page (`/:projectId/board`, `/:projectId/tickets`, etc.).
- Navigating to `/` redirects to the first project's board.
- Header displays the current project name instead of the hardcoded string "ai-dev-factory".
- `pytest tests/test_project_registry.py tests/test_project_scoped_routes.py` passes with no failures.
- `npm test` in `apps/dashboard/` passes with no failures.
- All existing `pytest tests/` tests continue to pass (backward-compatibility mode, no `AI_DEV_FACTORY_PROJECTS_ROOT` set).
