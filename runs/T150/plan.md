The plan is written to `runs/T150/plan.md`. Here it is:

---

## Objective

Introduce a Traefik-based reverse proxy layer that assigns stable local hostnames (e.g. `sandbox-{id}.ai-dev-factory.localhost`) to each sandbox environment, replacing raw port numbers currently exposed to users. Routes are registered automatically during sandbox startup and removed during cleanup.

## Included

**New files:**
- `deploy/traefik/traefik.yml` — Traefik static config: `web` entrypoint on port 80, file provider pointed at `${RUNTIME_ROOT}/proxy/routes/`, API dashboard enabled.
- `services/control_api/services/proxy_manager.py` — `ProxyManager` class with `register(sandbox_id, ports) -> urls` and `unregister(sandbox_id)`. Writes/removes per-sandbox YAML route files atomically. Web hostname: `sandbox-{id}.ai-dev-factory.localhost`, API hostname: `api.sandbox-{id}.ai-dev-factory.localhost`.
- `services/control_api/tests/test_proxy_manager.py` — unit tests covering file creation, deletion, idempotence, missing-file safety, and hostname uniqueness.

**Modified files:**
- `docker-compose.yml` — add `traefik` service (v3), bind port 80, mount routes dir, add `host.docker.internal` extra_host for Linux.
- `services/control_api/services/sandbox_manager.py` — instantiate `ProxyManager`, call `register` in `start()`, `unregister` in `destroy()`.
- `services/control_api/models/sandbox.py` — add `urls: dict[str, str] = {}` to `SandboxState`.
- `apps/dashboard/src/components/SandboxPanel.jsx` — replace `PortsTable` with clickable `UrlsTable`, fall back to ports when `urls` absent.
- `apps/dashboard/src/components/runtime-dashboard/SandboxRunsTable.jsx` — display URL links when `run.urls` is present.

## Excluded

- HTTPS/TLS (`.localhost` is a secure context in Chrome/Firefox over HTTP; deferred)
- System-wide DNS via dnsmasq or `/etc/resolver` (Chrome/Firefox resolve `*.localhost` natively)
- Traefik Docker-label integration on per-sandbox compose projects
- `deploy.yml` public endpoint declarations
- Auth/access control, cloud DNS, production ingress, network-level sandbox isolation

## Acceptance criteria

- `docker compose up` starts Traefik; dashboard reachable at `http://traefik.ai-dev-factory.localhost`
- After sandbox start, `${RUNTIME_ROOT}/proxy/routes/{id}.yml` exists with valid Traefik routes
- `GET /sandboxes/{id}` returns `urls: {"web": "http://sandbox-{id}.ai-dev-factory.localhost", "api": "http://api.sandbox-{id}.ai-dev-factory.localhost"}`
- Chrome/Firefox routes both hostnames to correct services, returning HTTP 200
- Two concurrent sandboxes have distinct route files and independent hostnames
- After `destroy()`, route file is removed; Traefik returns 404 for that hostname
- Dashboard shows clickable links (no raw ports when `urls` present)
- All `test_proxy_manager.py` tests pass
