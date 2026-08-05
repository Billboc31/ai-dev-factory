## Objective

Add a `redeploy_project` capability to the AI Workspace chat that lets a user trigger a `git pull` followed by Docker Compose service rebuilds for the backend and/or frontend of a locally hosted project, through the existing confirmation-gated action flow, with the deployment running in a background job so the Supervisor remains responsive.

## Included

### 1. New config file — `services/supervisor/workspace_projects.yml`

Schema per project (loaded at execution time via env var `WORKSPACE_PROJECTS_CONFIG`):

```yaml
projects:
  <project_id>:
    display_name: "Human-readable name"     # optional, shown in confirmation card
    repository_path: /host/path/to/repo
    default_branch: main
    allow_dirty: false         # false → reject if local uncommitted changes exist
    redeploy:
      backend:
        service: backend       # docker compose service name
      frontend:
        service: frontend
    preview_url: http://localhost:3000       # optional, returned on success
```

`_load_workspace_projects_config() -> dict` reads this file; returns `{}` on missing file. Called at each proposal and execution — never cached between requests.

---

### 2. `services/supervisor/main.py`

#### a. New module-level state

```python
# Per-project redeployment locks (in-memory; protects one Supervisor process/worker only)
_workspace_redeploy_locks: dict[str, threading.Lock] = {}
_workspace_redeploy_locks_mutex = threading.Lock()

# Background deployment job registry
_deployment_jobs: dict[str, dict] = {}        # keyed by deployment_id (UUID)
_deployment_jobs_lock = threading.Lock()
```

#### b. `_get_redeploy_lock(project_id: str) -> threading.Lock`

Follows the existing `_get_analysis_lock` pattern (lazy creation, `_workspace_redeploy_locks_mutex` guards the dict).

#### c. `_load_workspace_projects_config() -> dict`

Reads `WORKSPACE_PROJECTS_CONFIG` env var (default: path relative to supervisor package). Returns `{}` on `FileNotFoundError`. Parses YAML; returns `{}` on parse error (logged as warning).

#### d. `_git_has_local_changes(repo_path: str) -> bool`

Runs `subprocess.run(["git", "status", "--porcelain"], cwd=repo_path, timeout=10, capture_output=True, text=True)`. Returns `True` if stdout is non-empty. Raises on repo-not-found (non-existent path or non-git directory).

#### e. `_WORKSPACE_CAPABILITIES` — add entry

```python
"redeploy_project": {
    "description": "Pull the latest code and rebuild/restart selected services",
    "confirmation_required": True,
},
```

#### f. `_WORKSPACE_SYSTEM_PROMPT` — extend ALLOWED_CAPABILITIES

```
- redeploy_project: Pull latest code and rebuild/restart backend and/or frontend services.
  The branch is always the project's configured default branch (do not include a branch param).
  Params: pull (bool, default true), components (array, values: "backend", "frontend").
  proposed_action format: {"capability": "redeploy_project", "description": "...",
    "params": {"pull": true, "components": ["backend", "frontend"]}}
```

Update the RESPONSE FORMAT comment to document the optional `params` key.

#### g. `workspace_chat()` — proposal-time validation for `redeploy_project`

After the existing capability allowlist check, when `capability == "redeploy_project"`:

1. Load config via `_load_workspace_projects_config()`. If `project_id` not in config or `redeploy` key absent → set `intent = "informational"`, include explanation in `reply`, return with no `proposed_action`.
2. Extract `params` from LLM response:
   - `components`: must be a non-empty subset of configured `redeploy` keys for the project. Reject unknown components with `intent = "informational"`.
   - `pull`: default `True`. Accept only bool.
   - Do **not** accept a `branch` param from the LLM — the branch is always resolved from config.
