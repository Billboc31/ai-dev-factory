All 11 tests pass (6 new + 5 existing). Here's a summary of what was implemented:

**Files created:**
- `services/control_api/services/deployer_runner.py` — per-project threading lock, deploy/restart execution via `subprocess.run`, state persistence in `deploy-state.json`, log appending, stale-PID detection, healthcheck with retries

**Files modified:**
- `services/control_api/models/schemas.py` — added `DeployHealthcheck`, `DeployState`, `DeployLogsResponse`; extended `DeployerStatus` with `started_at/finished_at/error/last_step`; added `healthcheck` field to `DeployProfile`
- `services/control_api/routes/deployer.py` — updated status endpoint to read real state; added `POST /deployer/deploy`, `POST /deployer/restart` (both return HTTP 409 when locked), `GET /deployer/logs`
- `apps/dashboard/src/api/deployer.js` — added `triggerDeploy`, `triggerRestart`, `getDeployLogs`
- `apps/dashboard/src/components/ActionButton.jsx` — added `disabled` prop support
- `apps/dashboard/src/pages/DeployerPage.jsx` — added Deploy/Restart buttons (disabled while running), colored state badge with spinner, error line, collapsible logs panel with auto-refresh while running, polling stops on success/failed

**Tests created:**
- `tests/test_deployer_execution.py` — 6 tests covering success, failure, logs, lock (409), healthcheck failure, and restart with docker component
