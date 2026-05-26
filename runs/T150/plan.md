Now I have enough context to write the plan. Here it is:

---

## Objective

Introduce a Traefik-based reverse proxy layer that assigns stable local hostnames (e.g. `sandbox-{id}.ai-dev-factory.localhost`) to each sandbox environment, replacing the raw port numbers currently exposed to users. Routes are registered automatically during sandbox startup and removed during cleanup.

## Included

**`docker-compose.yml`**
- Add a `traefik` service (Traefik v3, official image).
- Bind Traefik to host port 80 (HTTP entrypoint named `web`).
- Mount `${RUNTIME_ROOT}/proxy/routes/` as a Traefik file provider (watched directory).
- Add `extra_hosts: ["host.docker.internal:host-gateway"]` to the Traefik service for Linux compatibility (macOS already resolves this natively).
- Expose the Traefik dashboard at `traefik.ai-dev-factory.localhost` for diagnostics.

**`deploy/traefik/traefik.yml`** (new static config)
- Declare the `web` entrypoint on port 80.
- Enable the file provider pointing to `/routes/` (container-side mount of `${RUNTIME_ROOT}/proxy/routes/`).
- Enable Traefik API/dashboard (insecure, local only).

**`services/control_api/services/proxy_manager.py`** (new)
- Class `ProxyManager` with:
  - `__init__(routes_dir: Path)` — directory watched by Traefik file provider.
  - `register(sandbox_id: str, ports: dict[str, int]) -> dict[str, str]` — writes a Traefik YAML route file for the sandbox; returns the URL map.
  - `unregister(sandbox_id: str)` — deletes the route file.
- Route file per sandbox: `{routes_dir}/{sandbox_id}.yml`.
- Web hostname: `sandbox-{sandbox_id}.ai-dev-factory.localhost` → `host.docker.internal:{web_port}`.
- API hostname: `api.sandbox-{sandbox_id}.ai-dev-factory.localhost` → `host.docker.internal:{api_port}`.
- Route file is written atomically (write to `.tmp` then rename) to avoid partial reads by Traefik.

**`services/control_api/services/sandbox_manager.py`**
- Instantiate `ProxyManager` in `SandboxManager.__init__` with `routes_dir` derived from runtime root env var.
- In `start()`: call `proxy_manager.register(sandbox_id, ports)` after the sandbox is running; persist returned URLs into `state.json`.
- In `destroy()`: call `proxy_manager.unregister(sandbox_id)` before the worktree is removed.
- In `stop()`: leave routes in place (sandbox is stopped, not destroyed; routes can remain stale but harmless).

**`services/control_api/models/sandbox.py`**
- Add `urls: dict[str, str] = {}` field to `SandboxState` (maps `"web"` / `"api"` to their local hostnames).

**`apps/dashboard/src/components/SandboxPanel.jsx`**
- Replace the raw `PortsTable` component with a `UrlsTable` component that renders each URL as a clickable `<a>` link (opens in a new tab).
- Fall back to raw port display when `urls` is absent (backwards-compatible with sandboxes started before T150).

**`apps/dashboard/src/components/runtime-dashboard/SandboxRunsTable.jsx`**
- Replace the `portsStr` display with URL links when `run.urls` is present; keep the existing port fallback.

**Tests**
- `tests/unit/services/test_proxy_manager.py`:
  - `register()` creates the expected YAML file with correct Traefik router/service config.
  - `unregister()` removes the file.
  - `register()` is idempotent (calling twice with different ports overwrites the file).
  - `unregister()` on a non-existent sandbox does not raise.
  - Hostname collision: two sandboxes with different IDs produce distinct route files and distinct hostnames.

## Excluded

- Internet or public exposure of sandbox services.
- HTTPS / TLS termination (`.localhost` domains are treated as secure contexts by Chrome and Firefox over plain HTTP; HTTPS support is a follow-up).
- Safari / system-wide DNS resolution (requires dnsmasq or `/etc/resolver/localhost`; out of scope for this ticket).
- Modifying sandbox Docker Compose projects with Traefik labels (Traefik's file provider, routing to host-exposed ports, makes this unnecessary).
- `deploy.yml` integration for declared public endpoints (follow-up).
- Authentication or access control on proxy routes.
- Cloud DNS or production ingress.
- Sandbox isolation at the network level (sandboxes already expose ports to the host; this ticket only adds a hostname alias layer on top).

## Acceptance criteria

- `docker compose up` starts a `traefik` container alongside `api` and `web`; Traefik dashboard is reachable at `http://traefik.ai-dev-factory.localhost`.
- After a sandbox is started, `${RUNTIME_ROOT}/proxy/routes/{sandbox_id}.yml` exists and contains a valid Traefik file-provider route targeting the sandbox's host ports.
- `GET /sandboxes/{id}` returns a `SandboxState` with `urls` populated: `{"web": "http://sandbox-{id}.ai-dev-factory.localhost", "api": "http://api.sandbox-{id}.ai-dev-factory.localhost"}`.
- In Chrome or Firefox (no extra DNS config), `http://sandbox-{id}.ai-dev-factory.localhost` proxies to the sandbox web service and returns HTTP 200.
- `http://api.sandbox-{id}.ai-dev-factory.localhost` proxies to the sandbox API service and returns HTTP 200.
- Two concurrently running sandboxes each have distinct route files and distinct hostnames; each URL resolves independently.
- After `destroy()`, the sandbox route file is removed and Traefik stops routing to that hostname (subsequent requests return 404).
- Dashboard `SandboxPanel` renders web and API entries as clickable links; raw port numbers are no longer displayed when `urls` is present.
- All unit tests in `test_proxy_manager.py` pass.
