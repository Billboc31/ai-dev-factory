Now I have a thorough understanding of the architecture. Let me produce the plan.

---

## Objective

Make sandbox deployments fully runtime-isolated by giving each sandbox its own runtime root directory and its own supervisor process on a dedicated port, so sandbox UIs and APIs no longer share state with the main runtime.

## Included

### Model changes
- **`services/control_api/models/sandbox.py`**
  - Add `supervisor_port: int` field to `SandboxState`
  - Add `sandbox_runtime_root: str` field to `SandboxState`

### Port/slot allocation
- **`services/control_api/services/sandbox_manager.py`**
  - In `_allocate_slot()`: compute `supervisor_port = 8090 + slot` (slot 0 = main supervisor, slot ≥ 1 = sandbox supervisors) and store in `SandboxState`
  - Set `sandbox_runtime_root = f"{RUNTIME_ROOT}/sandboxes/{sandbox_id}/runtime"` in `SandboxState` at creation time
  - Update `destroy()`: read `{sandbox_runtime_root}/supervisor.pid`, send `SIGTERM` to the sandbox supervisor process, then proceed with existing compose-down / worktree-remove / directory-rmtree sequence
  - `destroy()` must not touch the main runtime root files

### Worker changes
- **`tools/agent_runner/run_sandbox.py`**
  - Receive `supervisor_port` and `sandbox_runtime_root` from the start request payload (passed through supervisor `/sandbox/start`)
  - Create the sandbox runtime root directory tree (`state/`, `logs/`, `runs/`) before launching compose
  - Launch a second `uvicorn services.supervisor.main:app` subprocess bound to `127.0.0.1:{supervisor_port}` with `AI_DEV_FACTORY_RUNTIME_ROOT={sandbox_runtime_root}` and the same `HOST_*` / `CONTAINER_*` path-mapping env vars as the main supervisor
  - Write the supervisor subprocess PID to `{sandbox_runtime_root}/supervisor.pid`
  - Inject into the sandbox `deploy.env`:
    - `AI_DEV_FACTORY_SUPERVISOR_URL=http://host.docker.internal:{supervisor_port}`
    - `AI_DEV_FACTORY_SUPERVISOR_PORT={supervisor_port}`
    - `AI_DEV_FACTORY_RUNTIME_ROOT={sandbox_runtime_root}` (container-side override kept as `/runtime`, but host mapping updated in env)
  - On worker exit (normal, timeout, or exception): terminate the sandbox supervisor subprocess before returning

### Supervisor passthrough
- **`services/control_api/services/sandbox_runner.py`**
  - Include `supervisor_port` and `sandbox_runtime_root` in the JSON body sent to the main supervisor's `POST /sandbox/start` endpoint

- **`services/supervisor/main.py`**
  - In the `/sandbox/start` handler: extract `supervisor_port` and `sandbox_runtime_root` from the request body and forward them as env vars or CLI args to the `run_sandbox.py` subprocess

### Tests
- **`tests/test_sandbox_isolation.py`** — extend with:
  - `test_isolated_runtime_root`: verify each sandbox gets a distinct `sandbox_runtime_root`, confirm state written in one does not appear in the other
  - `test_isolated_supervisor_port`: verify `supervisor_port` values differ across slots and do not collide with main supervisor port 8090
  - `test_concurrent_sandboxes`: allocate two sandbox slots simultaneously, assert distinct ports and distinct runtime roots, assert slot registry integrity
  - `test_cleanup_isolates_main_runtime`: call `destroy()`, assert supervisor.pid process is gone, assert main runtime root and main supervisor are unaffected
  - All tests use `tmp_path` fixtures and mock subprocess; no real Docker or live network

## Excluded

- AI auto-fix loops (separate ticket)
- Cloud or production deployment
- Distributed runtime federation
- Changes to the main supervisor startup script (`deploy/start_supervisor.sh`)
- UI/frontend changes beyond what is driven by the existing dashboard already reading the correct API URL
- Migrating existing running sandboxes to the new scheme
- Supervisor health-check or restart-on-crash logic

## Acceptance criteria

- A sandbox's web UI displays only the state files under that sandbox's `sandbox_runtime_root`, not entries from the main runtime root
- `SandboxState` for any active sandbox contains a non-zero `supervisor_port` different from `8090` and a `sandbox_runtime_root` path distinct from `AI_DEV_FACTORY_RUNTIME_ROOT`
- Two sandboxes running concurrently have distinct `supervisor_port` values, distinct `sandbox_runtime_root` paths, and distinct API/web port pairs; no port collisions
- After `SandboxManager.destroy(sandbox_id)`, the process with PID from `{sandbox_runtime_root}/supervisor.pid` is no longer running, the `sandbox_runtime_root` directory no longer exists, and the main supervisor (`localhost:8090`) remains healthy
- `pytest tests/test_sandbox_isolation.py` passes for all four new test cases
- No existing test suite regresses (`pytest tests/` green)