3. Run `_git_has_local_changes(project_block["repository_path"])` informatively → `has_dirty_warning: bool`. On error (path missing, not a repo), set `has_dirty_warning = None`.
4. Store in `_pending_workspace_actions[action_id]` under `_workspace_lock`:

   ```python
   {
     "project_id": project_id,        # resolved configured key
     "capability": "redeploy_project",
     "description": <LLM description>,
     "params": {"pull": bool, "components": [...]},  # validated
     "has_dirty_warning": bool | None,              # informational only
     "created_at": <iso timestamp>,
   }
   ```

   **Not stored**: `repo_path`, branch, service names, preview URL — all re-derived from config at execution time.

5. Add to `result["proposed_action"]`:

   ```json
   {
     "capability": "redeploy_project",
     "description": "...",
     "action_id": "...",
     "project_id": "timizer",
     "safe_identifier": "timizer",        // project_id or display_name — never the host path
     "configured_branch": "main",         // from config, display only
     "pull": true,
     "components": ["backend", "frontend"],
     "has_dirty_warning": false
   }
   ```

#### h. `workspace_action_confirm()` — background-job branch for `redeploy_project`

After retrieving and validating the action (existing checks: action exists, project matches, capability allowlisted), add a special path for `redeploy_project` **before** calling `_execute_workspace_capability`:

1. Extract `components` and `pull` from `action["params"]`.
2. Attempt `lock = _get_redeploy_lock(project_id); acquired = lock.acquire(blocking=False)`.
3. If `not acquired` → return `JSONResponse(status_code=409, content={"detail": "deployment already running for project"})` without removing action from pending.
4. Generate `deployment_id = str(uuid4())`.
5. Under `_deployment_jobs_lock`, initialize:

   ```python
   _deployment_jobs[deployment_id] = {
     "deployment_id": deployment_id,
     "project_id": project_id,
     "status": "RUNNING",
     "stage": None,
     "started_at": <iso>,
     "completed_at": None,
     "result_message": None,
     "deployed_sha": None,
     "preview_url": None,
     "error_stage": None,
     "error_excerpt": None,
   }
   ```

6. Remove action from `_pending_workspace_actions` under `_workspace_lock`.
7. Spawn: `threading.Thread(target=_run_redeploy_job, args=(deployment_id, project_id, components, pull, lock), daemon=True).start()`.
8. Return immediately: `{"ok": True, "deployment_id": deployment_id, "status": "RUNNING"}`.

#### i. `_run_redeploy_job(deployment_id, project_id, components, pull, lock)` — new function

Runs in a daemon thread. Holds `lock` on entry; must release it unconditionally in `finally`.

**Top-level exception boundary**: the entire function body is wrapped in a `try / except Exception as exc` block with a `finally` that releases `lock`. Any uncaught exception writes `status="FAILED"`, `completed_at` (utc iso), `error_stage="INTERNAL_ERROR"`, `error_excerpt=str(exc)[:500]` to the job under `_deployment_jobs_lock`, and logs the full traceback server-side via `logger.exception`.

**Invariant**: when the thread exits (normally or via any exception), the job record must have `status` in `{"SUCCEEDED", "FAILED"}` and `completed_at` must be set.

All sensitive execution values resolved from config at the start of this function:

```python
config = _load_workspace_projects_config()
project_block = config.get("projects", {}).get(project_id)
```

If `project_block` is None (config changed since proposal) → update job to FAILED (`error_stage="CONFIG_MISSING"`, `completed_at` set), return.

Resolve:
- `repo_path = project_block["repository_path"]`
- `default_branch = project_block["default_branch"]`
- `allow_dirty = project_block.get("allow_dirty", False)`
- `service_map = {k: v["service"] for k, v in project_block["redeploy"].items()}`
- `preview_url = project_block.get("preview_url")`

If `repo_path` does not exist on disk → FAILED, `error_stage="PATH_NOT_FOUND"`, `completed_at` set. Return.

Validate that each component in `components` exists in `service_map`; FAILED, `error_stage="INVALID_COMPONENT"`, `completed_at` set. Return.

