I have all the information needed. Here is the plan.

---

## Objective

Add `runtime_root` and `force_source_refresh` fields to `EnvironmentProvisionRequest` in the supervisor so the control API's override is no longer silently dropped by Pydantic, causing `_resolve_runtime_root` to always fall back to `"auto"`.

## Included

- **`services/supervisor/main.py` — `EnvironmentProvisionRequest` model (lines 1250-1260)**
  Add two missing fields:
  ```python
  runtime_root: str | None = None
  force_source_refresh: bool = False
  ```

- **`services/supervisor/main.py` — `environments_provision` endpoint (lines 1271-1298)**
  Add input validation for `runtime_root` before delegating to `provision_environment_from_body`: reject non-absolute paths and paths containing `..` (return HTTP 422). Mirrors the safety guard already present in `_resolve_runtime_root` but fails fast at the API boundary.

- **`services/supervisor/main.py` — startup / provision logging**
  Log the received `EnvironmentProvisionRequest` fields at INFO level at the top of `environments_provision`, including `runtime_root` (masked to `None` or `"<set>"` to keep logs clean). This matches the diagnostic ask in the ticket.

- **`tests/test_environment_supervisor.py`**
  Add one test: POST `/environments/provision` with `runtime_root` set to a valid absolute tmp path, assert the value is forwarded to `deploy_operational_runtime` via `state.runtime_root` (or captured in the mock call args). No external process invocation needed — same mocking pattern as existing tests.

## Excluded

- Changes to `environment_provision.py`, `sandbox_runtime_deploy.py`, or `SandboxState` model — these already handle `runtime_root` correctly once it arrives.
- Changes to the control API `CreateEnvironmentRequest` — it already sends `runtime_root`.
- Restart/process lifecycle tooling — verifying the running supervisor picks up new code is an operational step, not a code change.
- `force_source_refresh` behavior changes — the field must be declared so it passes through; its downstream handling is already implemented.

## Acceptance criteria

- `EnvironmentProvisionRequest` in `services/supervisor/main.py` declares `runtime_root: str | None = None` and `force_source_refresh: bool = False`.
- POST `/environments/provision` with `"runtime_root": "/some/abs/path"` results in `state.runtime_root == "/some/abs/path"` (verified by the new test).
- POST `/environments/provision` with `"runtime_root": "relative/path"` returns HTTP 422.
- The new test passes with `pytest tests/test_environment_supervisor.py`.
- Deploy logs show `runtime_root_source=override` when an override is provided (verified manually or by an integration test inspecting the log line in `sandbox_runtime_deploy.py:393`).
