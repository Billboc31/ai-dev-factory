Now I have everything needed to write the plan.

## Objective

Introduce the minimal deployer foundation for V1: a deploy profile format (`.ai-dev-factory/deploy.yml`), a project scanner service, two read-only API endpoints (`/status`, `/scan`), and a minimal dashboard `DeployerPage`. No deployment execution, no subprocess orchestration, no JSONL logs.

## Included

### Deploy profile format
- Create `.ai-dev-factory/deploy.yml` at the repository root with the following fields: `version`, `project`, `required_tools` (list of strings), `components` (list with `name`, `type` (`docker`|`host`), and either `service` or `command` sub-field). The ai-dev-factory profile declares: `api` (docker, service `api`), `web` (docker, service `web`), `daemon` (host, command `python services/daemon/main.py`), required tools `gh`, `git`, `docker`, `claude`.

### Backend — new schemas (`services/control_api/models/schemas.py`)
- `DeployComponent` — `name: str`, `type: Literal["docker", "host"]`, `service: str | None`, `command: str | None`.
- `DeployProfile` — `version: int`, `project: str`, `required_tools: list[str]`, `components: list[DeployComponent]`.
- `ScanResult` — `docker_services: list[str]`, `python_backend: bool`, `node_frontend: bool`, `required_tools: list[str]`, `deploy_profile: DeployProfile | None` (populated if `deploy.yml` is present and valid).
- `DeployerStatus` — `state: Literal["idle"]`, `profile_present: bool`, `project_id: str`.

### Backend — project scanner service (`services/control_api/services/project_scanner.py`)
- `scan_project(project_root: Path) -> ScanResult`:
  - Detect docker-compose services: parse `docker-compose.yml` or `docker-compose.yaml` top-level `services` keys if present.
  - Detect Python backend: check for `requirements.txt` or `pyproject.toml`.
  - Detect Node frontend: check for `package.json`.
  - Detect required tools: probe `shutil.which()` for `gh`, `git`, `docker`, `claude`; include those present in the result list.
  - Load and parse `.ai-dev-factory/deploy.yml` if present; populate `deploy_profile`; set `deploy_profile = None` if missing or malformed (no exception raised to caller).

### Backend — deployer router (`services/control_api/routes/deployer.py`)
- `project_router = APIRouter(prefix="/projects/{project_id}/deployer", tags=["deployer"])`.
- `GET /status` → `DeployerStatus`: resolve project via `resolve_project` dependency; return `{ state: "idle", profile_present: bool, project_id }` (profile present if `.ai-dev-factory/deploy.yml` exists in the project root).
- `POST /scan` → `ScanResult`: resolve project root; call `scan_project(root)`; return result.

### Backend — router registration (`services/control_api/main.py`)
- Import `deployer` from routes; add `app.include_router(deployer.project_router)` alongside the existing project-scoped routers.

### Frontend — API client (`apps/dashboard/src/api/deployer.js`)
- `getDeployerStatus(projectId)` → `GET /api/projects/{projectId}/deployer/status`.
- `scanProject(projectId)` → `POST /api/projects/{projectId}/deployer/scan`.
- Both use the existing `_pfx()` / axios pattern.

### Frontend — DeployerPage (`apps/dashboard/src/pages/DeployerPage.jsx`)
- State: `status` (from `getDeployerStatus`), `scanResult` (from `scanProject`), `scanning` boolean.
- `usePolling(refreshStatus, 5000)` to update status badge automatically.
- Display: status badge (`idle` text + `profile_present` indicator), `ActionButton` "Scan Project" (disabled while `scanning`), below the button show `scanResult` if present — list `docker_services`, `required_tools`, `python_backend`/`node_frontend` flags.

### Frontend — route and nav registration
- `apps/dashboard/src/App.jsx`: add `<Route path="/deployer" element={<DeployerPage />} />` inside the existing `<Routes>` block; import `DeployerPage`.
- `apps/dashboard/src/components/ProjectSidebar.jsx`: add "Deployer" as a `NavLink` (path `/deployer`) in the same style as existing nav links.

### Tests
- `tests/test_project_scanner.py` — unit tests using `tmp_path` fixtures:
  - Docker-compose detection: write a minimal `docker-compose.yml`; assert `docker_services` lists expected service names.
  - Python backend detection: write `requirements.txt`; assert `python_backend` is `True`.
  - Node frontend detection: write `package.json`; assert `node_frontend` is `True`.
  - Tool detection: monkeypatch `shutil.which` to control availability; assert `required_tools` list.
  - Deploy profile loading: write a valid `.ai-dev-factory/deploy.yml`; assert `deploy_profile` is populated with correct fields.
  - Missing profile: no `.ai-dev-factory/deploy.yml`; assert `deploy_profile` is `None`.
- `tests/test_deployer_routes.py` — FastAPI `TestClient` integration tests:
  - `GET /projects/{id}/deployer/status` on a known project → `200` with `{ state: "idle", project_id: ... }`.
  - `GET /projects/{id}/deployer/status` with an unknown project → `404`.
  - `POST /projects/{id}/deployer/scan` on a project with a `docker-compose.yml` → `200` with `docker_services` populated.

## Excluded

- Deploy execution, restart execution, subprocess orchestration of any kind.
- Claude-assisted profile generation.
- Deployment logs (JSONL or otherwise).
- Concurrent deployment locking.
- Branch deployment (the `deploy` and `restart` endpoints are not created in V1).
- Healthcheck execution.
- Host process management.
- Any change to the daemon state machine or existing ticket workflows.
- New SQLite tables (no persistence beyond the filesystem `deploy.yml`).
- Dashboard build tooling changes.

## Acceptance criteria

- `.ai-dev-factory/deploy.yml` exists at the repository root, declares components `api` (docker), `web` (docker), `daemon` (host), and required tools `gh`, `git`, `docker`, `claude`.
- `GET /projects/{id}/deployer/status` returns `{ "state": "idle", "profile_present": true, "project_id": "..." }` for ai-dev-factory.
- `GET /projects/{id}/deployer/status` returns `404` for an unknown project ID.
- `POST /projects/{id}/deployer/scan` returns a `ScanResult` that lists at least the docker services from `docker-compose.yml` for ai-dev-factory.
- Dashboard route `/deployer` renders without error; the "Scan Project" button is visible; clicking it calls the scan endpoint and displays the returned components.
- Status badge updates automatically via the 5 s polling loop without a page reload.
- A "Deployer" nav link appears in `ProjectSidebar`.
- `pytest tests/test_project_scanner.py tests/test_deployer_routes.py` passes.
- No existing test suite regressions (`pytest tests/` passes overall).
