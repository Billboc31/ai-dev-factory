Implementation complete. Here's the summary:

---

## Changes made

**New files:**

| File | Purpose |
|---|---|
| `services/supervisor/__init__.py` | Package marker |
| `services/supervisor/main.py` | FastAPI supervisor app — `GET /health`, `GET /daemon/status`, `POST /daemon/start`, `POST /daemon/stop` |
| `deploy/start_supervisor.sh` | Host launch script — activates venv, exports env vars, starts uvicorn on `127.0.0.1:8090` |
| `tests/supervisor/__init__.py` | Test package marker |
| `tests/supervisor/test_supervisor.py` | 4 tests (all pass) |

**Modified files:**

| File | Change |
|---|---|
| `services/control_api/models/schemas.py` | Added `supervisor_available`, `supervisor_url` to `DaemonStatus`; added `error` to `ActionResult` |
| `services/control_api/services/daemon_manager.py` | Added `_supervisor_url()`, `_supervisor_start_command()`, `_call_supervisor()`; modified `get_status()`, `start()`, `stop()` with supervisor delegation as path 0 |
| `services/control_api/routes/daemon.py` | Added `_enrich_with_supervisor()` helper; status endpoints now populate supervisor fields |
| `docker-compose.yml` | Added commented-out `AI_DEV_FACTORY_SUPERVISOR_URL` with instructions |

**Behavior:** When `AI_DEV_FACTORY_SUPERVISOR_URL` is not set, all existing paths are unchanged. When set, `start()`/`stop()` delegate to the supervisor; on `ConnectError`, `start()` returns `error="supervisor_unreachable"` with a `host_command` pointing to `deploy/start_supervisor.sh`. All 37 relevant existing tests still pass.
