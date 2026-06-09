## Objective

Extend AI Dev Factory from a single-project tool into a multi-project workspace by adding a persistent workspace registry, an existing-project bootstrap flow, per-project isolated runtime directory trees, per-project daemon management in the supervisor, strict `project_id` validation, and a project-centric frontend with an import wizard.

## Included

### Backend — project ID validation helper
- `services/control_api/services/project_id.py` (new): `normalize_project_id(raw: str) -> str` (lowercase, `[a-z0-9_-]`, max 64 chars, collapse unsupported chars to `-`); `validate_project_id(raw: str) -> str` (reject invalid chars, `/`, `\\`, `.`, `..`, empty, whitespace-only — raise `ValueError`, do not rewrite); `assert_contained(runtime_root: Path, project_id: str) -> Path` (resolves `runtime_root/projects/{project_id}`, asserts no symlink escape and no path traversal outside `runtime_root/projects/`).

### Backend — workspace registry persistence
- `services/control_api/services/project_registry.py`: add `register(project_id: str, root: Path) -> None` writing to `{RUNTIME_ROOT}/workspace.json`; add `unregister(project_id: str) -> None`; add `load_from_workspace_file(runtime_root: Path) -> ProjectRegistry` classmethod (loads `workspace.json`, falls back to `_scan()` if absent); reject duplicate `project_id` in `register()` with `ValueError`.

### Backend — stack detector
- `services/control_api/services/stack_detector.py` (new): `detect_stack(project_root: Path) -> str` returning `"python" | "node" | "go" | "rust" | "unknown"` via file presence heuristics (`pyproject.toml/requirements.txt`, `package.json`, `go.mod`, `Cargo.toml`).

### Backend — project bootstrap service
- `services/control_api/services/project_bootstrap.py` (new): `bootstrap(project_root: Path, project_id: str, runtime_root: Path) -> BootstrapResult` that (1) calls `validate_project_id(project_id)` and `assert_contained(runtime_root, project_id)`, (2) verifies `project_root` is a git repo (`project_root/.git` exists), (3) creates `{runtime_root}/projects/{project_id}/{runs,logs,state,worktrees}/`, (4) writes `{project_root}/.ai-dev-factory/project.yml` (name, stack, bootstrapped_at) if absent, (5) calls `registry.register(project_id, project_root)`, (6) returns `BootstrapResult`.

### Backend — runtime resolver
- `services/control_api/services/runtime_resolver.py`: add `resolve_project_runtime_root(project_id: str, runtime_root: Path) -> Path` (delegates containment check to `assert_contained`); add optional `project_id` parameter to `resolve_runs_dir`, `resolve_logs_dir`, `resolve_state_dir`, `resolve_worktrees_dir` — when `project_id` is provided, return the nested project-specific path instead of the global path.

### Backend — API routes
- `services/control_api/routes/projects.py`: add `GET /projects` (returns all registered projects); `POST /projects/import` (validates request via `validate_project_id`, calls `bootstrap()`, returns `BootstrapResult`); `DELETE /projects/{project_id}` (calls `unregister()`). Keep the existing `GET /{project_id}/branches`.

### Backend — schemas
- `services/control_api/models/schemas.py`: add `ProjectImportRequest(project_root: str, project_id: str)`; add `BootstrapResult(project_id, project_root, runtime_root, stack, runs_dir, logs_dir, state_dir, worktrees_dir)`; extend `ProjectInfo` with `runtime_root: str | None` and `stack: str | None`.

### Backend — control_api startup
- `services/control_api/main.py`: replace the existing `ProjectRegistry` construction with `ProjectRegistry.load_from_workspace_file(runtime_root)` when `runtime_root` is resolvable; fall back to the existing scan-based construction otherwise. Expose `runtime_root` on `app.state` so routes can pass it to bootstrap.

