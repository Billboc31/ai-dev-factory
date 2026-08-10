Implementation complete. Here's a summary of everything that was done:

---

## Changes Made

### Modified files

**`services/supervisor/main.py`**
- Added `import time` and `from collections import deque` to imports
- Added 6 module-level state dicts for deploy sessions, per-project locks, and log file handlers
- Added `_DEPLOY_TYPE_ALLOWLIST`, `_validate_project_deploy_block()` (type check, `compose_file` path-containment, URL format), and `_get_project_deploy_lock()`
- Added persistence helpers: `_deploy_artifact_dir()`, `_write_deploy_log_line()` (RotatingFileHandler, 5 MB, 2 backups), `_write_deploy_state()` (atomic tmp→replace), `_update_deploy_history()` (bounded to 10, atomic)
- Added `_run_project_deploy_job()` background thread: stages `PENDING → BUILDING → STARTING → HEALTHCHECK → SUCCEEDED` (or `FAILED`), with bounded 50-line `deque` log tail; lock always released in `finally`
- Added 3 new endpoints: `POST /workspace/projects/{id}/deploy`, `GET .../deploy/history` (registered **before** `GET .../deploy/{deployment_id}` to avoid route collision)

**`services/supervisor/workspace_projects.example.yml`** — documented the full `deploy` block with all supported fields + a minimal deploy-only example

**`services/control_api/routes/workspace.py`** — added 3 transparent proxy routes (`/workspace/deploy`, `/workspace/deploy/history`, `/workspace/deploy/{id}`); the POST route passes the full status code + body through so 202/409/422 codes reach the frontend intact

**`apps/dashboard/src/api/workspace.js`** — added `deployProject`, `getDeployStatus`, `getDeployHistory`

**`apps/dashboard/src/components/ProjectWorkspacePanel.jsx`** — added deploy state, `usePolling` hook (2s, stops when terminal), `handleDeploy`, and the deploy UI section: button (disabled while running), stage badge, preview URL link, "Retry deploy" button on terminal states, log tail (`<pre>` scrollable), `not_deployable` banner, embedded `DeployHistoryPanel`

### New files

**`apps/dashboard/src/components/DeployHistoryPanel.jsx`** — fetches on mount, renders a table of last 5 deployments with timestamp, status badge, truncated SHA, and URL link

**`tests/test_deploy.py`** — 21 tests covering all acceptance criteria: validation, dirty-check, concurrency (409), lock-release-on-exception, SHA capture, path-escape rejection, success/failure/timeout flows, history bounding, GET cross-project 403/404, log tail ≤50 lines, retry after terminal state
