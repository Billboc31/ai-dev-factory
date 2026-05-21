Implementation complete. Here's a summary of everything created/modified:

---

## Files Created

| File | Purpose |
|---|---|
| `.ai-dev-factory/deploy.yml` | Deploy profile for ai-dev-factory: `api` (docker), `web` (docker), `daemon` (host), tools `gh git docker claude` |
| `services/control_api/services/project_scanner.py` | `scan_project()` — detects docker services, python/node stacks, host tools, loads deploy profile |
| `services/control_api/routes/deployer.py` | `GET /projects/{id}/deployer/status`, `POST /projects/{id}/deployer/scan` |
| `apps/dashboard/src/api/deployer.js` | `getDeployerStatus(projectId)`, `scanProject(projectId)` |
| `apps/dashboard/src/pages/DeployerPage.jsx` | Status badge + "Scan Project" button + scan result panel, 5s polling |
| `tests/test_project_scanner.py` | 13 unit tests for the scanner service |
| `tests/test_deployer_routes.py` | 5 integration tests for the API routes |

## Files Modified

| File | Change |
|---|---|
| `services/control_api/models/schemas.py` | Added `DeployComponent`, `DeployProfile`, `ScanResult`, `DeployerStatus` |
| `services/control_api/main.py` | Imported `deployer`, registered `deployer.project_router` |
| `services/control_api/requirements.txt` | Added `pyyaml>=6.0` |
| `apps/dashboard/src/App.jsx` | Added `DeployerPage` import, `/deployer` route, "Deployer" nav link |

## Test results

- **18/18** new tests pass (`test_project_scanner.py` + `test_deployer_routes.py`)
- **0 regressions** — pre-existing 44 failures are unchanged (env isolation issues in unrelated test files)

## Plan note

The plan listed the nav link under `ProjectSidebar.jsx`, but all existing nav links live in the `Nav` component in `App.jsx`. I placed it there to match the established pattern.
