All 12 tests pass and the diff looks clean. Here's a summary of what was implemented:

---

**Files created:**

- `deploy/traefik/traefik.yml` — Traefik v3 static config: `web` entrypoint on port 80, file provider watching `/routes`, API dashboard enabled
- `services/control_api/services/proxy_manager.py` — `ProxyManager` class with `register(sandbox_id, ports) → urls` (writes per-sandbox YAML route atomically) and `unregister(sandbox_id)` (removes route file); seeds `_dashboard.yml` for `traefik.ai-dev-factory.localhost` on first init
- `tests/test_proxy_manager.py` — 12 unit tests covering file creation, deletion, idempotence, missing-file safety, hostname uniqueness, concurrent sandboxes, dashboard seeding

**Files modified:**

- `docker-compose.yml` — adds `traefik` service (v3.0), binds port 80, mounts `traefik.yml` and the runtime proxy routes dir, adds `host.docker.internal:host-gateway` for Linux
- `services/control_api/models/sandbox.py` — adds `urls: dict[str, str] = {}` to `SandboxState`
- `services/control_api/services/sandbox_manager.py` — instantiates `ProxyManager` in `__init__`, calls `register` in `start()` on success, `unregister` in `destroy()`
- `apps/dashboard/src/components/SandboxPanel.jsx` — adds `UrlsTable` with clickable links; `SandboxRow` uses it when `urls` is present, falls back to `PortsTable`
- `apps/dashboard/src/components/runtime-dashboard/SandboxRunsTable.jsx` — "Ports" column renamed "Access"; shows clickable URL links when `run.urls` is present, falls back to raw port string
