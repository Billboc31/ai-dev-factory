## Objective

Add a one-click deployment action for workspace projects so a human can deploy and validate a generated application directly from the AI Dev Factory dashboard, without touching the terminal. Deployment is declarative, concurrency-safe, SHA-tracked, and includes a healthcheck stage before reporting success.

## Included

### Deployment config schema — `workspace_projects.yml`

Add an optional `deploy` block to the per-project entry. The block is declarative; no free-form shell commands or arbitrary paths are accepted from frontend or LLM input:

```yaml
deploy:
  type: docker-compose          # only supported value in this ticket
  compose_file: docker-compose.yml   # repository-relative path, validated after normalization
  preview_url: http://localhost:3000
  healthcheck_url: http://localhost:3000/health   # optional; if absent, skip healthcheck stage
  healthcheck_timeout_s: 60     # default 60 s
  healthcheck_interval_s: 5     # default 5 s
  allow_dirty: false            # default false — reject if working tree is dirty
```

**Deployability rule:** a project is deployable if and only if it has an explicit `deploy` block in `workspace_projects.yml`. The mere presence of a `docker-compose.yml` in the repository does **not** make a project deployable. If the `deploy` block is absent, `POST /deploy` returns `422 not_deployable`.

**Schema validation:** on supervisor startup and on every deploy request, validate the `deploy` block (type allowlist, `compose_file` path normalization and containment check, URL format). An invalid block returns `422 invalid_deploy_config`.

**`compose_file`** is resolved relative to the repository root registered in `workspace_projects.yml`. The resolved path must remain inside the repository root (no `..` escape). Execution uses `subprocess.run([..], shell=False)` — never `shell=True`.

Update `workspace_projects.example.yml` with the new block.

---

### Supervisor — in-memory job registry

Add a module-level dict `_deploy_sessions: dict[str, DeploymentSession]` keyed by `deployment_id`. Each session holds:

| Field | Type | Notes |
|---|---|---|
| `deployment_id` | `str` | UUID4, assigned at POST |
| `project_id` | `str` | for cross-project validation |
| `stage` | `str` | `PENDING` / `BUILDING` / `STARTING` / `HEALTHCHECK` / `SUCCEEDED` / `FAILED` |
| `status` | `str` | `running` / `succeeded` / `failed` |
| `started_at` | `str` | ISO-8601 |
| `completed_at` | `str` \| `None` | |
| `deployed_sha` | `str` \| `None` | captured before launch |
| `log_tail` | `deque[str]` | bounded to 50 lines |
| `preview_url` | `str` \| `None` | populated on success |
| `error` | `str` \| `None` | first error line on failure |

A per-project `asyncio.Lock` dict `_deploy_locks: dict[str, Lock]` enforces single-active-deployment per project.

---

### Supervisor — new endpoints (`services/supervisor/main.py`)

**`POST /workspace/projects/{project_id}/deploy`**

1. Look up project config; validate `deploy` block — `422 not_deployable` / `422 invalid_deploy_config` if missing or invalid.
2. Acquire `_deploy_locks[project_id]` non-blocking; if already held, return `409 DEPLOYMENT_IN_PROGRESS` with the active `deployment_id`.
3. Run `git rev-parse HEAD` in the repository path (no shell); capture `deployed_sha`. If the working tree is dirty and `allow_dirty: false`, release lock and return `422 dirty_working_tree`.
4. Allocate a `DeploymentSession`, insert into `_deploy_sessions`, launch background task.
5. Return `202 Accepted` with `{ "deployment_id": "..." }`.

Background task (lock held, released in `finally`):

