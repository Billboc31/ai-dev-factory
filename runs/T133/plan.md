Now I have a thorough picture of the architecture. Let me write the plan.

## Objective

Add an isolated sandbox deployment runtime so the deployer can spin up per-ticket Docker Compose environments that are fully isolated from the main runtime and from each other — with independent project names, port allocations, env files, logs, and lifecycle management.

## Included

### New files

**`services/control_api/models/sandbox.py`**
- Pydantic models: `SandboxState` (id, ticket_id, project_root, compose_project, ports dict, env_file path, status enum, created_at), `SandboxStatus` enum (`creating`, `running`, `stopped`, `error`, `destroyed`)

**`services/control_api/services/sandbox_manager.py`**
- `SandboxManager` class backed by `$RUNTIME_ROOT/sandboxes/`
- `create(ticket_id, project_root) → SandboxState` — allocates port slot, writes isolated env file (`sandboxes/{id}/.env`), writes `state.json`, registers sandbox
- `start(sandbox_id)` — runs `docker compose -p {compose_project} --env-file {sandbox_env} up -d` from the project root
- `stop(sandbox_id)` — runs `docker compose -p {compose_project} down`
- `destroy(sandbox_id)` — stops + removes `sandboxes/{id}/` dir + releases port slot
- `status(sandbox_id) → SandboxState` — reads `state.json`, optionally queries `docker compose ps` for live container state
- `logs(sandbox_id, component=None) → str` — reads from `sandboxes/{id}/logs/` or captures `docker compose -p {compose_project} logs`
- `list() → list[SandboxState]` — scans `sandboxes/` for all `state.json` files
- `cleanup_old(max_age_days=7)` — destroys sandboxes older than threshold
- Port registry: `sandboxes/port-registry.json` maps sandbox_id → port slot; slots are integer offsets from a base (e.g. web: `3000 + slot*100`, api: `8080 + slot*100`), slot 0 reserved for main runtime; allocates lowest free slot, releases on destroy

**`services/control_api/routes/sandbox.py`**
- `POST /sandboxes` — create sandbox (body: `ticket_id`, `project_root`)
- `GET /sandboxes` — list all sandboxes
- `GET /sandboxes/{sandbox_id}` — get status
- `POST /sandboxes/{sandbox_id}/start` — start sandbox
- `POST /sandboxes/{sandbox_id}/stop` — stop sandbox
- `DELETE /sandboxes/{sandbox_id}` — destroy sandbox
- `GET /sandboxes/{sandbox_id}/logs` — fetch logs (optional `?component=api`)
- `POST /sandboxes/cleanup` — trigger cleanup of old sandboxes

**`apps/dashboard/src/api/sandbox.js`**
- Thin fetch wrappers for all sandbox API endpoints, mirroring the style of `apps/dashboard/src/api/deployer.js`

**`apps/dashboard/src/components/SandboxPanel.jsx`**
- Panel listing all sandboxes with status badge, port table, created-at timestamp
- Action buttons: Start, Stop, Destroy per sandbox
- "Create sandbox" form (ticket_id input)
- Log viewer modal (calls `/sandboxes/{id}/logs`)
- Polling refresh (same pattern as existing dashboard components)

**`tests/test_sandbox_manager.py`**
- Unit tests (no Docker required, subprocess calls are mocked):
  - `test_create_allocates_unique_ports` — two sandboxes get different port slots
  - `test_create_does_not_conflict_with_main_runtime` — slot 0 is never assigned
  - `test_port_registry_released_on_destroy` — slot available again after destroy
  - `test_state_written_on_create` — `state.json` exists and parses correctly
  - `test_lifecycle_transitions` — status changes through creating/running/stopped/destroyed
  - `test_cleanup_old_removes_stale_sandboxes` — sandboxes beyond max_age_days are destroyed

**`tests/test_sandbox_routes.py`**
- Integration tests against FastAPI TestClient:
  - `test_create_sandbox_returns_201`
  - `test_list_sandboxes_empty_and_populated`
  - `test_get_sandbox_status`
  - `test_start_stop_destroy_sequence`
  - `test_destroy_releases_port`
  - `test_logs_endpoint_returns_text`

### Modified files

**`services/control_api/main.py`**
- Register `sandbox.router` with prefix `/sandboxes`

**`apps/dashboard/src/App.jsx`** (or the top-level layout component)
- Import and render `<SandboxPanel />` alongside existing panels

**`deploy/bootstrap.sh`**
- Create `$RUNTIME_ROOT/sandboxes/` during runtime root initialization

## Excluded

- AI fix loop or automated remediation on sandbox failures
- Tester agent integration
- Production or remote deployment targets
- Kubernetes or container orchestration beyond Docker Compose
- Per-sandbox custom Dockerfiles or image builds
- Multi-user access control for sandbox operations
- Sandbox-to-sandbox networking

## Acceptance criteria

- `POST /sandboxes` creates a directory at `$RUNTIME_ROOT/sandboxes/{sandbox_id}/` containing a valid `state.json` and a `.env` file with port values distinct from the main runtime (3000, 8080) and from other active sandboxes.
- `docker compose -p sandbox-{id}` containers start and stop without touching the main compose project.
- `GET /sandboxes/{id}/logs` returns non-empty output after a sandbox has been started.
- `DELETE /sandboxes/{id}` removes the sandbox directory, releases the port slot (verified by creating a new sandbox and observing it reuses the freed slot), and runs `docker compose down` for the compose project.
- `POST /sandboxes/cleanup` with `max_age_days=0` destroys all sandboxes; no sandbox directory remains under `$RUNTIME_ROOT/sandboxes/`.
- The main runtime (`docker-compose.yml`, ports 3000/8080) continues to function while a sandbox is running.
- The dashboard Sandboxes panel renders all live sandboxes with correct status, ports, and functional Start/Stop/Destroy buttons.
- All tests in `tests/test_sandbox_manager.py` and `tests/test_sandbox_routes.py` pass under `pytest`.
