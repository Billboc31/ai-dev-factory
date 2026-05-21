Now I have a thorough picture of the existing deployer code. Let me produce the plan.

## Objective

Add real deployment execution to the T127 deployer skeleton: load and run `deploy.yml` steps from Python, add deploy/restart API actions with per-project locking, capture logs, run post-deploy healthchecks, and expose status/logs in both the API and dashboard.

## Included

### New file: `services/control_api/services/deployer_runner.py`

- `get_deploy_state(project_root: Path) → DeployState` — reads `deploy-state.json`; detects stale "running" state via stored PID and resets to idle if PID is gone
- `run_deploy(project_id: str, project_root: Path) → ActionResult` — acquires in-process `threading.Lock` per project (non-blocking); returns 409-equivalent if locked; writes state file with `state="running"` + PID; runs each `DeployComponent` sequentially via `subprocess.run`; appends stdout/stderr to deploy log file; runs global healthcheck (with retries) if defined in profile; writes `state="success"` or `state="failed"` when done
- `run_restart(project_id: str, project_root: Path) → ActionResult` — same lock/log/state machinery; for `type=docker` components calls `docker compose restart {service}`; for `type=host` components re-runs `command`
- `get_deploy_logs(project_root: Path, lines: int) → list[str]` — reads last N lines from deploy log file

State file path: `{AI_DEV_FACTORY_RUNTIME_ROOT}/state/deploy-state.json` if env set, else `{project_root}/.ai-dev-factory/deploy-state.json`.  
Log file path: `{AI_DEV_FACTORY_RUNTIME_ROOT}/logs/deploy.log` if env set, else `{project_root}/.ai-dev-factory/deploy.log`.

### Modified: `services/control_api/models/schemas.py`

- Expand `DeployerStatus.state` from `Literal["idle"]` to `Literal["idle", "running", "success", "failed"]`
- Add `started_at: str | None`, `finished_at: str | None`, `error: str | None`, `last_step: str | None` to `DeployerStatus`
- Add `DeployHealthcheck(command: str, timeout: int = 30, retries: int = 3, delay: int = 5)` model
- Add `healthcheck: DeployHealthcheck | None = None` to `DeployProfile`
- Add `DeployLogsResponse(lines: list[str])` model

### Modified: `services/control_api/routes/deployer.py`

- Update `GET /projects/{project_id}/deployer/status` — call `get_deploy_state()` instead of only checking file presence; return full `DeployerStatus`
- Add `POST /projects/{project_id}/deployer/deploy` → calls `run_deploy()`; returns `ActionResult`; HTTP 409 if deploy already running
- Add `POST /projects/{project_id}/deployer/restart` → calls `run_restart()`; returns `ActionResult`; HTTP 409 if deploy already running
- Add `GET /projects/{project_id}/deployer/logs?lines=100` → calls `get_deploy_logs()`; returns `DeployLogsResponse`

### Modified: `apps/dashboard/src/api/deployer.js`

- Add `triggerDeploy(projectId)` → `POST /projects/{projectId}/deployer/deploy`
- Add `triggerRestart(projectId)` → `POST /projects/{projectId}/deployer/restart`
- Add `getDeployLogs(projectId, lines)` → `GET /projects/{projectId}/deployer/logs`

### Modified: `apps/dashboard/src/pages/DeployerPage.jsx`

- Add Deploy and Restart buttons (disabled while state is "running")
- Show deploy status badge: idle / running (spinner) / success / failed
- Show "Last error" line when state is failed
- Add a collapsible Logs panel that fetches and displays log lines (auto-refreshes while running)
- Polling interval stays 5 s; stop polling when state is success or failed

### New file: `tests/test_deployer_execution.py`

- `test_deploy_success` — deploy.yml with a `type=host` component that exits 0; assert state becomes success
- `test_deploy_failure` — component exits non-zero; assert state becomes failed with error
- `test_deploy_logs` — logs endpoint returns the captured output lines
- `test_deploy_lock` — two concurrent deploy requests; second returns HTTP 409
- `test_deploy_healthcheck_failure` — healthcheck command exits non-zero; assert state becomes failed
- `test_restart_success` — restart endpoint with docker-type component; verifies correct command invoked

## Excluded

- Claude-generated profile creation (covered by T127)
- Remote / cloud / Kubernetes deployment
- Secrets management or env-var injection
- Automatic deploy triggered after a merge
- Installing missing tools listed in `required_tools`
- WebSocket or server-sent-event streaming of logs (polling is sufficient)
- Per-component healthchecks (only global profile-level healthcheck)
- Persistent deploy history / audit log across multiple runs

## Acceptance criteria

- `POST /projects/{id}/deployer/deploy` runs the component commands from `deploy.yml` and returns `ok=true` on success
- `GET /projects/{id}/deployer/status` returns `state` of `running`, `success`, or `failed` (never stuck at `idle` after a deploy)
- `GET /projects/{id}/deployer/logs` returns non-empty lines after a deploy has run
- A component that exits non-zero causes `state=failed` and the response includes a human-readable error
- A failing healthcheck (command exits non-zero after all retries) causes `state=failed`
- A second `POST /deployer/deploy` while one is already running returns HTTP 409
- `POST /projects/{id}/deployer/restart` issues `docker compose restart {service}` for docker-type components
- The dashboard Deploy/Restart buttons trigger the correct API calls; status badge reflects current state; logs panel displays captured output
- All six new tests pass; existing `test_deployer_routes.py` tests continue to pass
- The existing daemon/runtime ticket workflow is unaffected (no changes to daemon routes or daemon_manager)
