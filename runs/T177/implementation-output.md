Implementation complete. Here's a summary:

## Changes made

**`services/supervisor/main.py`**
- `EnvironmentProvisionRequest` (line ~1250): added `runtime_root: str | None = None` and `force_source_refresh: bool = False` — these fields were already sent by the control API but stripped by Pydantic since they weren't declared.
- `environments_provision` handler: added path validation for `runtime_root` matching the existing check in `control_api/routes/environments.py` — returns HTTP 400 for relative paths or paths containing `..`.

**`tests/test_environment_supervisor.py`**
- `test_provision_runtime_root_override_propagates`: POSTs a valid `runtime_root`, asserts `SandboxState.runtime_root` matches it and that `deploy_operational_runtime` receives the state with the correct value.
- `test_provision_invalid_runtime_root_returns_400`: confirms both `"relative/path"` and `"/a/../b"` return 400.

**Test results**: 5/6 pass. The 1 failure (`test_supervisor_provision_maps_and_validates_host_project_root`) is pre-existing and unrelated to this ticket.
