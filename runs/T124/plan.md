Now I have everything needed. Let me write the V1 plan.

---

## Objective

Introduce a read-only project registry service and expose it via the existing `GET /api/projects` endpoint, then wire a project selector sidebar into the dashboard so the active project name is visible in the UI — all without touching any existing daemon/tickets/actions routes.

## Included

**Backend — `services/control_api/services/project_registry.py` (new)**
- `ProjectRegistry` class: scans a `projects_root: Path` for subdirectories that are git repositories (contain a `.git` entry); maps each valid subdir to a `ProjectEntry(id=dirname, root=Path)`.
- `list_projects(artifact_reader) → list[ProjectInfo]`: returns one `ProjectInfo` per discovered project (calls `artifact_reader.list_tickets(root)` for `tickets_count`).
- `resolve(project_id: str) → Path | None`: returns the root for a known project or `None`.
- Static constructor `from_single_root(root: Path)` for backward-compatible single-project mode.

**Backend — `services/control_api/main.py`**
- Read `AI_DEV_FACTORY_PROJECTS_ROOT` env var in `create_app()`.
- When set: instantiate `ProjectRegistry(projects_root=Path(env_var))`; attach to `app.state.project_registry`.
- When absent: fall back to `ProjectRegistry.from_single_root(project_root)`.
- Add `--projects-root` CLI argument mirroring the env var.

**Backend — `services/control_api/routes/providers.py`**
- Replace the body of `list_projects()`: read `request.app.state.project_registry`; delegate to `registry.list_projects(artifact_reader)`.
- No signature change; existing response model `list[ProjectInfo]` is preserved.

**Frontend — `apps/dashboard/src/hooks/useProjects.js` (new)**
- Fetches `/api/projects`; returns `{ projects, loading, error }`.
- Polls on a 10-second interval via the existing `usePolling` hook pattern.

**Frontend — `apps/dashboard/src/components/ProjectSidebar.jsx` (new)**
- Renders the project list from `useProjects`; highlights the entry whose `name` matches the `activeProject` prop; calls `onSelect(project.name)` on click.
- Minimal styling consistent with the existing Tailwind dark-theme nav.

**Frontend — `apps/dashboard/src/App.jsx`**
- Add `useState` for `activeProject`; initialize to the first project returned by `/api/projects` (or `"ai-dev-factory"` until the fetch resolves).
- Render `<ProjectSidebar>` as a left-column aside next to `<main>`.
- Replace the hardcoded `<span>ai-dev-factory</span>` in `Nav` with the `activeProject` value passed as a prop.
- No route path changes; all existing `<Route>` paths are unchanged.

**Tests**
- `tests/test_project_registry.py` (new): unit tests using `tmp_path` fixtures —
  - `from_single_root` returns one project with correct `id` and `root`.
  - `projects_root` with two valid git subdirs (each with a `.git` dir) returns both.
  - Non-git subdirectories are ignored.
  - Empty `projects_root` returns an empty list.
  - `resolve(known_id)` returns the correct path; `resolve(unknown_id)` returns `None`.
- `tests/test_projects_endpoint.py` (new): integration tests using `TestClient(create_app(...))` —
  - Single-root mode (no `AI_DEV_FACTORY_PROJECTS_ROOT`): `GET /projects` returns a list of length 1 with `name == project_root.name`.
  - Multi-root mode: two temporary git roots → `GET /projects` returns both; each has the correct `tickets_count`.
  - Existing endpoints (`GET /health`, `GET /daemon/status`) still respond 200 in both modes.

## Excluded

- Remounting any existing router (`/daemon`, `/tickets`, `/issues`, `/project-map`) under a `/projects/{project_id}/` prefix.
- Rewriting any frontend API client (`daemon.js`, `tickets.js`, `projectMap.js`) to include a `projectId` parameter.
- Making any runtime action (daemon start/stop, ticket intake, board queries) project-scoped.
- Runtime state migration when `AI_DEV_FACTORY_PROJECTS_ROOT` is newly configured.
- Multi-daemon orchestration or per-project daemon lifecycle management.
- Changes to `ProjectInfo` schema fields beyond what already exists (`name`, `root`, `tickets_count`).
- Responsive/mobile layout work.

## Acceptance criteria

- `GET /api/projects` returns a JSON array containing at least `{"name": "ai-dev-factory", "root": "...", "tickets_count": <n>}` when no `AI_DEV_FACTORY_PROJECTS_ROOT` is set.
- With `AI_DEV_FACTORY_PROJECTS_ROOT` pointing at a directory containing two valid git subdirs, `GET /api/projects` returns two entries, one per subdir.
- `GET /api/daemon/status`, `GET /api/tickets`, and all other pre-existing routes return the same responses as before this change (no regression).
- Dashboard sidebar renders a list item for each project returned by `GET /api/projects`.
- The active project's name is displayed in the header instead of the hardcoded string `"ai-dev-factory"`.
- Clicking a project entry in the sidebar updates the displayed project name in the header.
- `pytest tests/test_project_registry.py tests/test_projects_endpoint.py` passes with no failures.
- `pytest tests/` passes with no failures (full backward-compatibility regression check).
