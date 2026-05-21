I have enough context. Here is the implementation plan.

---

## Objective

Introduce a minimal host-side supervisor HTTP service so the Docker control API can delegate daemon start/stop/status operations to the host instead of attempting to spawn the daemon inside the container. V1 covers the daemon lifecycle only — no generic job registry, no deployer support.

## Included

**New file — `services/supervisor/__init__.py`**
Empty package marker.

**New file — `services/supervisor/main.py`**
Minimal FastAPI app (default port 8090, localhost-only bind). Four endpoints:
- `GET /health` — returns `{"status": "ok", "daemon_pid": <int|null>}`.
- `GET /daemon/status` — reads `runs/daemon.pid`, checks liveness via `os.kill(pid, 0)`, returns `{"running": bool, "pid": int|null, "started_at": str|null}`.
- `POST /daemon/start` — refuses if already running; spawns `run_daemon.py` via `subprocess.Popen` using the host venv resolved from `AI_DEV_FACTORY_PROJECT_ROOT`; writes PID file only on successful spawn; returns `{"ok": bool, "pid": int}`.
- `POST /daemon/stop` — sends `SIGTERM` to the recorded PID; removes PID file; returns `{"ok": bool}`.

Respects `AI_DEV_FACTORY_PROJECT_ROOT` and `AI_DEV_FACTORY_RUNTIME_ROOT` for path resolution (same conventions as `runtime_resolver.py`). Does not implement auth — localhost trust only.

**New file — `deploy/start_supervisor.sh`**
Convenience shell script: activates host venv, exports env vars, launches `uvicorn services.supervisor.main:app --host 127.0.0.1 --port 8090`. Used for manual start and referenced in dashboard error messages.

**Modified — `services/control_api/services/daemon_manager.py`**
Add a supervisor delegation path (new functions `_supervisor_url()`, `_call_supervisor()`):
- `_supervisor_url()` reads `AI_DEV_FACTORY_SUPERVISOR_URL` env var; returns `None` when unset.
- At the top of `start()`, `stop()`, and `status()` entry points: if supervisor URL is set, delegate via `httpx` (already a likely dependency, or add it) with a short timeout (2 s); on `httpx.ConnectError` or timeout, return a structured `ActionResult` with `ok=False`, `error="supervisor_unreachable"`, and the manual `host_command` field populated.
- Existing `AI_DEV_FACTORY_HOST_DAEMON_COMMAND` path is kept unchanged as independent fallback.

**Modified — `services/control_api/models/schemas.py`**
Add optional fields to `DaemonStatus`:
- `supervisor_available: bool | None = None`
- `supervisor_url: str | None = None`

**Modified — `services/control_api/routes/daemon.py`**
Populate `supervisor_available` and `supervisor_url` in the `/daemon/status` response by pinging `GET /health` on the configured supervisor URL (or marking `None` when unconfigured).

**Modified — `docker-compose.yml`**
Add commented-out `AI_DEV_FACTORY_SUPERVISOR_URL=http://host.docker.internal:8090` env var with an explanatory comment directing operators to start `deploy/start_supervisor.sh` on the host first.

**New file — `tests/supervisor/test_supervisor.py`**
Minimal pytest tests using `httpx.AsyncClient` + `ASGITransport`:
- `test_health_ok` — GET /health returns 200 and `status == "ok"`.
- `test_daemon_status_not_running` — GET /daemon/status returns `{"running": false}` when no PID file.
- `test_start_delegates_to_supervisor` — mock `_supervisor_url()` to return a test URL, mock `httpx.AsyncClient.post`, assert `daemon_manager.start()` calls the supervisor endpoint and does not call `subprocess.Popen`.
- `test_supervisor_unreachable_returns_structured_error` — mock `httpx` to raise `ConnectError`, assert `ActionResult.error == "supervisor_unreachable"` and `host_command` is populated.

## Excluded

- Deployer jobs, mapper daemon, guardian daemon (future tickets).
- Generic job registry / filesystem job persistence.
- Dependency auto-install (gh, claude, git assumed present on host).
- Remote host support over SSH.
- Authentication on the supervisor endpoint.
- Dashboard frontend changes beyond what the existing status response surface already provides.
- Rewriting `run_daemon.py` or any daemon internals.

## Acceptance criteria

- `GET http://localhost:8090/health` returns 200 with `{"status": "ok"}` when the supervisor is running on the host.
- `POST /daemon/start` via the control API (with `AI_DEV_FACTORY_SUPERVISOR_URL` set) spawns the daemon on the host; `run_daemon.py` has access to `gh`, `claude`, `git`, and the canonical runtime root.
- `POST /daemon/stop` via the control API stops the host-side daemon and removes the PID file.
- `GET /daemon/status` via the control API includes `supervisor_available: true` when reachable, `false` when not.
- When the supervisor is unreachable, the control API returns `ok: false`, `error: "supervisor_unreachable"`, and a populated `host_command` string — no PID file is written.
- Existing manual daemon launch (`python tools/agent_runner/run_daemon.py ...`) continues to work unchanged.
- Existing `AI_DEV_FACTORY_HOST_DAEMON_COMMAND` delegation path continues to work unchanged.
- All four new pytest tests pass.
- No call to `subprocess.Popen` for the daemon occurs inside the Docker control API when `AI_DEV_FACTORY_SUPERVISOR_URL` is set.
