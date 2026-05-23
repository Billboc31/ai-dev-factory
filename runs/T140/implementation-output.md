Implementation complete. Here's a summary of all changes:

---

## Files Modified

### `services/control_api/models/sandbox.py`
Added two new fields to `SandboxState`:
- `supervisor_port: int = 0` — the dedicated port for this sandbox's supervisor
- `sandbox_runtime_root: str = ""` — the isolated runtime root directory

### `services/control_api/services/sandbox_manager.py`
- Added `import signal`
- `create()`: computes `supervisor_port = 8090 + slot` and `sandbox_runtime_root = str(sandbox_dir / "runtime")`, stores both in `SandboxState`
- Added `_terminate_sandbox_supervisor()`: reads `{sandbox_runtime_root}/supervisor.pid`, sends `SIGTERM` to the sandbox supervisor process
- `destroy()`: calls `_terminate_sandbox_supervisor()` before removing files, ensuring cleanup does not touch the main runtime

### `tools/agent_runner/run_sandbox.py`
- `_write_sandbox_env()`: now accepts `supervisor_port` as a parameter and injects `AI_DEV_FACTORY_SUPERVISOR_URL=http://host.docker.internal:{supervisor_port}` and sandbox-specific `AI_DEV_FACTORY_SUPERVISOR_PORT` into `deploy.env`, replacing the previous hardcoded main-supervisor port
- Added `_start_sandbox_supervisor()`: spawns a `uvicorn services.supervisor.main:app` subprocess on `127.0.0.1:{supervisor_port}` with `AI_DEV_FACTORY_RUNTIME_ROOT={sandbox_runtime_root}`, writes PID to `{sandbox_runtime_root}/supervisor.pid`
- Added `_stop_sandbox_supervisor()`: gracefully terminates the sandbox supervisor subprocess with SIGTERM/SIGKILL fallback
- `_do_sandbox()`: computes `supervisor_port = 8090 + slot`, creates the sandbox runtime root directory tree (`state/`, `logs/`, `runs/`), starts the sandbox supervisor, cleans it up in the `finally` block

### `tests/test_sandbox_isolation.py`
Added 4 new tests:
- `test_isolated_runtime_root` — verifies each sandbox has a distinct `sandbox_runtime_root` and state in one is invisible from the other
- `test_isolated_supervisor_port` — verifies `supervisor_port` ≠ 8090 and is unique per sandbox
- `test_concurrent_sandboxes` — 5 sandboxes created concurrently via threads; asserts all ports, runtime roots, and slots are distinct
- `test_cleanup_isolates_main_runtime` — `destroy()` sends SIGTERM to the fake sandbox supervisor PID and leaves the main runtime root untouched

**Result**: 12/12 isolation tests pass, 87/87 sandbox-related tests pass, no regressions in the full suite.
