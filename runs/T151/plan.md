Now I have enough context to write the plan.

## Objective

Introduce a Deployment Environments dashboard as a UX and metadata abstraction layer on top of the existing `SandboxManager` infrastructure. No second orchestration engine is created — environments are sandboxes enriched with branch/ref, environment type, and deployment mode metadata.

## Included

### Backend

**`services/control_api/models/sandbox.py`**
- Add 3 enums: `EnvironmentType` (main, develop, integration, preview, sandbox, feature, custom), `EnvironmentMode` (deploy_and_test, persistent), `RefType` (branch, tag, commit, pr_ref)
- Add 7 optional fields to `SandboxState`, all defaulting to `None` for backward-compatibility: `env_name: str | None`, `env_type: EnvironmentType | None`, `ref: str | None`, `ref_type: RefType | None`, `deployment_mode: EnvironmentMode | None`, `deployed_at: str | None`, `stopped_at: str | None`

**`services/control_api/services/sandbox_manager.py`**
- Extend `create()` to accept optional kwargs `env_name`, `ref`, `ref_type`, `env_type`, `deployment_mode`; write them into `SandboxState` when provided
- In `start()`: stamp `state.deployed_at = datetime.utcnow().isoformat()` before writing state
- In `stop()`: stamp `state.stopped_at = datetime.utcnow().isoformat()` before writing state
- All existing logic unchanged

**`services/control_api/routes/environments.py`** (new file)
- Router prefix `/environments`, all handlers delegate to `SandboxManager`
- `POST /environments` — create env (body: `env_name`, `ref`, `ref_type`, `env_type`, `deployment_mode`, `project_root`); internally calls `SandboxManager.create()` then `SandboxManager.start()`
- `GET /environments` — list all sandboxes where `env_name is not None`
- `GET /environments/{env_id}` — calls `SandboxManager.status()`
- `POST /environments/{env_id}/redeploy` — calls `SandboxManager.restart()`
- `POST /environments/{env_id}/stop` — calls `SandboxManager.stop()`
- `DELETE /environments/{env_id}` — calls `SandboxManager.destroy()`, returns 204
- `POST /environments/{env_id}/refresh` — calls `SandboxManager.refresh()`
- `GET /environments/{env_id}/logs` — calls `SandboxManager.logs()`

**`services/control_api/main.py`**
- Import `environments_router` from `routes/environments.py` and register with `app.include_router()`

### Frontend

**`apps/dashboard/src/api/environments.js`** (new)
- 8 axios functions mirroring the new routes: `createEnvironment`, `listEnvironments`, `getEnvironment`, `redeployEnvironment`, `stopEnvironment`, `deleteEnvironment`, `refreshEnvironment`, `getEnvironmentLogs`

**`apps/dashboard/src/pages/EnvironmentsPage.jsx`** (new)
- Polls `listEnvironments()` every 5000ms via `usePolling`
- Renders a grid of `EnvironmentCard` components
- "New Environment" button opens `CreateEnvironmentModal`
- Error state via `ErrorBanner`

**`apps/dashboard/src/components/EnvironmentCard.jsx`** (new)
- Displays: `env_name`, `env_type` badge, `ref` + `ref_type`, `status` badge, `deployment_mode` badge
- Displays: `urls.web` and `urls.api` as clickable links, `deployed_at`, `stopped_at` timestamps
- Action buttons: Redeploy, Stop, Delete, Refresh, View Logs
- Log view uses existing `LogViewerDrawer` component pattern

**`apps/dashboard/src/components/CreateEnvironmentModal.jsx`** (new)
- Form fields: `env_name` (text input), `env_type` (select with enum values), `ref` (text input, e.g. branch name or commit SHA), `ref_type` (select), `deployment_mode` (radio: Deploy & Test / Persistent), `project_root` (text input)
- Submit calls `createEnvironment()`; closes modal on success

**`apps/dashboard/src/App.jsx`**
- Add `import EnvironmentsPage` and route `<Route path="/environments" element={<EnvironmentsPage />} />`

**`apps/dashboard/src/App.jsx` or existing nav component**
- Add "Environments" nav link pointing to `/environments` in the same nav list as `/runtime-dashboard`, `/sandboxes`, etc.

### Tests

**`tests/test_environment_routes.py`** (new, pytest + httpx async client)
1. `test_deploy_branch_environment` — POST /environments with ref=`feature/x`, verify response has `env_name`, `ref`, `deployed_at`
2. `test_deploy_persistent_environment` — POST with `deployment_mode=persistent`, verify field returned
3. `test_concurrent_environment_deployments` — create two envs, GET /environments returns both
4. `test_environment_deletion_cleanup` — POST then DELETE, GET returns 404
5. `test_branch_ref_display_correctness` — GET /environments/{id}, assert `ref` and `ref_type` match creation payload
6. `test_environment_lifecycle_transitions` — create → stop, verify `deployed_at` set and `stopped_at` set after stop
7. `test_dashboard_action_idempotency` — stop a stopped env, expect no 5xx error

## Excluded

- Any new orchestration engine, port registry, or supervisor lifecycle separate from `SandboxManager`
- `EnvironmentManager` class or `run_environment.py` worker
- Kubernetes, cloud deployment, GitHub Actions integration
- Authentication / permissions
- Automatic preview deployments per PR (future ticket)
- Deployment history, rollback, environment snapshots (future tickets)
- Modifying existing `/sandboxes` routes or `SandboxPanel.jsx` behavior
- Environment templates

## Acceptance criteria

- `GET /environments` returns only sandbox entries that carry `env_name` (i.e. were created via `/environments`)
- `SandboxState` JSON files for pre-existing sandboxes remain valid (all new fields default `None`)
- A sandbox created via `POST /environments` with `ref="develop"` returns `ref="develop"` in all subsequent GET responses
- After `POST /environments/{id}/stop`, `stopped_at` is a valid ISO timestamp in the state; `deployed_at` was set at creation
- Two environments created with different `env_name` values coexist and are both visible in `GET /environments`
- `DELETE /environments/{id}` followed by `GET /environments/{id}` returns 404
- `POST /environments/{id}/stop` on an already-stopped environment returns 2xx (idempotent)
- `/environments` nav link appears in the dashboard and renders the Environments page
- `pytest tests/test_environment_routes.py` passes with all 7 tests green
- No new supervisor process type, no new port allocation system beyond the existing `SandboxManager` slot registry