**Branch check (before any Git/Docker command):**
1. Run `git branch --show-current` in `repo_path` (timeout=10).
2. `FileNotFoundError` → FAILED, `error_stage="GIT_NOT_FOUND"`, `completed_at` set. Return.
3. `subprocess.TimeoutExpired` → FAILED, `error_stage="BRANCH_CHECK_TIMEOUT"`, `error_excerpt="git branch --show-current timed out"`, `completed_at` set. Return.
4. Non-zero returncode → FAILED, `error_stage="BRANCH_CHECK"`, `error_excerpt=stderr[:500]`, `completed_at` set. Return.
5. If current branch ≠ `default_branch` → FAILED, `error_stage="BRANCH_MISMATCH"`, `error_excerpt=f"current branch '{current}' differs from configured branch '{default_branch}'"`, `completed_at` set. Return.

**Fresh dirty check (before any Git/Docker command):**
1. Call `_git_has_local_changes(repo_path)`.
2. `FileNotFoundError` → FAILED, `error_stage="GIT_NOT_FOUND"`, `completed_at` set. Return.
3. `subprocess.TimeoutExpired` → FAILED, `error_stage="DIRTY_CHECK_TIMEOUT"`, `completed_at` set. Return.
4. If True and `allow_dirty` is False → FAILED, `error_stage="DIRTY_CHECK"`, `error_excerpt="uncommitted changes detected"`, `completed_at` set. Return.

**Execution sequence:**

For each stage, update `_deployment_jobs[deployment_id]["stage"]` under `_deployment_jobs_lock` before running the command.

- If `pull` is True:
  - Update stage → `"PULLING"`.
  - `subprocess.run(["git", "pull", "--ff-only", "origin", default_branch], cwd=repo_path, timeout=120, capture_output=True, text=True)`.
  - `subprocess.TimeoutExpired` → FAILED, `error_stage="PULLING"`, `error_excerpt="git pull timed out after 120 s"`, `completed_at` set. Return.
  - `FileNotFoundError` → FAILED, `error_stage="PULLING"`, `error_excerpt="git executable not found"`, `completed_at` set. Return.
  - Non-zero returncode → FAILED, `error_stage="PULLING"`, `error_excerpt=stderr[:500]`, `completed_at` set. Return.

- For each `component` in `components` (in order; first failure stops the loop):
  - `service = service_map[component]`.
  - Update stage → `f"BUILDING_{component}"`.
  - `subprocess.run(["docker", "compose", "up", "-d", "--build", service], cwd=repo_path, timeout=300, capture_output=True, text=True)`.
  - `subprocess.TimeoutExpired` → FAILED, `error_stage=f"BUILDING_{component}"`, `error_excerpt="docker compose timed out after 300 s"`, `completed_at` set. Return.
  - `FileNotFoundError` → FAILED, `error_stage=f"BUILDING_{component}"`, `error_excerpt="docker executable not found"`, `completed_at` set. Return.
  - Non-zero returncode → FAILED, `error_stage=f"BUILDING_{component}"`, `error_excerpt=stderr[:500]`, `completed_at` set. Return.

- Get deployed SHA: `subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=repo_path, timeout=10, ...)`. Failure here is non-fatal: use `deployed_sha = None`.

- Update job to SUCCEEDED: `deployed_sha`, `preview_url`, `result_message`, `completed_at`.

Log each stage to `logger.info("redeploy %s: stage=%s", project_id, stage)`.

`finally` block: `lock.release()`. Always executes on success, failure, timeout, and unexpected exception.

#### j. New Supervisor endpoint — `GET /workspace/projects/{project_id}/deployments/{deployment_id}`

Returns current job state for polling:

- 200: full `_deployment_jobs[deployment_id]` dict, when `_deployment_jobs[deployment_id]["project_id"] == project_id`.
- 404: `deployment_id` not found, or `project_id` mismatch.

---

### 3. `services/control_api/routes/workspace.py`

#### a. New polling proxy route

Add:

```text
GET /projects/{project_id}/workspace/deployments/{deployment_id}
```

This route must:
- use the existing project-resolution dependency to validate `project_id`;
- forward to the Supervisor endpoint `GET /workspace/projects/{project_id}/deployments/{deployment_id}`;
- preserve the Supervisor HTTP status code and JSON response body verbatim;
- return 404 for an unknown deployment or project mismatch (pass through Supervisor 404).

