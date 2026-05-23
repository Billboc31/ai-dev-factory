Now I have enough context to write the plan.

## Objective

Move sandbox environments to a configurable root outside the main runtime hierarchy (e.g., `~/sandboxes/{project-name}/{sandbox-id}/`) and make the sandbox layout project-agnostic, so multiple projects can own concurrent, fully isolated sandbox environments. The dashboard must expose the sandbox root and full project topology.

## Included

### Configuration (`deploy/.env.example`)
- Add `SANDBOX_ROOT` variable (e.g., `~/sandboxes`) — the new top-level sandbox root, independent of `AI_DEV_FACTORY_RUNTIME_ROOT`.
- Add `PROJECT_NAME` variable — the generic project identifier used as the per-project subdirectory inside `SANDBOX_ROOT`. Default: basename of `AI_DEV_FACTORY_PROJECT_ROOT`.

### Path resolution (`services/control_api/services/runtime_resolver.py`)
- Add `get_sandbox_root() → Path`: resolves `SANDBOX_ROOT` env var, expands `~`, falls back to `~/sandboxes`.
- Add `get_project_name() → str`: resolves `PROJECT_NAME` env var, falls back to `Path(AI_DEV_FACTORY_PROJECT_ROOT).name`.
- Add `get_project_sandbox_dir() → Path`: returns `get_sandbox_root() / get_project_name()`.

### Sandbox manager (`services/control_api/services/sandbox_manager.py`)
- Change `sandboxes_dir` to use `get_project_sandbox_dir()` instead of `{RUNTIME_ROOT}/sandboxes`.
- Keep per-sandbox internal layout unchanged (`state.json`, `.env`, `deploy.env`, `run.log`, `worktree/`, `runtime/`).
- Update `destroy()` to remove the full `{sandbox_dir}` tree (verify no partial cleanup leaves orphan directories).
- Port registry (`port-registry.json`) moves to `get_project_sandbox_dir()`.

### Agent runner (`tools/agent_runner/run_sandbox.py`)
- Propagate `SANDBOX_ROOT` and `PROJECT_NAME` into `deploy.env` written for each sandbox so sandbox-local scripts can locate their own root.
- Remove any remaining hardcoded `ai-dev-factory` path fragments in env construction.

### Dashboard backend (`services/control_api/routes/runtime_dashboard.py`)
- Add or extend an existing endpoint (e.g., `GET /runtime-dashboard/overview`) to return:
  - `sandbox_root`: absolute path to `get_sandbox_root()`
  - `project_name`: value of `get_project_name()`
  - `project_sandbox_dir`: absolute path to `get_project_sandbox_dir()`
  - list of active sandboxes with their IDs and status (already available via sandbox manager)

### Dashboard frontend (`apps/dashboard/src/`)
- Update `runtimeDashboard.js` to consume the new `sandbox_root`, `project_name`, and `project_sandbox_dir` fields.
- Display sandbox root path and project-level topology (project name → list of sandboxes) in the relevant dashboard component.

### Docker / compose (`docker-compose.yml`, `deploy/.env.example`)
- If `SANDBOX_ROOT` is outside the existing volume mounts, add a bind-mount for `${SANDBOX_ROOT}` so container-side code can read/write sandbox state. Update path-mapper env vars accordingly (`CONTAINER_SANDBOX_ROOT`, `HOST_SANDBOX_ROOT`).

### Path mapper (`services/supervisor/path_mapper.py`)
- Handle `CONTAINER_SANDBOX_ROOT` / `HOST_SANDBOX_ROOT` alongside the existing `CONTAINER_RUNTIME_ROOT` / `HOST_RUNTIME_ROOT` mappings.

## Excluded

- Cloud orchestration, Kubernetes, or production deployment changes.
- Migrating existing live sandbox state from the old location (out of scope; users recreate sandboxes).
- Changes to supervisor/daemon internal logic beyond path resolution.
- Automatic AI self-healing or any autonomous loop features.
- Changes to ticket workflow, planner, or any non-sandbox runtime subsystem.
- Multi-machine or remote sandbox support.

## Acceptance criteria

- A new `SANDBOX_ROOT` env var controls the top-level sandbox root; sandboxes are created at `{SANDBOX_ROOT}/{PROJECT_NAME}/{sandbox_id}/` — no longer under `{AI_DEV_FACTORY_RUNTIME_ROOT}/sandboxes/`.
- `PROJECT_NAME` defaults to the basename of `AI_DEV_FACTORY_PROJECT_ROOT`; it can be overridden without code changes.
- Two projects with different `PROJECT_NAME` values can have sandboxes under the same `SANDBOX_ROOT` without conflicts (separate subdirectories, separate port registries).
- Destroying a sandbox (`DELETE /sandboxes/{id}`) removes the entire `{SANDBOX_ROOT}/{PROJECT_NAME}/{sandbox_id}/` directory with no orphan files.
- `GET /runtime-dashboard/overview` (or equivalent) returns `sandbox_root`, `project_name`, `project_sandbox_dir`, and active sandbox list.
- The dashboard UI displays the sandbox root path and the project → sandbox topology.
- No hardcoded `ai-dev-factory` strings remain in sandbox path construction code.
- The existing sandbox lifecycle (create, start, stop, destroy) works end-to-end with the new root layout.
- `docker-compose.yml` mounts `SANDBOX_ROOT` so container-side code can access sandbox state at the new location.
