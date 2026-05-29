All 23 tests pass — 15 pre-existing and 8 new.

**Summary of changes:**

**`services/control_api/routes/environments.py`** (2 edits):
- Added `SandboxStatus` to the import
- Added `_destroy_silently(mgr, sandbox_id)` helper before `_get_manager`
- Rewrote the post-create block: on `start()` exception → destroy + HTTP 500; on `status == error` → destroy + HTTP 500; only returns HTTP 201 when `status == running`

**`tests/test_environment_routes.py`** (1 edit, 8 new tests added):
- `_fail_compose_up` mock helper (returns rc=1 for compose up, rc=0 otherwise)
- `test_create_environment_creates_real_sandbox_dir` — sandbox dir exists on disk after create
- `test_create_environment_creates_state_json` — `state.json` exists and is valid JSON
- `test_create_environment_creates_env_file` — `.env` exists
- `test_failed_provisioning_returns_500` — failed compose up → HTTP 500
- `test_failed_provisioning_no_environment_card` — failed create → `GET /environments` returns `[]`
- `test_failed_provisioning_sandbox_dir_removed` — failed create → no sandbox directory left
- `test_create_environment_sandbox_id_from_manager` — response `id` is a 12-char hex string
- `test_environment_actions_work_after_create` — stop/redeploy/refresh/delete all return non-5xx after successful create