#### b. Propagate all Supervisor error statuses (≥ 400)

Update the workspace proxy forwarding helper so that **any** Supervisor response with `status_code >= 400` is returned with the original HTTP status. This currently applies to:

- `409 Conflict` (concurrent deployment already running);
- `404 Not Found` (unknown deployment, unknown action);
- any other 4xx or 5xx from the Supervisor.

The forwarded response must carry the same `status_code` and the same JSON body as the Supervisor response. It must not be silently collapsed to HTTP 200 with a `detail` field.

---

### 4. `apps/dashboard/src/api/workspace.js`

Add:

```js
export const getDeploymentStatus = (projectId, deploymentId) =>
  api.get(`/projects/${projectId}/workspace/deployments/${deploymentId}`);
```

The URL targets the Control API route added in §3a.

---

### 5. `apps/dashboard/src/components/ProjectWorkspacePanel.jsx`

#### Extend `ActionConfirmCard`

When `message.proposedAction?.capability === 'redeploy_project'`, render additional rows below the description:

- **Project**: `message.proposedAction.safe_identifier`
- **Branch**: `message.proposedAction.configured_branch`
- **Pull**: Yes / No from `message.proposedAction.pull`
- **Components**: comma-joined `message.proposedAction.components`
- **Local changes**: warning badge when `message.proposedAction.has_dirty_warning === true`

Do **not** display any host path. Use `safe_identifier` only.

No changes to the Confirm button or the existing `confirmWorkspaceAction` API call.

#### Background deployment polling in `handleConfirmAction`

When the confirm response includes `deployment_id` (i.e. `res.data.deployment_id`):

1. Update message state to `{ confirmed: false, deploymentId: res.data.deployment_id, deploymentStage: 'RUNNING' }`.
2. Start a polling loop (`setTimeout` chain, interval ~2 s) calling `getDeploymentStatus(projectId, deploymentId)`.
3. On each poll: update `deploymentStage` in message state.
4. On `status === 'SUCCEEDED'`: set `confirmed: true`, `confirmResult` to success message including SHA and preview URL. Stop polling.
5. On `status === 'FAILED'`: set `confirmError` to `${data.error_stage}: ${data.error_excerpt}`. Stop polling.
6. On HTTP 4xx or 5xx from the polling request: stop polling, display error.
7. Cap polling at 15 minutes; if exceeded, display "Deployment timed out — check supervisor logs."

#### Render deployment progress in `ActionConfirmCard`

When `message.deploymentId` is set and `message.confirmed` is false and no `confirmError`:
- Show spinner with current stage label (e.g. "PULLING…", "BUILDING backend…").
- Stage labels displayed: PULLING, BUILDING_backend, BUILDING_frontend, VERIFYING, SUCCEEDED, FAILED.

---

### 6. `tests/supervisor/test_workspace_redeploy.py` (new file)

#### Config and helpers

- `test_load_config_missing` — missing file → `{}`.
- `test_load_config_valid` — valid YAML → parsed correctly.
- `test_git_has_local_changes_clean` — empty porcelain → False.
- `test_git_has_local_changes_dirty` — non-empty porcelain → True.
- `test_git_has_local_changes_not_a_repo` — nonexistent path → raises.

#### Proposal-time validation

- `test_chat_unknown_project_returns_informational` — project not in config → intent=informational, no proposed_action.
- `test_chat_unknown_component_rejected` — LLM requests component not in config → intent=informational.
- `test_chat_branch_param_ignored` — LLM provides branch → stripped, configured branch used instead.
- `test_chat_has_dirty_warning_propagated` — dirty repo → `has_dirty_warning=True` in proposed_action.

#### Confirmation and lock

- `test_confirm_starts_background_job` — confirm returns `{ok: true, deployment_id: ..., status: "RUNNING"}` immediately.
- `test_confirm_concurrent_returns_409` — lock held → HTTP 409.
- `test_confirm_unknown_action_id_returns_404` — forged action_id → 404.

#### Background job execution

