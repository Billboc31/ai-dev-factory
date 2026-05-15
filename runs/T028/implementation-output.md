Implementation complete. Here's the summary:

---

## Changes

### Files created

**`services/control_api/`** — new FastAPI REST backend

| File | Role |
|------|------|
| `main.py` | FastAPI app factory, request logging middleware, CLI entrypoint |
| `models/schemas.py` | Pydantic models: `TicketSummary`, `DaemonStatus`, `ActionResult`, etc. |
| `services/artifact_reader.py` | Read-only access to `runs/` — never writes |
| `services/subprocess_runner.py` | Validated subprocess calls to `run_ticket.py` / `run_issue_intake.py` |
| `services/daemon_manager.py` | Start/stop daemon via PID file at `runs/daemon.pid` + SIGTERM |
| `routes/health.py` | `GET /health` |
| `routes/daemon.py` | `GET /daemon/status`, `POST /daemon/start|stop|restart` |
| `routes/tickets.py` | All ticket read + workflow + git action endpoints |
| `routes/issues.py` | `POST /issues/intake`, `GET /issues/intake/status` |
| `routes/providers.py` | `GET /providers/status`, `GET /projects` |
| `requirements.txt` | fastapi, uvicorn, pydantic, httpx, pytest |

**`services/__init__.py`** — makes `services` a Python package

**Tests (3 files)**

| File | Coverage |
|------|----------|
| `tests/test_control_api_endpoints.py` | 15 tests — health, daemon status, ticket CRUD, plan/logs/artifacts, providers |
| `tests/test_control_api_subprocess.py` | 11 tests — ticket_id validation, ok/fail mapping, OSError, no state.json mutation, daemon lifecycle |
| `tests/test_control_api_artifacts.py` | 18 tests — validate, list, get, logs, artifacts, plan/review/tests, no-write invariant |

### Results

- **44 new tests pass**
- **237 existing tests unchanged**
- No workflow logic duplicated — all actions delegate to `run_ticket.py` or `run_daemon.py`
- `state.json` is never written by the API layer
