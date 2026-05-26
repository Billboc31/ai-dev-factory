Now I have a complete picture of the codebase. Let me write the plan.

## Objective

Introduce a dedicated Environments / Deployments page in the dashboard that lets users deploy arbitrary refs (branches, tags, PR refs, commits) to named, concurrent environments, and manage their full lifecycle (deploy, redeploy, stop, delete, refresh) — integrated with the existing supervisor, docker-compose, worktree and proxy-URL infrastructure.

## Included

### Backend — Control API

**`services/control_api/models/environment.py`** — new file
- `EnvironmentMode` enum: `deploy_and_test`, `persistent`
- `EnvironmentType` enum: `main`, `develop`, `integration`, `preview`, `sandbox`, `feature`, `pr`, `custom`
- `EnvironmentStatus` enum: `creating`, `deploying`, `running`, `stopped`, `failed`, `deleted`
- `EnvironmentState` Pydantic model: `id`, `project_id`, `name`, `env_type`, `mode`, `ref`, `ref_type` (`branch|tag|commit|pr_ref`), `status`, `urls`, `health`, `created_at`, `deployed_at`, `stopped_at`, `last_step`, `error`, `worktree_path`, `compose_project`, `ports`, `supervisor_port`
- `EnvironmentDeployRequest` Pydantic model (POST body for create + deploy)

**`services/control_api/services/environment_manager.py`** — new file
- `create_environment(project_id, name, env_type, mode, ref, ref_type)` → `EnvironmentState`; allocates port slot from `environments-port-registry.json`, writes `{environments_root}/{env_id}/state.json`
- `deploy_environment(env_id)` → sends `POST /environments/start` to supervisor HTTP API; updates status to `deploying`
- `redeploy_environment(env_id)` → stop then deploy; idempotent (no-op if not running)
- `stop_environment(env_id)` → sends `POST /environments/{env_id}/stop` to supervisor; idempotent if already stopped
- `delete_environment(env_id)` → sends `DELETE /environments/{env_id}` to supervisor, removes state dir and port registry entry
- `refresh_environment(env_id)` → reload `state.json` from disk
- `list_environments(project_id=None)` → scan `environments_root` dirs
- `get_environment_logs(env_id, lines)` → tail `{environments_root}/{env_id}/run.log`
- Port slot allocation follows the same `port-registry.json` pattern as `sandbox_manager.py`; proxy URL registration via existing `ProxyManager`

**`services/control_api/routes/environments.py`** — new file
```
POST   /environments                          → EnvironmentState   (create; optional ?deploy=true)
GET    /environments                          → list[EnvironmentState]  (?project_id filter)
GET    /environments/{env_id}                 → EnvironmentState
POST   /environments/{env_id}/deploy          → ActionResult
POST   /environments/{env_id}/redeploy        → ActionResult
POST   /environments/{env_id}/stop            → ActionResult
DELETE /environments/{env_id}                 → 204
POST   /environments/{env_id}/refresh         → EnvironmentState
GET    /environments/{env_id}/logs            → LogsResponse  (?lines=200)
```

**`services/control_api/main.py`** — modify: register `environments` router

---

### Backend — Supervisor

**`services/supervisor/main.py`** — add new routes:
```
POST   /environments/start                    → spawn run_environment.py worker
GET    /environments/{env_id}/status          → read state.json from disk
GET    /environments/{env_id}/logs            → tail run.log (line-buffered)
POST   /environments/{env_id}/stop            → SIGTERM worker process
DELETE /environments/{env_id}                 → stop + cleanup worktree + remove dir
```

Worker process tracked by PID in `{environments_root}/{env_id}/worker.pid`

**`tools/agent_runner/run_environment.py`** — new file
- CLI: `--env-id`, `--project-id`, `--ref`, `--ref-type`, `--mode`, `--environments-root`
- Steps executed and recorded in `state.json` (`last_step`):
  1. `checkout` — create isolated git worktree at the requested ref (`git worktree add --detach ... {ref}`)
  2. `bootstrap` — run project bootstrap script
  3. `build` — run project build
  4. `start` — `docker compose up -d` with allocated env vars + ports
  5. `healthcheck` — poll project healthcheck URL
- For `mode=deploy_and_test`: after successful healthcheck, mark `status=running`; stop is triggered externally or after dashboard action
- For `mode=persistent`: same pipeline but environment stays running after healthcheck passes
- Writes `run.log` throughout; updates `state.json` status, `deployed_at`, `error`, `last_step`
- On failure: run undeploy (docker compose down), set `status=failed`

---

### Frontend

