36/36 passing. The implementation is complete. Here's a summary of what was already done before this session and confirmed working:

**Files modified/created:**

- `services/control_api/models/sandbox.py` — `supervisor_pid: int | None = None` field added to `SandboxState`
- `services/control_api/services/sandbox_manager.py`:
  - `create()` — `.env` now includes `AI_DEV_FACTORY_SUPERVISOR_URL` (per-sandbox port) and `AI_DEV_FACTORY_RUNTIME_ROOT` (per-sandbox runtime root)
  - `_start_sandbox_supervisor()` — new method: spawns a uvicorn supervisor subprocess with the sandbox-scoped port and runtime root, writes `supervisor.pid` into the sandbox runtime root, returns the PID
  - `start()` — calls `_start_sandbox_supervisor()` and stores the PID in state
  - `stop()` — clears `supervisor_pid` in state after terminating
  - `_terminate_sandbox_supervisor()` — uses `state.supervisor_pid` as fallback when the PID file is missing
- `deploy/start_supervisor.sh` — accepts `--port` and `--runtime-root` CLI overrides (already done)
- `tests/test_sandbox_daemon_isolation.py` — 5 new tests covering all acceptance criteria
