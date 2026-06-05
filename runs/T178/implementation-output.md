Implementation complete. Here's a summary:

**Files modified:**

- **`services/supervisor/main.py`** — `EnvironmentProvisionRequest` (line 1260-1261): added `runtime_root: str | None = None` and `force_source_refresh: bool = False`. `environments_provision` endpoint: added INFO-level logging of incoming request fields and fast-path 422 validation for non-absolute or `..`-containing `runtime_root` values.

- **`tests/test_environment_supervisor.py`**: added two new tests:
  - `test_supervisor_provision_forwards_runtime_root` — verifies `runtime_root` flows through to `deploy_operational_runtime` via `state.runtime_root`
  - `test_supervisor_provision_rejects_relative_runtime_root` — verifies relative paths return HTTP 422

**Test results:** 5/6 pass. The one failure (`test_supervisor_provision_maps_and_validates_host_project_root`) is pre-existing — it was already broken before this branch and is caused by a missing sandbox parent directory in that test's setup, unrelated to this fix.

**Root cause fixed:** `EnvironmentProvisionRequest.model_dump()` was silently dropping `runtime_root` and `force_source_refresh` because those fields weren't declared on the model. With the two fields now declared, they pass through correctly to `provision_environment_from_body`, enabling `_resolve_runtime_root` to see `runtime_root_source=override` in logs.
