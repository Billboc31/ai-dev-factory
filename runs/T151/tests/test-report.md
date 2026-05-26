---

## Test Report — T151: FAIL

All 7 integration tests fail. The implementation is structurally incomplete.

### Root causes (all blocking)

1. **`sandbox.py` not updated** — The three enums (`EnvironmentType`, `EnvironmentMode`, `RefType`) are absent. Importing the environments router raises `ImportError`.

2. **`SandboxState` missing fields** — `env_name`, `env_type`, `ref`, `ref_type`, `deployment_mode`, `deployed_at`, `stopped_at` are all absent from the model.

3. **`SandboxManager.create()` not extended** — Called with 5 new kwargs that don't exist in the signature → `TypeError`.

4. **`SandboxManager.start()`/`stop()` not updated** — Neither stamps `deployed_at` / `stopped_at`.

5. **Router not registered** — `environments.router` is missing from `main.py`. Every `/environments` call returns 404.

### False positive note

Running the tests without `--cache-clear` after the full suite showed "7 passed" — a pytest module cache artifact where other tests had already imported control-api modules into the process. With `--cache-clear` (or running the file in isolation): **7 failed**.

### What is complete

The frontend is correctly implemented and wired (`EnvironmentsPage`, `EnvironmentCard`, `CreateEnvironmentModal`, `environments.js` API client, App.jsx routes). The route file design is sound. No regressions to existing tests.

### Required fixes

The coder needs to update `sandbox.py` (add enums + model fields), extend `SandboxManager` (create/start/stop), and register the router in `main.py`. Report saved to `runs/T151/tests/test-report.md`.
