All clean. Here's a summary of all files created or modified:

---

## Changes made

### Created
- `apps/dashboard/src/components/SandboxRunsPanel.jsx` — new component listing all historical sandbox runs with Logs/Cleanup per row

### Modified

| File | What changed |
|---|---|
| `tools/agent_runner/run_sandbox.py` | Added `fcntl` import; `_allocate_port_slot`, `_release_port_slot`, `_write_sandbox_env` helpers; `_run_scripts` now accepts `extra_env`; `_do_sandbox` allocates ports, writes `deploy.env`, enriches state with `ports`/`worktree_path`/`compose_project`, and releases the slot in `finally` |
| `docker-compose.yml` | Port mappings now `${API_PORT:-8080}:8080` and `${WEB_PORT:-3000}:80` |
| `services/control_api/models/schemas.py` | Added `ports`, `worktree_path`, `compose_project` to both `SandboxValidationState` and `SandboxValidationStatus` |
| `services/control_api/services/sandbox_runner.py` | `_state_from_payload` now extracts and passes `ports`, `worktree_path`, `compose_project` |
| `services/control_api/routes/sandbox.py` | `get_project_sandbox_status` passes new fields; added `runs_router` with `GET /sandbox-runs`, `GET /sandbox-runs/{id}/logs`, `DELETE /sandbox-runs/{id}` |
| `services/control_api/main.py` | Mounts `sandbox.runs_router` |
| `apps/dashboard/src/api/deployer.js` | Added `listSandboxRuns`, `getSandboxRunLogs`, `cleanupSandboxRun` |
| `apps/dashboard/src/pages/DeployerPage.jsx` | `SandboxStatusPanel` shows ports, worktree path and Refresh button; imports and renders `<SandboxRunsPanel />` |
