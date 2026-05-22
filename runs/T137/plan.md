I have enough context to write the plan.

## Objective

Prevent sandbox validation runs from colliding with main runtime ports (API 8080, web 3000) by allocating isolated ports per run, writing a sandbox-specific deploy env file into each worktree, and showing historical sandbox runs with their port allocation, worktree path, and cleanup actions in the dashboard.

## Included

### A — Port isolation in `tools/agent_runner/run_sandbox.py`

- Add `_allocate_port_slot(sandbox_id)`: reads `{RUNTIME_ROOT}/sandboxes/port-registry.json`, finds the next unused integer slot ≥ 1 (slot 0 is the main runtime), writes the registry back. Use `fcntl.flock()` with `LOCK_EX` on a companion `.port-registry.lock` file for cross-process safety (run_sandbox.py is a subprocess independent of the API container).
- Add `_release_port_slot(sandbox_id)`: removes the sandbox_id entry from `port-registry.json` (same lock).
- Port formulas, mirroring `sandbox_manager.py`: `api_port = 8080 + slot * 100`, `web_port = 3000 + slot * 100`.
- Add `_write_sandbox_env(sandbox_dir, sandbox_id, runtime_root, project_root, slot_ports, compose_project)`: writes a `deploy.env` file at `{sandbox_dir}/deploy.env` containing `AI_DEV_FACTORY_RUNTIME_ROOT`, `AI_DEV_FACTORY_PROJECT_ROOT`, `AI_DEV_FACTORY_SUPERVISOR_PORT` (read from env, default 8090), `API_PORT`, `WEB_PORT`, `COMPOSE_PROJECT_NAME`, `SANDBOX_ID`.
- Modify `_do_sandbox()`:
  - Allocate a port slot before creating the worktree.
  - Compute `compose_project = f"sandbox-{sandbox_id}"`.
  - Call `_write_sandbox_env(...)` after allocating ports.
  - Pass sandbox env vars (`API_PORT`, `WEB_PORT`, `COMPOSE_PROJECT_NAME`, `SANDBOX_ID`) as extra entries in the subprocess environment passed to `_run_scripts()`.
  - Include `ports`, `worktree_path`, `compose_project` in `state_base` and all `_write_state` calls.
  - Call `_release_port_slot(sandbox_id)` at the end of `_do_sandbox` in a `finally` block (whether success, failure, or exception).
- Modify `_run_scripts()`: accept an `extra_env: dict` parameter and merge it into `os.environ.copy()` before passing as `env=` to every `subprocess.run()` call. This makes the env vars available to `docker compose` for variable substitution without requiring scripts to source a file.

### B — Parameterise `docker-compose.yml`

- Change the `api` service port mapping from `"8080:8080"` to `"${API_PORT:-8080}:8080"`.
- Change the `web` service port mapping from `"3000:80"` to `"${WEB_PORT:-3000}:80"`.
- Main runtime is unaffected (defaults remain 8080/3000 when variables are not set).

### C — State schema enrichment in `services/control_api/models/schemas.py`

- Add `ports: dict[str, int] = {}` to `SandboxValidationState`.
- Add `worktree_path: str | None = None` to `SandboxValidationState`.
- Add `compose_project: str | None = None` to `SandboxValidationState`.
- Mirror the same three fields in `SandboxValidationStatus`.

### D — Pass new fields through `services/control_api/services/sandbox_runner.py`

- In `_state_from_payload()`: extract `ports = raw.get("ports") or {}`, `worktree_path = raw.get("worktree_path")`, `compose_project = raw.get("compose_project")` and populate the returned `SandboxValidationState`.

### E — Update status route and add runs endpoints in `services/control_api/routes/sandbox.py`

- In `get_project_sandbox_status()`: pass `ports`, `worktree_path`, `compose_project` from `state` into the `SandboxValidationStatus(...)` constructor.
- Add a new `runs_router = APIRouter(prefix="/sandbox-runs", tags=["sandbox"])`.
  - `GET /api/sandbox-runs`: scan `{RUNTIME_ROOT}/sandboxes/*/state.json`, parse each as a raw dict, return entries that contain a `project_id` key (validation runs) rather than `ticket_id` (SandboxManager entries). Return as `list[SandboxValidationStatus]`.
  - `GET /api/sandbox-runs/{sandbox_id}/logs`: read `{RUNTIME_ROOT}/sandboxes/{sandbox_id}/run.log` from disk and return lines as `SandboxValidationLogsResponse`. Return empty list if missing.
  - `DELETE /api/sandbox-runs/{sandbox_id}` (status 204): remove `{RUNTIME_ROOT}/sandboxes/{sandbox_id}/` (using `shutil.rmtree`). If the directory has a `worktree/` subdirectory, run `git worktree remove --force <path>` first. Remove the sandbox_id entry from `port-registry.json` (with the same file lock). Return 404 if sandbox_id directory does not exist. Must not touch any path outside `{RUNTIME_ROOT}/sandboxes/{sandbox_id}/`.
