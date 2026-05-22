All 23 tests pass. Here's the implementation summary:

---

## Files created

| File | Role |
|---|---|
| `services/control_api/models/sandbox.py` | `SandboxState` model + `SandboxStatus` enum |
| `services/control_api/services/sandbox_manager.py` | `SandboxManager` — file-backed, thread-safe port registry, full lifecycle |
| `services/control_api/routes/sandbox.py` | 8 REST endpoints under `/sandboxes` |
| `apps/dashboard/src/api/sandbox.js` | Axios client for all sandbox endpoints |
| `apps/dashboard/src/components/SandboxPanel.jsx` | Dashboard panel: list, create form, start/stop/destroy, log modal |
| `tests/test_sandbox_manager.py` | 13 unit tests (subprocess mocked) |
| `tests/test_sandbox_routes.py` | 10 integration tests (TestClient) |

## Files modified

| File | Change |
|---|---|
| `services/control_api/main.py` | `import sandbox` + `app.include_router(sandbox.router)` |
| `apps/dashboard/src/App.jsx` | `SandboxPanel` import, nav link, `/sandboxes` route |
| `deploy/bootstrap.sh` | `mkdir -p $RUNTIME_ROOT/sandboxes` |

## Key design decisions

- **Port isolation**: slot 0 reserved for main runtime (3000/8080); sandboxes get slot ≥ 1 → ports 3100/8180, 3200/8280, etc. Registry in `sandboxes/port-registry.json`.
- **Compose isolation**: each sandbox gets `COMPOSE_PROJECT_NAME=sandbox-{id}` via a dedicated `.env` file, preventing cross-project container conflicts.
- **Thread safety**: module-level `threading.Lock` guards port registry reads/writes.
- **No Docker required in tests**: all `subprocess.run` calls are patched via `unittest.mock`.