- `test_job_branch_mismatch_rejected` — current branch ≠ configured → FAILED (status set, completed_at set), no git pull or compose called.
- `test_job_dirty_between_proposal_and_confirm` — repo clean at proposal, dirty at execution → FAILED (status set, completed_at set).
- `test_job_pull_failure_stops_early` — git pull fails → FAILED PULLING (status set, completed_at set), no compose called.
- `test_job_first_component_failure_stops_loop` — backend compose fails → FAILED (status set, completed_at set), frontend compose not called.
- `test_job_backend_only` — components=["backend"] → compose called once for backend service only.
- `test_job_frontend_only` — components=["frontend"] → compose called once for frontend service only.
- `test_job_success_returns_sha_and_url` — full success → status=SUCCEEDED, deployed_sha present, preview_url present, completed_at set.
- `test_job_lock_released_after_failure` — command failure → lock released (can acquire again immediately), status=FAILED, completed_at set.
- `test_job_lock_released_after_exception` — unexpected exception in thread → lock released, status=FAILED, completed_at set, error_stage="INTERNAL_ERROR".
- `test_job_git_timeout` — git pull exceeds timeout → FAILED PULLING, lock released, status=FAILED, completed_at set.
- `test_job_compose_timeout` — docker compose exceeds timeout → FAILED BUILDING, lock released, status=FAILED, completed_at set.
- `test_job_git_not_found` — git executable missing (`FileNotFoundError`) → FAILED, `error_stage` set, lock released, completed_at set.
- `test_job_docker_not_found` — docker executable missing (`FileNotFoundError`) → FAILED, `error_stage` set, lock released, completed_at set.
- `test_job_path_not_exist` — configured path missing → FAILED PATH_NOT_FOUND, no subprocess called, lock released, completed_at set.
- `test_job_config_reloaded_at_execution` — stale repo_path in pending action not used; fresh config applied.
- `test_job_stale_service_name_ignored` — tampered service name not executed; service from config used.
- `test_job_config_missing_at_execution` — project removed from config between proposal and execution → FAILED CONFIG_MISSING, lock released, completed_at set.
- `test_job_terminal_state_always_set` — simulate unexpected exception → status=FAILED, completed_at set, error_stage="INTERNAL_ERROR", lock released.

#### Supervisor status polling endpoint

- `test_get_deployment_status_running` — job in RUNNING state → 200 with stage.
- `test_get_deployment_status_succeeded` — completed job → 200 with sha, preview_url.
- `test_get_deployment_status_project_mismatch` — wrong project_id → 404.
- `test_get_deployment_status_unknown` — unknown deployment_id → 404.

---

### 7. `tests/control_api/test_workspace_redeploy_proxy.py` (new file)

#### Control API proxy correctness

- `test_proxy_polling_200` — Supervisor returns 200 with job state → Control API returns 200 with unchanged body.
- `test_proxy_supervisor_409_becomes_control_api_409` — Supervisor returns 409 → Control API returns 409 (not 200 with detail).
- `test_proxy_supervisor_404_becomes_control_api_404` — Supervisor returns 404 → Control API returns 404.
- `test_proxy_unknown_project_returns_404` — project_id fails the existing project-resolution dependency → 404 before forwarding.

---

### 8. Frontend tests (`apps/dashboard/src/components/ProjectWorkspacePanel.test.jsx` or similar)

- `test_confirm_card_renders_redeploy_fields` — renders safe_identifier, configured_branch, pull, components.
- `test_confirm_card_shows_dirty_warning` — `has_dirty_warning=true` → warning badge visible.
- `test_confirm_card_no_host_path_displayed` — no element contains the literal `repository_path` value.
- `test_confirm_submits_only_action_id` — Confirm click sends only `action_id` to `confirmWorkspaceAction`; no path/branch/service override.
- `test_polling_shows_stage` — mock polling returns BUILDING_backend → spinner text updated.
- `test_polling_stops_on_succeeded` — SUCCEEDED state → confirmed bubble shown, no further fetch.
- `test_polling_stops_on_failed` — FAILED state → error shown, no further fetch.
- `test_polling_stops_on_http_error` — polling returns 4xx → error displayed, no further fetch.

