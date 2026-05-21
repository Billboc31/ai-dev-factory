Plan written to `runs/T128/plan.md`.

Here's a summary of the key architectural decisions:

**Core idea**: Add a new **"Path 1b"** to the existing 3-path daemon strategy in `daemon_manager.py`. When `AI_DEV_FACTORY_SUPERVISOR_URL` is set, all daemon operations (start/stop/status/logs) are delegated to the host supervisor HTTP API instead of refusing or spawning locally.

**New components**:
- `tools/supervisor/main.py` — FastAPI service on `127.0.0.1:8765`, endpoints for start/stop/status/logs per job type
- `tools/supervisor/job_registry.py` — JSON-persisted job state with file locking
- `tools/supervisor/dependency_check.py` — validates git, gh, claude, docker, venv
- `tools/supervisor/start.sh` — host launch script using project venv

**Modified files** (4):
- `daemon_manager.py` — add supervisor client path (Path 1b), no PID-file writes when supervisor owns the job
- `daemon.py` routes — add `GET /daemon/supervisor-status` for dashboard detection
- `docker-compose.yml` — commented `AI_DEV_FACTORY_SUPERVISOR_URL` example
- Dashboard — supervisor unavailability banner + structured failure reason display

**Key risks called out**: `host.docker.internal` on Linux (fixed via `extra_hosts: host-gateway`), port conflict (configurable), and race with manually-launched daemon (supervisor checks existing PID file before spawning).
