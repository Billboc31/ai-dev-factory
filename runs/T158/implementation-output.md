All 40 tests pass. Here's a summary of what was verified and fixed:

---

## Implementation Summary — T158

All backend and frontend work was already complete from previous coder attempts. This session verified the implementation and fixed 2 failing tests.

### Files verified (no changes needed)
- `services/control_api/models/sandbox.py` — enums + `web_host`/`api_host` on `SandboxState`
- `services/control_api/routes/environments.py` — full CRUD endpoints + DNS-safe host validation + collision check (updated to use `mgr._proxy.routes_dir`)
- `services/control_api/services/sandbox_manager.py` — `create()` accepts and stores custom hosts; `proxy_routes_dir` param added
- `services/control_api/services/proxy_manager.py` — `register()` and `build_sandbox_urls()` accept `web_host`/`api_host` overrides
- `services/control_api/main.py` — `environments.router` already registered
- `apps/dashboard/src/api/environments.js` — complete
- `apps/dashboard/src/components/CreateEnvironmentModal.jsx` — `web_host`/`api_host` fields, auto-generation from env_name slug, per-field validation errors, URL preview
- `apps/dashboard/src/components/EnvironmentCard.jsx` — pretty URLs as primary links, collapsible debug section for raw ports

### Test fix
`tests/test_environment_routes.py` — added `monkeypatch.setenv("HOST_RUNTIME_ROOT", ...)` to `test_create_environment_with_custom_hosts` and `test_create_environment_host_collision` to prevent cross-run pollution from the system's real proxy routes directory. The linter also updated the collision check to use `mgr._proxy.routes_dir` for full isolation.

**Result: 40/40 tests pass.**
