Now I have enough context. Here is the plan:

## Objective

Add a one-click deployment action for workspace projects so a human can deploy and validate a generated application directly from the AI Dev Factory dashboard, without touching the terminal.

## Included

**Supervisor — new deployment endpoint and background job handler**
- `services/supervisor/main.py`: add `POST /workspace/projects/{project_id}/deploy` endpoint, mirroring the `redeploy_project` pattern (T227, lines 3622–3797); add `deploy_project` background handler that:
  1. reads the project's deploy config (checks for `deploy.yml` or `docker-compose.yml` in the repository path defined in `workspace_projects.yml`);
  2. returns `422 Unprocessable Entity` with `not_deployable` reason if no config is found (deployability check);
  3. runs the deployment pipeline (e.g. `docker compose up -d --build` or custom deploy command from config);
  4. captures stdout/stderr line by line into an in-memory log buffer;
  5. resolves the `preview_url` from config once the pipeline succeeds;
  6. writes final state to a new per-project JSON file `.ai-dev-factory/project-deploy-state.json` (status, started_at, completed_at, preview_url, deployed_sha);
  7. appends log lines to `.ai-dev-factory/project-deploy.log`.
- `services/supervisor/main.py`: add `GET /workspace/projects/{project_id}/deploy/{deployment_id}` polling endpoint (same shape as existing deployment status endpoint at lines ~2907-2908).
- `services/supervisor/main.py`: add `GET /workspace/projects/{project_id}/deploy/history` endpoint returning the last N deployment records (read from `project-deploy-state.json`).

**workspace_projects.yml schema extension**
- Add optional `deploy` block to the per-project config schema (alongside existing `redeploy` block):
  ```yaml
  deploy:
    command: docker compose up -d --build   # or path to a deploy script
    preview_url: http://localhost:3000
    healthcheck: curl -sf http://localhost:3000/health
  ```
- Document the new key in `workspace_projects.example.yml`.

**Dashboard frontend**
- `apps/dashboard/src/api/workspace.js`: add `deployProject(projectId)` and `getDeployStatus(projectId, deploymentId)` and `getDeployHistory(projectId)` API functions.
- `apps/dashboard/src/components/ProjectWorkspacePanel.jsx`: add a "Deploy project" button (reuse `ActionButton` pattern); wire polling loop (reuse `usePolling` hook) to display live stage and log tail; show `preview_url` as a clickable link on success; show retry button on failure.
- `apps/dashboard/src/components/DeployHistoryPanel.jsx` *(new small component)*: renders the last N deployments (timestamp, status badge, URL, link to logs) fetched from the history endpoint; embedded inside `ProjectWorkspacePanel`.

**Existing workflows left unchanged**
- The existing `deployer_runner.py` / `DeployerPage.jsx` (which deploys ai-dev-factory itself) is not modified.
- The T227 `redeploy_project` handler is not modified.

## Excluded

- Automatic production deployments.
- Blue/green, canary, or rollback strategies.
- Multi-environment management.
- Automatic UI validation or regression test generation.
- Kubernetes / cloud-provider integrations.
- Deployment config generation for projects that do not already have a `deploy.yml` or `docker-compose.yml` (a separate ticket should handle scaffolding).
- Migrating existing deployment history from another source.
- Authentication / access control on the new endpoints (inherits whatever the supervisor currently uses).

## Acceptance criteria

- `POST /workspace/projects/{project_id}/deploy` returns `422` with `not_deployable` if the project has no detected deploy config; returns `200` with a `deployment_id` otherwise.
- `GET /workspace/projects/{project_id}/deploy/{deployment_id}` returns a status object with `stage`, `status` (`running` / `succeeded` / `failed`), `log_tail` (last 50 lines), and `preview_url` (populated on success).
- On success, `.ai-dev-factory/project-deploy-state.json` is written with `status=succeeded`, `preview_url`, `deployed_sha`, and timestamps.
- On failure, status is `failed` and the log tail contains the relevant error output.
- The dashboard "Deploy project" button triggers the endpoint, shows live stage progression, and displays the URL as a clickable link when done.
- A failed deployment can be retried by clicking the button again (no 409 conflict once the previous job is finished).
- `GET /workspace/projects/{project_id}/deploy/history` returns the last 5 deployment records.
- All existing workspace actions (pull, redeploy) work without change.
- `workspace_projects.example.yml` documents the new `deploy` block.