---

### 9. `services/supervisor/workspace_projects.example.yml` (new file)

An example/documentation config with the full schema annotated; never loaded by tests.

---

## Excluded

- SSE or WebSocket streaming of deployment progress (polling via new GET endpoint is sufficient).
- Rollback on failure.
- Production or cloud deployment.
- Multi-host orchestration.
- Arbitrary remote shell access or LLM-composed commands.
- Hot-reload of `workspace_projects.yml` without Supervisor restart.
- Allowing the LLM or frontend to select a branch other than the configured default branch.
- Deployment cancellation or timeout-triggered abort.
- Redeploying a project other than the active workspace project via the chat context.

## Acceptance criteria

- From the workspace chat for project P, "pull and redeploy this project" resolves to P's configured recipe. Requesting an unconfigured project returns `intent=informational` with a refusal explanation and no `proposed_action`.
- `components: ["backend"]`, `components: ["frontend"]`, and `components: ["backend", "frontend"]` each result in only the requested Docker Compose services being rebuilt/restarted.
- No `git pull`, `git branch`, or `docker compose` command runs before the user clicks Confirm.
- The confirmation card displays: safe project identifier (not the host path), configured branch, pull flag, selected components, and a dirty-repo warning when applicable.
- At execution time, the background job re-reads `workspace_projects.yml` and derives `repo_path`, `default_branch`, service names, `allow_dirty`, and `preview_url` from config — values from the pending action or frontend are never used for command construction.
- The background job reads the current Git branch at execution time; if it differs from `default_branch`, the job fails with a branch-mismatch message before any Git or Docker command.
- The background job re-checks `git status --porcelain` at execution time; if dirty and `allow_dirty: false`, the job fails before any Git or Docker command.
- `workspace_action_confirm()` returns HTTP 409 when a deployment for the same project is already running; this 409 is preserved through the Control API proxy and reaches the dashboard as HTTP 409.
- The in-memory per-project lock is always released in a `finally` block, regardless of success, failure, timeout, or unexpected exception.
- `workspace_action_confirm()` returns within one second with `{ok: true, deployment_id: ..., status: "RUNNING"}`; the Supervisor remains responsive during deployment.
- When `_run_redeploy_job` exits (normally or via any exception), the deployment job record has `status` in `{"SUCCEEDED", "FAILED"}` and `completed_at` is always set. A job must never remain permanently in `"RUNNING"` after the thread exits.
- `subprocess.TimeoutExpired`, `FileNotFoundError`, missing/invalid configuration, missing repository path, non-Git repository, and unexpected exceptions each produce `status="FAILED"`, `completed_at` set, `error_stage` set to an appropriate label, and `error_excerpt` bounded to 500 characters.
- The frontend polls `GET /projects/{project_id}/workspace/deployments/{deployment_id}` on the Control API and updates the chat bubble with the current stage, deployed SHA and preview URL on success, or failed stage and log excerpt on failure.
- The Control API polling route validates `project_id` with the existing project-resolution dependency and forwards the Supervisor response status and body unchanged.
- Control API tests confirm: Supervisor 409 → Control API 409; Supervisor 404 → Control API 404; Supervisor 200 → Control API 200 with unchanged body.
- On success, the chat bubble shows the deployed git SHA and, when configured, the preview URL.
- On failure, the chat bubble shows the failed stage and the first 500 characters of the relevant stderr or error message.
- Frontend polling stops immediately when the response carries `status: "FAILED"`, `status: "SUCCEEDED"`, or an HTTP error; no further fetches are made after a terminal state.
- The three existing capabilities (`restart_daemon`, `rerun_dependency_analysis`, `resume_execution`) and all non-actionable workspace chat behavior continue to work unchanged.
- All test cases in `test_workspace_redeploy.py` and `test_workspace_redeploy_proxy.py` pass.
- No frontend test can construct or submit an arbitrary `repo_path`, branch, service name, or shell command via the confirmation card.
