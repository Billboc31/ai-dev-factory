All 23 tests pass. Here is the structured review.

---

## Review — T161: Fix Environments create flow to provision real sandbox runtime

### Ticket compliance

| Requirement | Status | Notes |
|---|---|---|
| `SandboxManager.create()` called | ✅ | Line 110–120 of `environments.py` |
| Real sandbox directory created | ✅ | `sandbox_dir.mkdir()` in `create()`, confirmed by `test_create_environment_creates_real_sandbox_dir` |
| `state.json` written | ✅ | `_write_state(state)` in `create()`; confirmed by `test_create_environment_creates_state_json` |
| `.env` written | ✅ | `env_file.write_text()` in `create()`; confirmed by `test_create_environment_creates_env_file` |
| Runtime directories initialised | ✅ | `_start_sandbox_supervisor()` creates `runtime/state`, `runtime/logs`, `runtime/runs` |
| Failed provisioning → HTTP 500 | ✅ | Lines 122–128; confirmed by `test_failed_provisioning_returns_500` |
| Failed provisioning → no environment card | ✅ | `_destroy_silently()` → `mgr.destroy()`; confirmed by `test_failed_provisioning_no_environment_card` |
| Failed provisioning → sandbox dir removed | ✅ | `shutil.rmtree()` in `destroy()`; confirmed by `test_failed_provisioning_sandbox_dir_removed` |
| Real sandbox id in response | ✅ | 12-char UUID hex from `SandboxManager.create()`; confirmed by `test_create_environment_sandbox_id_from_manager` |
| Actions work post-create | ✅ | Confirmed by `test_environment_actions_work_after_create` |

### Plan compliance

The implementation matches the plan precisely:
- `_destroy_silently()` helper added at line 59 — readable, logs on failure.
- Post-create block: exception path → destroy + 500; silent error path (`status == error`) → destroy + 500; happy path returns only when `status == running`.
- Exactly 8 new tests added, matching the plan's table one-for-one.
- Only two files modified (`routes/environments.py`, `tests/test_environment_routes.py`), per plan scope.

### Code quality

**`environments.py`:**
- `_destroy_silently()` is clean and correctly scoped — catches any exception, logs with sandbox_id and error, no re-raise. The right tool for a best-effort cleanup call. ✅
- The two-branch failure check (exception vs `status == error`) correctly handles the silent failure mode documented in the plan (docker compose `up` returning rc ≠ 0 sets status without raising). ✅
- No scope creep — no other routes or methods touched. ✅

**`tests/test_environment_routes.py`:**
- `_fail_compose_up()` is correctly designed: rc=1 only for commands containing `"up"`, rc=0 for everything else (including `"down"` called during `destroy()`). Without this asymmetry, cleanup in `_destroy_silently` would also fail. ✅
- Tests are isolated with `tmp_path`, deterministic, no inter-test dependencies. ✅
- The regex `r"[0-9a-f]{12}"` in `test_create_environment_sandbox_id_from_manager` accurately captures the UUID-hex ID contract. ✅

### Observations (non-blocking)

1. **`subprocess.Popen` not mocked in tests**: `_start_sandbox_supervisor()` uses `Popen` which is outside the `subprocess.run` mock scope. In practice uvicorn attempts to launch but the process is non-blocking (`start_new_session=True`) and `OSError` is caught. This was pre-existing behaviour before T161 and all 15 original tests still pass, so no regression. Worth noting as a pre-existing test isolation gap, not introduced here.

2. **HTTP 201 response even when `started.status` is neither `running` nor `error`**: The implementation returns `started` for any status that is not `SandboxStatus.error` and does not raise. In practice `start()` only ever returns `running` or `error`, so this is safe. This is an implicit contract assumption, not a defect.

### Verdict

Implementation is correct, scoped exactly to the plan, all 23 tests pass, and no fake runtime states can survive provisioning failures. No blocking issues.

IMPLEMENTATION_APPROVED
