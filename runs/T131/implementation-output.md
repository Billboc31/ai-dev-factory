Both fixes applied and verified. Here's what changed:

**Files modified:**

- **`docker-compose.yml`** — Removed the extra leading space on line 24 before `- AI_DEV_FACTORY_SUPERVISOR_URL=...`. YAML now parses correctly and the env var is picked up by the container.

- **`services/control_api/models/schemas.py`** — Added `DaemonStartRequest` model with `restart_policy: str = "no-restart"`.

- **`services/control_api/services/daemon_manager.py`** — Added `restart_policy: str = "no-restart"` to `start()` and `restart()`. The supervisor call now passes `{"exec_cmd": exec_cmd, "restart_policy": restart_policy}`.

- **`services/control_api/routes/daemon.py`** — Updated all four start/restart endpoints (default and project-scoped) to accept an optional `DaemonStartRequest` body and forward `restart_policy` to the manager.

The `restart_policy` flows fully: dashboard → `POST /daemon/start` → `daemon_manager.start()` → `_call_supervisor(...)` → supervisor `POST /daemon/start`.
