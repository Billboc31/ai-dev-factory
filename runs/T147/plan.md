Now I have enough context to write the implementation plan.

## Objective

Isolate sandbox daemon instances from the main runtime by launching a per-sandbox supervisor and daemon process that uses only the sandbox's runtime root, communicates only with its own supervisor port, and is started/stopped automatically by the sandbox API — eliminating the need for manual host commands.

## Included

**`services/control_api/services/sandbox_manager.py`**
- On sandbox start: launch a host-side supervisor subprocess bound to the sandbox's already-allocated `supervisor_port` (currently `8090 + slot`) with `AI_DEV_FACTORY_RUNTIME_ROOT` set to a sandbox-scoped subdirectory (e.g. `{runtime_root}/sandboxes/{sandbox_id}/runtime/`)
- Store the supervisor PID in sandbox state (`sandboxes/{id}/state.json`)
- On sandbox stop/destroy: SIGTERM the sandbox supervisor (which propagates to the sandbox daemon via existing supervisor stop logic), then clean up the supervisor PID entry
- Ensure `_destroy_sandbox` calls the stop path before removing sandbox files

**`sandboxes/{id}/.env` generation in `sandbox_manager.py`**
- Add `AI_DEV_FACTORY_SUPERVISOR_URL=http://host.docker.internal:{supervisor_port}` so the sandbox's control-api routes daemon calls through the per-sandbox supervisor
- Add `AI_DEV_FACTORY_RUNTIME_ROOT={sandbox_runtime_root}` so the sandbox daemon uses an isolated runtime root

**`deploy/start_supervisor.sh`**
- Accept optional `--port` and `--runtime-root` arguments so it can be called for both the main supervisor and per-sandbox supervisors

**`services/control_api/models/sandbox.py`**
- Add `supervisor_pid: Optional[int]` field to `SandboxState`

**`tests/test_sandbox_daemon_isolation.py`** (new file)
- `test_isolated_daemon_startup`: verify sandbox supervisor starts on the correct port with the sandbox runtime root
- `test_isolated_daemon_shutdown`: verify sandbox supervisor/daemon stops without touching the main daemon
- `test_concurrent_sandbox_daemons`: verify two sandboxes each get their own supervisor on distinct ports and separate runtime roots
- `test_sandbox_runtime_root_isolation`: verify daemon state files (pid, log, workers.json) land in the sandbox runtime root, not the main one
- `test_cleanup_safety`: verify destroying a sandbox stops its daemon and does not affect a running main daemon

## Excluded

- AI auto-fix loops
- Cloud deployment or remote supervisor support
- Network isolation between sandbox daemons
- CPU/memory resource limits for sandbox processes
- Modifying the daemon polling logic (`run_daemon.py`) — only the supervisor launch and env wiring change
- Changing how sandbox ports are allocated (the `slot`-based `port-registry.json` mechanism is already correct)

## Acceptance criteria

- `POST /sandboxes/{id}/start` results in a supervisor process running at `8090 + slot` with `AI_DEV_FACTORY_RUNTIME_ROOT` pointing to the sandbox-specific runtime directory; no manual host command is needed
- `POST /daemon/start` from the sandbox's control-api starts a daemon using only the sandbox runtime root (verified by checking pid/log files land in `sandboxes/{id}/runtime/runs/`)
- Two concurrently running sandboxes each have distinct supervisor ports and distinct runtime roots with no file overlap
- `POST /sandboxes/{id}/destroy` stops the sandbox daemon and supervisor; the main daemon's `runs/daemon.pid` is unchanged
- All five new tests in `test_sandbox_daemon_isolation.py` pass
- `sandbox_manager.py` contains no references to the main supervisor URL or main runtime root