- Stage `BUILDING`: run `docker compose -f <compose_file> up -d --build` as an argv list (`shell=False`); stream stdout/stderr line by line into the bounded `log_tail` deque (cap 50 lines) and append to `project-deploy.log`.
- Stage `STARTING`: wait 2 s (configurable via `startup_wait_s`, default 2).
- Stage `HEALTHCHECK` (if `healthcheck_url` configured): poll `healthcheck_url` with `httpx.AsyncClient` every `healthcheck_interval_s` until success or `healthcheck_timeout_s` expires. On timeout → `FAILED`.
- Stage `SUCCEEDED`: set status, `completed_at`, `preview_url`.
- On any exception or timeout → set stage `FAILED`, capture error message.
- `finally`: release `_deploy_locks[project_id]`; write persistence files (see below).

**`GET /workspace/projects/{project_id}/deploy/{deployment_id}`**

- Look up `_deploy_sessions[deployment_id]`; return `404` if absent.
- Validate that `session.project_id == project_id`; return `403` otherwise.
- Return `{ deployment_id, stage, status, log_tail: list(session.log_tail), preview_url, error, started_at, completed_at, deployed_sha }`.

**`GET /workspace/projects/{project_id}/deploy/history`**

- Read `.ai-dev-factory/project-deploy-history.json` for the project; return the last 5 records (empty list if file absent).

---

### Persistence model

Two files written inside the project's repository root under `.ai-dev-factory/`:

**`project-deploy-state.json`** — latest deployment only:
```json
{ "deployment_id": "...", "status": "succeeded", "stage": "SUCCEEDED",
  "started_at": "...", "completed_at": "...", "deployed_sha": "...",
  "preview_url": "...", "error": null }
```

**`project-deploy-history.json`** — bounded array of at most 10 records, newest first:
```json
[ { "deployment_id": "...", "status": "...", "started_at": "...",
    "completed_at": "...", "deployed_sha": "...", "preview_url": "..." }, ... ]
```

Both files are written atomically (write to a `.tmp` sibling, then `os.replace`). The history array is trimmed to 10 entries before writing. The history endpoint returns the last 5 of those.

**`project-deploy.log`** — raw stdout/stderr appended per deployment, rotated at 5 MB (keep 2 backups) using `logging.handlers.RotatingFileHandler`.

Logs exposed through the polling endpoint are the in-memory bounded tail only (50 lines max). Raw log files are not streamed to the dashboard; secrets visible in logs are the operator's responsibility and are documented as a known limitation.

---

### Dashboard frontend

**`apps/dashboard/src/api/workspace.js`**

Add:
- `deployProject(projectId)` — `POST /workspace/projects/{project_id}/deploy`
- `getDeployStatus(projectId, deploymentId)` — `GET .../deploy/{deployment_id}`
- `getDeployHistory(projectId)` — `GET .../deploy/history`

**`apps/dashboard/src/components/ProjectWorkspacePanel.jsx`**

- Add "Deploy project" `ActionButton`.
- Button is disabled while `status === 'running'` (no duplicate trigger).
- On click: call `deployProject`, store `deployment_id`, start polling via `usePolling` hook.
- Display current `stage` as a step indicator.
- Display last 50 log lines (scrollable, monospace).
- On `succeeded`: show `preview_url` as a clickable link; show "Retry" button.
- On `failed`: show error message; show "Retry" button; hide preview link.
- On `422 not_deployable`: display a non-action banner "This project has no deployment configuration."
- Retry re-calls `deployProject` (backend allows it once lock is free).

**`apps/dashboard/src/components/DeployHistoryPanel.jsx`** *(new small component)*

- Fetched from `getDeployHistory` on panel mount.
- Renders a table: timestamp, status badge, SHA (truncated), URL link (if succeeded).
- Embedded at the bottom of `ProjectWorkspacePanel`.

