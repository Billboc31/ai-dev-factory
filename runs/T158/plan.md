Now I have a solid picture of the codebase. Producing the plan.

---

## Objective

Introduce named environments with user-configurable Traefik `web_host`/`api_host` URLs: extend the sandbox model with environment metadata, wire the existing `/environments` router, add host validation, update `ProxyManager` to accept custom hostnames, and update the Create Environment modal with host fields and auto-generation.

## Included

### Backend — `services/control_api/models/sandbox.py`

- Add enums: `EnvironmentType` (main | develop | integration | preview | sandbox | feature | custom), `RefType` (branch | tag | commit | pr_ref), `EnvironmentMode` (persistent | deploy_and_test)
- Extend `SandboxState` with optional fields: `env_name: str | None`, `env_type: EnvironmentType | None`, `ref: str | None`, `ref_type: RefType | None`, `deployment_mode: EnvironmentMode | None`, `web_host: str | None`, `api_host: str | None`

### Backend — `services/control_api/routes/environments.py`

- Extend `CreateEnvironmentRequest` (or equivalent Pydantic schema) with `web_host: str | None` and `api_host: str | None` fields
- Add host validation before sandbox creation:
  - DNS-safe check (regex: labels are alphanumeric + hyphens, no leading/trailing hyphens, dot-separated)
  - Collision check: scan existing `proxy/routes/*.yml` files to extract declared `Host(...)` rules; reject if requested host already appears
  - Reserved host rejection: block `traefik.*`, `_*`-prefixed labels, bare `localhost`
  - Return explicit 422 with user-readable message on any validation failure
- Pass validated `web_host`/`api_host` + env fields through to `SandboxManager.create()`

### Backend — `services/control_api/services/sandbox_manager.py`

- Update `create()` signature to accept `env_name`, `env_type`, `ref`, `ref_type`, `deployment_mode`, `web_host`, `api_host`
- Store all new fields in `SandboxState` before persisting

### Backend — `services/control_api/services/proxy_manager.py`

- Update `register()` (and `build_sandbox_urls()`) to accept optional `web_host`/`api_host` overrides
- If overrides are provided, use them directly in the Traefik YAML `Host(...)` rule and in the returned `urls` dict; otherwise fall back to current `sandbox-{id}.*` pattern
- Update `unregister()` / `destroy()` to remove the route file regardless of whether the host was custom or auto-generated (no change needed if deletion is by sandbox_id file path — confirm)

### Backend — `services/control_api/main.py`

- Register the environments router: `app.include_router(environments.router)`

### Frontend — `apps/dashboard/src/components/CreateEnvironmentModal.jsx`

- Add `web_host` and `api_host` text fields to the create form
- Auto-generate initial values from `env_name` slug (e.g. `"Demo Client"` → `demo-client.ai-dev-factory.localhost`); allow manual override
- Show live validation error messages returned by the API (host collision, invalid format) beneath each field
- Display preview of final `http://{web_host}` and `http://{api_host}` URLs before submit

### Frontend — `apps/dashboard/src/components/EnvironmentCard.jsx`

- Confirm that Web URL and API URL from `env.urls.web` / `env.urls.api` are rendered as primary clickable elements (already partially done — verify and fix if ports are surfaced instead)
- Port fallback section must be collapsed/hidden by default; only expand in a debug toggle

### Frontend — `apps/dashboard/src/api/environments.js`

- No structural changes expected; confirm `createEnvironment` payload forwards `web_host` and `api_host`

## Excluded

- No project-ID-based URL path (`/projects/{id}/environments`); existing `/environments` flat pattern is retained to match current router and frontend client
- No SQLite migration; JSON file-based persistence is kept unchanged
- No SSL/TLS certificate automation
- No wildcard DNS management
- No environment cloning
- No auto-scaling or convergence loop changes
- No Deployer tab changes
- No multi-user access control
- No Kubernetes or cloud deployment support
- No changes to the Traefik infrastructure lifecycle (TraefikManager / InfraServiceManager)

## Acceptance criteria

- `POST /environments` with `web_host`/`api_host` creates a sandbox whose Traefik route file uses the provided hostnames verbatim
- `GET /environments` returns environments with `urls.web` and `urls.api` reflecting the custom hosts
- Submitting a `web_host` already present in any existing `proxy/routes/*.yml` returns HTTP 422 with a descriptive message
- Submitting a DNS-unsafe hostname (e.g. `"my host!.localhost"`) returns HTTP 422
- Submitting a reserved host (e.g. `"traefik.ai-dev-factory.localhost"`) returns HTTP 422
- The Create Environment modal auto-generates host fields from `env_name` and allows override
- Validation errors (collision, format) appear inline below the affected field
- Final URLs are previewed before submit
- Environment cards show `http://{web_host}` and `http://{api_host}` as primary links; raw port numbers are hidden by default
- Stop and Delete actions clean up the Traefik route file for the environment
- The Deployer tab remains fully functional and unchanged
