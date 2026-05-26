Implementation complete. Here's a summary of every change:

---

## Files modified

**`services/control_api/models/sandbox.py`**
- Added `supervisor_pid: int | None = None` field to `SandboxState`

**`services/control_api/services/sandbox_manager.py`**
- `create()`: `.env` file now also writes `AI_DEV_FACTORY_SUPERVISOR_URL` (pointing to `host.docker.internal:{supervisor_port}`) and `AI_DEV_FACTORY_RUNTIME_ROOT` (the sandbox-scoped runtime dir), so any daemon started via the sandbox API uses the isolated root
- New `_start_sandbox_supervisor()`: spawns a uvicorn supervisor subprocess bound to `127.0.0.1:{supervisor_port}` with `AI_DEV_FACTORY_RUNTIME_ROOT` set to the sandbox runtime root; writes `supervisor.pid`; returns the PID (or `None` on failure)
- `start()`: calls `_start_sandbox_supervisor()` and stores the returned PID in `state.supervisor_pid`
- `_terminate_sandbox_supervisor()`: now checks `state.supervisor_pid` first (preferred), then falls back to reading the PID file — ensuring reliable termination whether the PID comes from state or the filesystem
- `stop()`: clears `supervisor_pid` in the state update to reflect the stopped supervisor

**`deploy/start_supervisor.sh`**
- Parses optional `--port` and `--runtime-root` CLI arguments (after sourcing `.env`), so the same script drives both the main supervisor and per-sandbox supervisors

## Files created

**`tests/test_sandbox_daemon_isolation.py`** — 5 new tests:
1. `test_isolated_daemon_startup`: verifies `Popen` is called with the sandbox's port and that `supervisor_pid` is stored in state
2. `test_isolated_daemon_shutdown`: verifies `os.kill` targets only the sandbox supervisor and that `supervisor_pid` is cleared; main daemon PID file untouched
3. `test_concurrent_sandbox_daemons`: two sandboxes get distinct supervisor processes, ports, runtime roots, and PIDs
4. `test_sandbox_runtime_root_isolation`: `.env` contains the sandbox's own supervisor URL and runtime root; second sandbox gets a separate root
5. `test_cleanup_safety`: `destroy()` SIGTERMs the sandbox supervisor and removes its directory without touching a co-running main daemon PID file