- Mount `runs_router` in `main.py` (or wherever routers are registered).

### F — Dashboard: enrich `SandboxStatusPanel` in `apps/dashboard/src/pages/DeployerPage.jsx`

- Add a `PortsTable`-style display of `status.ports` (when non-empty) inside `SandboxStatusPanel`.
- Show `status.worktree_path` (when present) as a monospace truncated line.
- Add a manual "Refresh" button that calls the existing `fetchStatus` callback.

### G — New component `apps/dashboard/src/components/SandboxRunsPanel.jsx`

- Fetch `GET /api/sandbox-runs` on mount and every 10 s.
- Render each run as a row showing: sandbox_id, project_id, state badge, started_at, finished_at, last_step, ports (as a `PortsTable`), worktree_path.
- Per-row actions:
  - **Logs** button: opens a modal fetching `GET /api/sandbox-runs/{id}/logs`.
  - **Cleanup** button: calls `DELETE /api/sandbox-runs/{id}`, then refreshes the list. Disabled while running.
- Heading "Sandbox Runs" with a "Refresh" button.
- Accepts an optional `maxRows` prop (default unlimited).

### H — Dashboard: add API client calls

- `apps/dashboard/src/api/deployer.js` (or a shared `sandbox.js`):
  - `listSandboxRuns()` → `GET /api/sandbox-runs`
  - `getSandboxRunLogs(sandboxId, lines)` → `GET /api/sandbox-runs/{id}/logs?lines={lines}`
  - `cleanupSandboxRun(sandboxId)` → `DELETE /api/sandbox-runs/{id}`

### I — Render `SandboxRunsPanel` in the dashboard

- Import and render `<SandboxRunsPanel />` in the page that already shows `<SandboxPanel />` (likely the Sandboxes route or a new "Validation Runs" tab/section within the same page).

## Excluded

- AI fix loop (retry on failure).
- Tester agent integration.
- Cloud or remote deployment.
- Automatic merge on validation success.
- Changing the SandboxManager's in-process thread lock to a file lock (separate concern; the API container is single-process so the existing threading.Lock is sufficient for SandboxManager alone).
- Per-project port reservation across concurrent validation runs (single concurrent run per project is the assumed constraint).
- Supervisor-side listing or cleanup endpoints (the control API reads the runtime root volume directly).

## Acceptance criteria

- Running sandbox validation no longer binds to ports 8080 or 3000; the allocated API and web ports appear in the validation state and in logs.
- Each validation run has its own `sandboxes/{sandbox_id}/deploy.env` file containing all required fields (runtime root, project root, supervisor port, API port, web port, compose project name, sandbox id).
- Each validation run uses a unique docker compose project name (`sandbox-{sandbox_id}`), verifiable with `docker compose ls`.
- The `port-registry.json` file contains the sandbox's slot during the run and is cleaned of that slot after the run completes.
- `docker-compose.yml` contains `${API_PORT:-8080}` and `${WEB_PORT:-3000}`; the main runtime still starts on 8080/3000 without any additional configuration.
- `GET /api/projects/{id}/sandbox/status` returns `ports`, `worktree_path`, and `compose_project` fields for a completed run.
- `GET /api/sandbox-runs` returns all historical validation runs (state, sandbox_id, project_id, timestamps, ports, worktree_path).
- `GET /api/sandbox-runs/{id}/logs` returns the full run log.
- `DELETE /api/sandbox-runs/{id}` removes the worktree and sandbox directory; the main runtime directories and other sandboxes are untouched.
- The dashboard sandbox status panel shows ports and worktree path for the active/last run.
- The dashboard "Sandbox Runs" panel lists historical runs with Logs and Cleanup buttons.
- Cleanup of a completed sandbox run succeeds; the same cleanup on a non-existent id returns 404.
