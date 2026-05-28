All 66 tests pass. Here's a summary of what was implemented:

## Files modified

**Backend:**
- `services/control_api/models/sandbox.py` — Added `EnvironmentType`, `RefType`, `EnvironmentMode` enums; extended `SandboxState` with `env_name`, `env_type`, `ref`, `ref_type`, `deployment_mode`, `web_host`, `api_host`, `deployed_at`, `stopped_at`
- `services/control_api/services/proxy_manager.py` — Updated `build_sandbox_urls()` and `register()` to accept optional `web_host`/`api_host` overrides; custom hosts are used verbatim in Traefik YAML rules
- `services/control_api/services/sandbox_manager.py` — `create()` now accepts and stores all env fields; `start()` passes custom hosts to proxy and sets `deployed_at`; `stop()` sets `stopped_at`
- `services/control_api/routes/environments.py` — Added `web_host`/`api_host` to `CreateEnvironmentRequest`; added DNS-safe format validation, reserved-host rejection, and collision detection against existing route files (422 with field-prefixed error message)
- `services/control_api/main.py` — Registered `environments.router`

**Frontend:**
- `apps/dashboard/src/components/CreateEnvironmentModal.jsx` — Added Web Host and API Host fields with auto-generation from `env_name` slug; manual override tracking; inline field-level error display; URL preview section
- `apps/dashboard/src/components/EnvironmentCard.jsx` — URLs rendered as primary "Open Web ↗" / "Open API ↗" buttons with copy; raw ports hidden behind a collapsible "Debug" toggle

**Tests:**
- `tests/test_proxy_manager.py` — 5 new tests for custom host overrides
- `tests/test_environment_routes.py` — 5 new tests covering custom hosts, invalid format, reserved host, host collision, and bare `localhost` rejection
