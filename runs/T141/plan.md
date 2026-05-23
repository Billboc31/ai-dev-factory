## Objective

Extend the sandbox system so that each sandbox represents a complete, generically-declared runtime environment — with all required components started, health-tracked, and shut down safely — and expose the resulting state through enriched lifecycle endpoints and a richer dashboard.

## Included

### 1. Generic runtime topology model — new file
`services/control_api/models/runtime_topology.py`
- `ComponentType(Enum)`: `compose_service`, `supervisor`, `daemon`, `worker`, `database`, `redis`, `custom`
- `ComponentHealth(Enum)`: `unknown`, `healthy`, `degraded`, `stopped`, `error`
- `RuntimeComponent`, `RuntimeTopology` Pydantic models

### 2. Sandbox profile format — new convention
`ai/sandbox-profile.yml.example` — example with all component types.  
Loaded from `{project_root}/ai/sandbox-profile.yml` at sandbox startup; falls back to a default profile (compose services + supervisor) if absent or unparseable.

### 3. Enriched `SandboxState`
- `services/control_api/models/sandbox.py`: add `topology`, `urls`, `uptime_seconds`
- `services/control_api/models/schemas.py`: enrich `SandboxRunSummary` / `SandboxValidationStatus` with topology, urls, runtime_root, allocated_ports, uptime_seconds

### 4. Profile loading and component startup — `run_sandbox.py`
- `_load_sandbox_profile()` with safe fallback
- `_start_components()` dispatching by type (compose → already done; daemon/worker → supervisor daemon API; database/redis → compose verify; custom → daemon)
- `_check_component_health()` with HTTP probe + PID liveness check
- `_poll_topology_health()` called after initial healthcheck and every 30 s; writes topology to state files

### 5. Enhanced stop sequence — `run_sandbox.py`
Ordered shutdown: compose down → daemon/worker PIDs (SIGTERM+SIGKILL) → supervisor SIGTERM → port release → lock/pid file cleanup under `{sandbox_runtime_root}/`

### 6. Cleanup with artifact preservation — `sandbox_manager.py`
- `destroy(sandbox_id, preserve_logs=False)` — copies `run.log` + `state.json` to `sandboxes/preserved/{id}/` before deletion when flag is set
- `restart(sandbox_id)` — stop then start
- `refresh_state(sandbox_id)` — reads state.json from disk without side effects

### 7. New lifecycle endpoints — `routes/sandbox.py`
- `POST /sandboxes/{id}/restart`
- `POST /sandboxes/{id}/refresh`
- `DELETE /sandboxes/{id}?preserve_logs=false`

### 8. Dashboard enrichment — `routes/runtime_dashboard.py`
Return topology, urls, runtime_root, allocated_ports, uptime_seconds in both list and detail endpoints.

### 9. Tests
- `tests/test_sandbox_lifecycle.py` (new): restart, refresh, destroy with preservation, stop sequence
- `tests/test_runtime_topology.py` (new): profile loading (valid, missing, invalid, default fallback), component health check

## Excluded

- Distributed orchestration, Kubernetes, cloud/production deployment
- AI auto-healing loops (T138)
- Automatic component restart driven by health-check failures
- Frontend/UI changes (dashboard consumes the enriched API)
- Changes to the main (non-sandbox) supervisor
- Component dependency DAG (components start sequentially in declaration order)
- Modifications to `docker-compose.yml` itself

## Acceptance criteria

- `GET /runtime-dashboard/sandbox-runs` returns `topology`, `urls`, `allocated_ports`, `runtime_root`, `uptime_seconds` per sandbox
- `POST /sandboxes/{id}/restart` produces running → stopped → running state transitions
- `POST /sandboxes/{id}/refresh` returns current state without side effects
- `DELETE /sandboxes/{id}?preserve_logs=true` leaves `run.log` + `state.json` under `sandboxes/preserved/{id}/`
- A sandbox with a `sandbox-profile.yml` declaring a daemon shows that component in topology with correct health
- A sandbox without a profile behaves identically to today
- On stop: compose down, daemon PIDs terminated, port slot released, no stale locks/PIDs under `{sandbox_runtime_root}/`
- Two sandboxes run concurrently without port conflict or registry corruption
- `pytest tests/test_sandbox_lifecycle.py tests/test_runtime_topology.py` passes

The plan has been saved to `runs/T141/plan.md`.
