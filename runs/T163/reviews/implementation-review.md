Now I have a complete picture. Let me write the review.

---

## Review — T163: Persist failed environment deployments

### Summary

The implementation is a minimal, surgical fix that precisely targets the root cause: two `_destroy_quietly()` calls in `provision_environment()` that silently erased failed environments. Both are replaced with `apply_deploy_failure()` + `mgr._write_state()`, mirroring the pattern already used by `redeploy_environment()`. No new abstractions, no scope creep.

---

### Acceptance criteria review

| Criterion | Status | Notes |
|---|---|---|
| Failed environments remain visible | ✅ | `status=error`, state written to disk, returned by `GET /environments` |
| Failure reason persisted | ✅ | `lifecycle_error = str(exc)` on exception path; `result.error` on failed-result path |
| Logs remain accessible | ✅ | Sandbox dir preserved; existing logs endpoint unchanged |
| Retry Deploy from failed env | ✅ | `redeploy_environment()` already handles all states; no change needed |
| Delete works on failed env | ✅ | Existing delete already handles error-state; no change needed |
| Failed envs clearly marked | ✅ | `status=error`, `lifecycle_phase=failed`, `urls={}` |
| No fake healthy/running status | ✅ | `urls={}` enforced by `apply_deploy_failure()`; `status=error` |
| Successful deploys unaffected | ✅ | Success path is untouched |

---

### Code correctness

**`provision_environment()` exception path** (lines 172–178):

```python
except Exception as exc:
    failed = apply_deploy_failure(
        state,
        OperationalDeployResult(success=False, error=str(exc)),
    )
    mgr._write_state(failed)
    raise RuntimeError(f"environment provisioning failed: {exc}") from exc
```

`state` here is the nonlocal variable updated by `_persist` callbacks during `deploy_operational_runtime`, so it captures the most-recent intermediate state at the point of exception. `lifecycle_error` is set to the exception message. Consistent with `redeploy_environment()`.

**`provision_environment()` failed-result path** (lines 179–184):

```python
if not result.success:
    failed = apply_deploy_failure(state, result)
    mgr._write_state(failed)
    raise RuntimeError(...)
```

Uses the full `result` object, so `lifecycle_steps`, `last_step`, `healthcheck_status`, `smoke_status` are all preserved. Correct.

**`apply_deploy_failure()` behavior**: Sets `urls={}` (no fake URLs), `status=SandboxStatus.error`, `lifecycle_phase=LifecyclePhase.failed`, preserves all failure context. Already proven by use in `redeploy_environment()`.

---

### Test quality

Three tests correctly updated from asserting destroy-on-failure to asserting persist-on-failure:
- `test_failed_provisioning_persists_environment_card` — verifies `status=error` and 1 environment visible
- `test_failed_provisioning_preserves_sandbox_dir` — verifies sandbox dir survives
- `test_failed_provisioning_preserves_custom_sandbox_path` — verifies custom path and `status=error`

The existing `test_failed_provisioning_returns_500` is unchanged and correctly verifies the 500 response is still returned.

---

### Minor observations (non-blocking)

1. **`_destroy_quietly()` is now dead code.** The helper at line 265 is no longer called from anywhere in the codebase. The plan deliberately retained it "for cleanup edge cases," but it is currently unreachable. This could confuse future readers. Not a blocker since it causes no harm, but worth noting for a follow-up cleanup.

2. **Tests don't assert `lifecycle_error` is non-null.** The new tests check `status=error` but don't verify `lifecycle_error` contains the failure message. Given that `apply_deploy_failure()` is already tested implicitly through `redeploy_environment()` tests, this is a minor coverage gap, not a blocking issue.

3. **Exception path `lifecycle_steps` is `[]`.** When an exception is raised mid-deploy, `OperationalDeployResult(success=False, error=str(exc))` has empty `steps`, so `lifecycle_steps` is written as `[]` even if intermediate steps ran. This matches `redeploy_environment()` behavior and is consistent; partial step info is still accessible via `run.log`/`supervisor.log` on disk.

---

### Risk assessment

- **Regression risk: minimal.** The success path is untouched. The only behavior change is that failure no longer calls `_destroy_quietly()`.
- **Data safety: none.** No existing data is deleted by this change; the opposite is true.
- **Scope: tightly bounded.** 7-line diff in one service file, 3 test renames + assertion updates.

---

### Conclusion

The implementation is correct, minimal, and exactly matches the plan. All 8 acceptance criteria from the ticket are satisfied. The change mirrors an existing, proven pattern from `redeploy_environment()`. Minor observations noted above are not blocking.

IMPLEMENTATION_APPROVED
