Here is the implementation plan:

---

## Objective

Transform AI Dev Factory into a multi-project workspace by adding a persistent workspace registry, an existing-project bootstrap flow, per-project isolated runtime directory trees, per-project daemon management in the supervisor, and a project-centric frontend with an import wizard.

## Included

### Backend — workspace registry persistence
- `services/control_api/services/project_registry.py`: add `register(project_id, root)` and `unregister(project_id)` methods that persist to `{RUNTIME_ROOT}/workspace.json`; add `load_from_workspace_file(runtime_root)` classmethod to rehydrate from disk on API startup; keep the existing scan-based `_scan()` fallback when no workspace file exists.

### Backend — project bootstrap service
- `services/control_api/services/project_bootstrap.py` (new): `bootstrap(project_root, project_id, runtime_root) -> BootstrapResult` that (1) validates the path is a git repo, (2) creates `{runtime_root}/projects/{project_id}/{runs,logs,state,worktrees}/`, (3) writes `.ai-dev-factory/project.yml` into the target repo (name, stack, bootstrapped_at) if absent, (4) registers the project, (5) returns `BootstrapResult`.

### Backend — stack detector
- `services/control_api/services/stack_detector.py` (new): `detect_stack(project_root) -> str` returning `python | node | go | rust | unknown` from file presence heuristics.

### Backend — per-project runtime resolver
- `services/control_api/services/runtime_resolver.py`: add `resolve_project_runtime_root(project_id)` → `{RUNTIME_ROOT}/projects/{project_id}`; add optional `project_id` to `resolve_runs_dir / resolve_logs_dir / resolve_state_dir / resolve_worktrees_dir` so they return project-nested paths when both args are provided.

### Backend — API routes
- `services/control_api/routes/projects.py`: add `GET /projects`, `POST /projects/import`, `DELETE /projects/{project_id}`.

### Backend — schemas
- `services/control_api/models/schemas.py`: add `ProjectImportRequest`, `BootstrapResult`; extend `ProjectInfo` with `runtime_root` and `stack`.

### Backend — control_api startup
- `services/control_api/main.py`: prefer `load_from_workspace_file()` on startup; fall back to directory scan.

### Supervisor — per-project daemon management
- `services/supervisor/main.py`: add `_per_project_daemon_states` and `_per_project_daemon_procs` dicts; add per-project PID/log path helpers; add `_spawn_project_daemon(project_id, project_root, exec_cmd)`; add `POST /projects/{id}/daemon/start`, `GET /projects/{id}/daemon/status`, `POST /projects/{id}/daemon/stop` following the existing analysis/scripts endpoint pattern; include per-project PIDs in the monitor loop.

### Frontend
- `apps/dashboard/src/pages/ProjectsPage.jsx` (new): projects home with import button.
- `apps/dashboard/src/pages/ImportProjectPage.jsx` (new): import wizard (path → validate → bootstrap → navigate).
- `apps/dashboard/src/api/projects.js` (new): `listProjects()`, `importProject()`, `deleteProject()`.
- `apps/dashboard/src/App.jsx`: add `/projects` and `/import-project` routes; add "Projects" nav link.

## Excluded

- Traefik, deploy environments, healthcheck pipelines.
- URL-scheme refactor to `/projects/:id/*` — context/query-param routing is sufficient for the MVP.
- Per-project daemon auto-start on bootstrap — start remains explicit.
- SQLite schema partitioning.
- Worktree collision prevention for duplicate ticket IDs across projects.
- "Create new project" beyond a placeholder button.
- Migration of the existing single-project runtime layout.

## Acceptance criteria

- `GET /projects` returns all registered projects.
- `POST /projects/import` with a valid git repo creates the full runtime directory tree, writes `.ai-dev-factory/project.yml`, persists to `workspace.json`, returns `200 BootstrapResult`.
- `POST /projects/import` with a non-git path or duplicate `project_id` returns `4xx`.
- `GET /projects` includes the newly imported project after a successful import.
- `POST /projects/{id}/daemon/start` on the supervisor spawns a daemon with `cwd` set to the project root; the PID file lands at `{runtime_root}/projects/{id}/runs/daemon.pid`.
- Two projects can have simultaneous active daemons without PID file collision.
- `ProjectsPage` renders with the project list and an "Import project" button.
- `ImportProjectPage` completes a bootstrap and the project appears in the list on success.
- Existing tests pass without modification.
