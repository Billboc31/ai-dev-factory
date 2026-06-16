All 14 tests pass (13 pre-existing + 1 new).

**Summary of changes:**

- `services/control_api/services/project_bootstrap.py`: Added `runtime_base_root_not_writable` → `ValueError` mapping before the generic `RuntimeError` fallthrough. This ensures the control_api routes' `ValueError` handler catches it and returns 422 instead of 500.
- `tests/test_project_bootstrap.py`: Added `test_bootstrap_raises_value_error_on_not_writable_runtime_base` to verify the new branch raises `ValueError` with the correct message.