**`apps/dashboard/src/api/environments.js`** — new file
- `listEnvironments(projectId?)`, `getEnvironment(id)`, `createEnvironment(data)`
- `deployEnvironment(id)`, `redeployEnvironment(id)`, `stopEnvironment(id)`
- `deleteEnvironment(id)`, `refreshEnvironment(id)`, `getEnvironmentLogs(id, lines)`

**`apps/dashboard/src/pages/EnvironmentsPage.jsx`** — new file
- Top bar: project filter dropdown, environment type filter, status filter, "New Environment" button
- Environment list: one `EnvironmentCard` per environment, auto-refreshed every 5s
- "New Environment" opens `CreateEnvironmentModal`
- Log drawer: inline log viewer per environment (reuses `LogViewerDrawer` pattern from `runtime-dashboard/`)
- Empty state when no environments exist

**`apps/dashboard/src/components/environments/EnvironmentCard.jsx`** — new file
- Displays: name, env type badge, status badge, ref + ref_type chip, URLs as clickable links, health indicator, `created_at` / `deployed_at` timestamps, `last_step` progress hint, error message if failed
- Action buttons: Deploy (if stopped/failed), Redeploy (if running), Stop (if running), Delete, Refresh, View Logs toggle
- Action buttons disabled while status is `creating` or `deploying` (prevent double-submit)

**`apps/dashboard/src/components/environments/CreateEnvironmentModal.jsx`** — new file
- Fields: Project (selector), Name (text), Environment type (dropdown), Mode (radio: Deploy & Test / Persistent Environment), Ref (text input), Ref type (dropdown: branch / tag / commit / pr_ref)
- Submit calls `createEnvironment` then optionally `deployEnvironment` if mode warrants immediate deploy

**`apps/dashboard/src/App.jsx`** — modify: add route `/environments` → `EnvironmentsPage`

**`apps/dashboard/src/components/ProjectSidebar.jsx`** (or equivalent nav component) — modify: add "Environments" navigation link pointing to `/environments`

---

### Tests

**`tests/test_environment_manager.py`** — new file, covering:
- `test_deploy_branch_environment` — create + deploy a branch environment; assert `status=running`
- `test_deploy_persistent_environment` — create with `mode=persistent`; assert environment remains running after healthcheck
- `test_concurrent_environment_deployments` — deploy two environments for the same project; assert both coexist with distinct port allocations
- `test_environment_deletion_cleanup` — delete a running environment; assert worktree removed and port registry entry freed
- `test_branch_ref_display_correctness` — assert `ref` and `ref_type` stored and returned correctly for branch, tag, commit, pr_ref inputs
- `test_environment_lifecycle_transitions` — drive state machine through: creating → deploying → running → stopped → deleted
- `test_dashboard_action_idempotency` — call deploy twice, stop twice, delete twice; assert no errors and final state is consistent

## Excluded

- Kubernetes, cloud deployment, GitHub Actions integration
- Authentication, access control, permissions
- Automatic PR preview deployments (future ticket)
- Deployment history / audit trail beyond current run log
- Environment templates, snapshots, pinning, rollback
- Distributed deployment scheduling
- Any changes to existing sandbox (`/sandboxes/*`), deployer (`/deployer/*`), or runtime dashboard routes — those remain untouched
- Multi-host or remote deployment targets

## Acceptance criteria

- `GET /environments` returns all environments across projects; filtered correctly by `?project_id=`
- A new environment created via `POST /environments` with `ref=my-branch&ref_type=branch` shows `ref=my-branch` and `ref_type=branch` in subsequent GET responses
- Two environments for the same project can be deployed concurrently; each has distinct port allocations and distinct URLs
- `POST /environments/{env_id}/deploy` called twice while already deploying is a no-op (returns current state, no duplicate worker spawned)
- `DELETE /environments/{env_id}` removes the worktree directory and frees the port registry slot; a subsequent `GET` returns 404
- `mode=persistent` environment remains `status=running` after healthcheck succeeds without any further API call
- `mode=deploy_and_test` environment transitions to `status=running` and can be stopped via `POST /environments/{env_id}/stop`
- Dashboard `/environments` page renders all environments with name, type badge, status badge, ref chip, URLs, timestamps and action buttons
- Action buttons are disabled while status is `creating` or `deploying`
- Log drawer for an environment tails `run.log` with offset-based streaming (same pattern as existing `LogViewerDrawer`)
- All seven integration tests in `test_environment_manager.py` pass
- No existing routes (`/sandboxes/*`, `/projects/{id}/sandbox/*`, `/runtime-dashboard/*`) are broken