**Existing files not modified:**
- `deployer_runner.py` / `DeployerPage.jsx` (factory's own deployer)
- T227 `redeploy_project` handler

---

### Tests

**Backend (`tests/test_deploy.py`):**
- No `deploy` block → `POST` returns `422 not_deployable`.
- Invalid `deploy` block (bad type, path escape) → `422 invalid_deploy_config`.
- Concurrent `POST` while active → second returns `409 DEPLOYMENT_IN_PROGRESS`.
- Lock released in `finally` after exception in background task.
- `deployed_sha` captured before subprocess launch.
- Dirty working tree with `allow_dirty: false` → `422 dirty_working_tree`.
- Dirty working tree with `allow_dirty: true` → deployment proceeds.
- `compose_file` path containing `..` → rejected at validation.
- Successful build + healthcheck → `stage=SUCCEEDED`, `preview_url` set.
- Successful build + healthcheck failure → `stage=FAILED`.
- Healthcheck timeout → `stage=FAILED`.
- History file contains last 5 records after 6 deployments.
- `GET .../deploy/{id}` with wrong `project_id` → `403`.
- `log_tail` never exceeds 50 lines regardless of subprocess output volume.
- Retry `POST` after terminal state (`succeeded` or `failed`) → allowed, returns new `deployment_id`.

**Frontend (`tests/` or Vitest):**
- "Deploy project" button is disabled while `status === 'running'`.
- Preview URL link appears only after `succeeded`.
- `not_deployable` banner renders without action button.
- History table renders last 5 rows.

## Excluded

- Automatic production deployments.
- Blue/green, canary, or rollback strategies.
- Multi-environment management.
- Automatic UI validation or regression test generation.
- Kubernetes / cloud-provider integrations.
- Deployment config generation for projects without an existing config (separate ticket).
- Migrating existing deployment history.
- Authentication / access control on new endpoints (inherits current supervisor policy).
- Streaming raw log files to the dashboard (bounded tail only).
- Secret redaction from logs (documented limitation, not implemented here).
- Any deployment type other than `docker-compose` (extensible but not implemented in this ticket).

## Acceptance criteria

- `POST /workspace/projects/{project_id}/deploy` returns `422 not_deployable` when no `deploy` block is present; `422 invalid_deploy_config` when the block is malformed or contains an escaping path; `409 DEPLOYMENT_IN_PROGRESS` with the active `deployment_id` when another deployment is already running for that project; `202 Accepted` with a new `deployment_id` otherwise.
- `git rev-parse HEAD` is executed before the subprocess is launched and the result is stored as `deployed_sha` in the session and persistence files.
- A dirty working tree is rejected with `422 dirty_working_tree` unless the project config explicitly sets `allow_dirty: true`.
- `compose_file` paths are normalized and validated to remain inside the repository root; any path escape is rejected at config validation time.
- Deployment stages progress as `PENDING → BUILDING → STARTING → HEALTHCHECK → SUCCEEDED` (or `FAILED` at any stage). If `healthcheck_url` is absent, `HEALTHCHECK` stage is skipped.
- A deployment transitions to `SUCCEEDED` only after the healthcheck HTTP call returns a 2xx response within `healthcheck_timeout_s`. Timeout or non-2xx response transitions to `FAILED`.
- `GET /workspace/projects/{project_id}/deploy/{deployment_id}` returns `403` when `deployment_id` belongs to a different `project_id`; returns `404` when unknown.
- Polling response `log_tail` contains at most 50 lines regardless of actual subprocess output volume.
- `.ai-dev-factory/project-deploy-state.json` is written atomically with the latest deployment result.
- `.ai-dev-factory/project-deploy-history.json` is written atomically and contains at most 10 records; `GET .../deploy/history` returns the last 5.
- `project-deploy.log` is rotated at 5 MB with 2 backups.
- Per-project `asyncio.Lock` is always released in `finally`, including after subprocess exception or timeout.
- The dashboard "Deploy project" button is disabled while `status === 'running'`; enabled after any terminal state.
- The dashboard shows a non-action `not_deployable` banner and no deploy button when the project config lacks a `deploy` block.
- Preview URL is rendered as a clickable link only after `SUCCEEDED`; a retry button appears on `FAILED`.
- All existing workspace actions (pull, redeploy) are unaffected.
- `workspace_projects.example.yml` documents the new `deploy` block with all supported fields.
- All listed backend and frontend tests pass.
