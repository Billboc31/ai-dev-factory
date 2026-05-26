Everything looks correct. Here's a summary of what was implemented:

---

## Implementation complete

**Files modified:**

- `services/control_api/models/sandbox.py` — Added 3 enums (`EnvironmentType`, `EnvironmentMode`, `RefType`) and 7 optional fields to `SandboxState` (all `None` by default for backward-compatibility)
- `services/control_api/services/sandbox_manager.py` — Extended `create()` with optional env kwargs; `start()` now stamps `deployed_at`; `stop()` now stamps `stopped_at`
- `services/control_api/main.py` — Imports and registers the new environments router
- `apps/dashboard/src/App.jsx` — Added `EnvironmentsPage` import, `/environments` route, and "Environments" nav link

**Files created:**

- `services/control_api/routes/environments.py` — 8 REST endpoints (`POST`, `GET`, `GET/{id}`, `POST/{id}/redeploy`, `POST/{id}/stop`, `DELETE/{id}`, `POST/{id}/refresh`, `GET/{id}/logs`), all delegating to `SandboxManager`
- `apps/dashboard/src/api/environments.js` — 8 axios client functions mirroring the routes
- `apps/dashboard/src/pages/EnvironmentsPage.jsx` — Polling grid page with "New Environment" button
- `apps/dashboard/src/components/EnvironmentCard.jsx` — Card with status/type badges, URL links, timestamps, action buttons, and inline log viewer
- `apps/dashboard/src/components/CreateEnvironmentModal.jsx` — Form for env_name, ref, ref_type, env_type, deployment_mode, project_root
- `tests/test_environment_routes.py` — 7 tests, all green

**Test results:** 7/7 new tests pass; 38/38 existing sandbox tests pass (no regressions).
