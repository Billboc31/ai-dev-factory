I now have a complete understanding of the bug and its fix. Here is the implementation plan:

---

## Objective

Fix `runtime_root` override being silently dropped by the supervisor's `EnvironmentProvisionRequest` model, so the chosen override reaches `deploy_operational_runtime` and deploy logs show "override" instead of "auto".

## Included

**`services/supervisor/main.py` — `EnvironmentProvisionRequest` model (lines 1250–1259)**
- Add `runtime_root: str | None = None`
- Add `force_source_refresh: bool = False`

These two fields are sent by the container API (`body.model_dump(mode="json")`) but currently stripped by Pydantic because the supervisor model doesn't declare them. This is the sole root cause.

**`services/supervisor/main.py` — `environments_provision` handler (after line 1272)**
- Add path validation for `runtime_root` (absolute path, no `..`) matching the validation already present in `control_api/routes/environments.py` lines 105–111.
- Return a 400 `JSONResponse` on invalid input, so invalid values fail validation instead of being silently ignored.

**`tests/test_environment_supervisor.py`**
- Add a test that POSTs to `/environments/provision` with a valid `runtime_root`, patches `deploy_operational_runtime`, and asserts that the `SandboxState` returned has `runtime_root` set to the submitted value.
- Add a test that POSTs with an invalid `runtime_root` (relative path or containing `..`) and asserts a 400 response.

## Excluded

- `CreateEnvironmentModal.jsx` — already sends `runtime_root` correctly.
- `services/control_api/routes/environments.py` — already validates, accepts, and forwards `runtime_root`.
- `services/control_api/services/environment_provision.py` — already stores `runtime_root` in `SandboxState` and passes it to `deploy_operational_runtime`.
- `services/control_api/models/sandbox.py` — `SandboxState.runtime_root` field already exists.
- `services/control_api/services/sandbox_runtime_deploy.py` — `_resolve_runtime_root()` already handles the override correctly.
- No changes to the redeploy flow; it already preserves `runtime_root` from persisted state.
- No UI changes.

## Acceptance criteria

- A POST to `/environments/provision` with `runtime_root: "/some/abs/path"` results in `SandboxState.runtime_root == "/some/abs/path"` in the supervisor response.
- `deploy_operational_runtime` is called with a state where `state.runtime_root` equals the submitted value (verifiable by asserting on the mock call args in the new test).
- A POST to `/environments/provision` with `runtime_root: "relative/path"` or `runtime_root: "/a/../b"` returns HTTP 400 (not 200/ignored).
- `pytest tests/test_environment_supervisor.py` passes with the new tests.
- No existing tests are broken.
