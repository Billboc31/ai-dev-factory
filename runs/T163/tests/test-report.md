I have enough data for the full test report. Let me write it.

---

## Test Report — T163: Persist failed environment deployments for debugging and retry

### Scope

Validation of the `provision_environment()` change in `services/control_api/services/environment_provision.py` and the three updated tests in `tests/test_environment_routes.py`.

---

### Test suite execution

```
31 passed in 1.95s
```

All 31 tests pass with no failures or errors.

---

### Acceptance criteria — status

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | Failed environments remain visible in the dashboard | **PASS** | `provision_environment()` calls `apply_deploy_failure()` + `mgr._write_state(failed)` on both failure paths (exception and failed-result). `GET /environments` returns all environments with `env_name != None`, including error-state ones. `test_failed_provisioning_persists_environment_card` PASSED. |
| 2 | Failure reason and lifecycle step are persisted | **PASS** | `apply_deploy_failure()` sets `lifecycle_error=result.error`, `last_step`, `lifecycle_steps`, `lifecycle_phase=failed`. Exception path captures `str(exc)`. Verified by code inspection and parity with `redeploy_environment()`. |
| 3 | Logs remain accessible after failure | **PASS** | No `_destroy_quietly()` call remains on any failure path — confirmed by grep (only the dead definition at line 265). Sandbox dir is preserved. `GET /environments/{env_id}/logs` reads from preserved sandbox dir. `test_failed_provisioning_preserves_sandbox_dir` and `test_failed_provisioning_preserves_custom_sandbox_path` PASSED. |
| 4 | Retry Deploy works from failed environments | **PASS** | `redeploy_environment()` reads state then calls `mgr.stop()` (safe on a stopped/error environment), resets status to `creating`, and re-runs the full pipeline. Existing redeploy test PASSED. Note: test only covers redeploy from a healthy environment — no test explicitly resets to failed state then redeploys. Functionally sound but minor coverage gap. |
| 5 | Delete works on failed environments | **PASS** | `DELETE /environments/{env_id}` calls `mgr.destroy(env_id)` which handles any state regardless of lifecycle phase. Existing deletion test PASSED. Same coverage gap as AC4 — no test explicitly deletes from a failed state. |
| 6 | Failed environments are clearly marked as failed | **PASS** | `apply_deploy_failure()` sets `status=SandboxStatus.error`, `lifecycle_phase=LifecyclePhase.failed`. `test_failed_provisioning_persists_environment_card` asserts `envs[0]["status"] == "error"`. PASSED. |
| 7 | No fake healthy/running status | **PASS** | `apply_deploy_failure()` enforces `urls={}` and `status=SandboxStatus.error`. Not `running`, not `healthy`. Verified by code inspection. |
| 8 | Existing successful deploy flows continue to work | **PASS** | Success path in `provision_environment()` is completely untouched (lines 185–187). 27 of 31 tests cover successful deploy paths — all pass. |

---

### Regressions

None. The change is additive-only on the failure path. The success path was not modified.

---

### Code inspection findings

**`_destroy_quietly()` is unreachable dead code.** The helper defined at `environment_provision.py:265` is never called from any runtime path. This was noted as non-blocking in the implementation review and is confirmed by grep. It is a cleanup concern, not a defect.

**`_destroy_silently()` in `environments.py:44`** is a pre-existing separate dead helper, unrelated to this change — it also goes uncalled. Not introduced by this ticket.

**Exception path `lifecycle_steps` is `[]`.** When a mid-deploy exception fires, `OperationalDeployResult(success=False, error=str(exc))` has no steps, so `lifecycle_steps=[]` is persisted. Partial step progress is still accessible via `run.log`/`supervisor.log` on disk. This matches `redeploy_environment()` behavior — consistent, not a defect.

---

### Minor gaps (non-blocking)

1. Tests for AC4 and AC5 do not explicitly test redeploy or delete from a `status=error` environment. The code path is correct, but targeted tests would increase confidence.
2. New tests assert `status=error` but do not assert `lifecycle_error` is non-null, leaving a minor assertion gap on the failure-context field.

---

### Conclusion

**All 8 acceptance criteria are satisfied.** The implementation is minimal, correct, and well-tested. The minor coverage gaps noted above are not blocking. The change introduces no regressions.

**TEST_COMPLETE — PASS**
