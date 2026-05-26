The plan is written. Here's what it covers:

**Backend (3 files modified/created):**
- `models/sandbox.py` — adds `EnvironmentType`, `EnvironmentMode`, `RefType` enums + 7 optional fields to `SandboxState` (backward-compatible, all default `None`)
- `sandbox_manager.py` — `create()` accepts env metadata, `start()` stamps `deployed_at`, `stop()` stamps `stopped_at`; all else untouched
- `routes/environments.py` (new) — 9 thin-wrapper endpoints delegating entirely to `SandboxManager`
- `main.py` — registers the new router

**Frontend (5 files new, 2 modified):**
- `api/environments.js`, `pages/EnvironmentsPage.jsx`, `components/EnvironmentCard.jsx`, `components/CreateEnvironmentModal.jsx` (new)
- `App.jsx` + `ProjectSidebar.jsx` — nav wiring

**Tests:** 7 integration tests in `tests/test_environment_routes.py` covering branch/persistent environments, concurrency, timestamps, deletion cleanup, and idempotency.

No second orchestration pipeline is introduced — the environment layer is purely metadata + UX on top of the existing `SandboxManager`.
