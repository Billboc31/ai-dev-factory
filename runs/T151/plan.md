The plan has been written to `runs/T151/plan.md`. Here's a summary of the key design decisions:

**Core correction from the review**: No second orchestration pipeline. The previous plan introduced `EnvironmentManager`, `run_environment.py`, new supervisor routes, and a second port registry — all rejected. The revised plan eliminates all of that.

**What the revised plan does instead**:

1. **`models/sandbox.py`** — adds `EnvironmentMode` + `EnvironmentType` enums and extends `SandboxState` with 7 optional fields (`env_name`, `env_type`, `env_mode`, `ref`, `ref_type`, `deployed_at`, `stopped_at`). Existing sandboxes deserialize fine with `None` defaults.

2. **`sandbox_manager.py`** — minimal extension: `create()` accepts the new env fields, `start()` stamps `deployed_at`, `stop()` stamps `stopped_at`. Core orchestration untouched.

3. **`routes/environments.py`** — new thin-wrapper routes (`/environments/*`) that delegate entirely to the existing `SandboxManager`. No new state machine, no new worker, no new registry.

4. **Frontend** — new `EnvironmentsPage`, `EnvironmentCard`, `CreateEnvironmentModal`, `environments.js` API client, and nav wiring in `App.jsx` + `ProjectSidebar.jsx`.

5. **Tests** — 7 integration tests in `tests/test_environment_routes.py` using the existing test harness.