### Supervisor — per-project daemon management
- `services/supervisor/main.py`: add `_project_daemon_states: dict[str, DaemonState]` and `_project_daemon_procs: dict[str, subprocess.Popen]`; add helpers `_project_runs_dir(project_id, project_runtime_root)`, `_project_logs_dir(project_id, project_runtime_root)`, `_project_pid_path(project_id, project_runtime_root)`; add `POST /projects/{project_id}/daemon/start` (validates project exists via control_api registry lookup before spawning, logs all resolved paths: `project_id`, `project_root`, `project_runtime_root`, `runs_dir`, `logs_dir`, `state_dir`, `worktrees_dir`, `daemon_pid_path`); add `GET /projects/{project_id}/daemon/status`; add `POST /projects/{project_id}/daemon/stop`; include per-project daemon PIDs in the monitor loop without touching global daemon state.

### Frontend
- `apps/dashboard/src/pages/ProjectsPage.jsx` (new): lists all projects from `GET /projects`; shows "Import project" button; navigates to `/import-project`.
- `apps/dashboard/src/pages/ImportProjectPage.jsx` (new): two-field form (local path, project ID with auto-normalize preview); calls `importProject()`; shows success with link to the project dashboard or error with the 4xx message.
- `apps/dashboard/src/api/projects.js`: add `listProjects()`, `importProject(project_root, project_id)`, `deleteProject(project_id)` alongside the existing branch-listing calls.
- `apps/dashboard/src/App.jsx`: add `/projects` route (ProjectsPage) and `/import-project` route (ImportProjectPage); add "Projects" nav link.

### Documentation — follow-up tracking
- `runs/T181/fixes/context-20260609T135439Z.md` (already present): confirm it notes ticket/worktree collision prevention across projects as a known out-of-scope limitation requiring a follow-up ticket.

## Excluded

- Traefik, deploy environments, healthcheck pipelines.
- URL-scheme refactor to `/projects/:id/*` nested routing — context/query-param routing is sufficient for the MVP.
- Per-project daemon auto-start on bootstrap — daemon start remains explicit.
- SQLite/database schema partitioning per project.
- Worktree collision prevention for duplicate ticket IDs across projects (follow-up ticket required).
- "Create new project" beyond a placeholder button.
- Migration of the existing single-project runtime layout.
- Production runtime deployment or sandbox orchestration.

## Acceptance criteria

- `GET /projects` returns all registered projects including `runtime_root` and `stack` fields.
- `POST /projects/import` with a valid git repo creates `{runtime_root}/projects/{project_id}/{runs,logs,state,worktrees}/`, writes `.ai-dev-factory/project.yml`, persists to `workspace.json`, and returns `200 BootstrapResult` with all resolved paths.
- `POST /projects/import` with a non-git path returns `4xx`.
- `POST /projects/import` with a `project_id` containing `/`, `\\`, `..`, whitespace, or other invalid chars returns `4xx`.
- `POST /projects/import` with a duplicate `project_id` returns `4xx`.
- `GET /projects` includes the newly imported project after a successful import.
- The bootstrap service cannot produce a `project_runtime_root` outside `{runtime_root}/projects/` (containment assertion verified in unit test).
- `POST /projects/{id}/daemon/start` on the supervisor spawns a daemon with `cwd` set to the project root; the PID file lands at `{runtime_root}/projects/{id}/runs/daemon.pid`.
- Supervisor daemon start logs all runtime paths (`project_id`, `project_root`, `project_runtime_root`, `runs_dir`, `logs_dir`, `state_dir`, `worktrees_dir`, `daemon_pid_path`).
- `POST /projects/{id}/daemon/start` on the supervisor returns `4xx` if the project is not registered in the workspace registry.
- Two projects can have simultaneous active daemons without PID file collision.
- Global daemon state and PID file are untouched by per-project daemon operations.
- `ProjectsPage` renders with the project list and an "Import project" button.
- `ImportProjectPage` completes a bootstrap and the project appears in the list on success; displays the 4xx error message on failure.
- Existing tests pass without modification.
