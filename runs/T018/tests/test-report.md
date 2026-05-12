**Test report written to `runs/T018/tests/test-report.md`.**

---

## Summary

**61/61 tests pass — VALIDATION: PASS**

All T018 acceptance criteria are met:

| Criterion | Status |
|---|---|
| Failure explicite dans runtime.log | PASS — `runtime failure: X (rc=N)` logged on every non-zero exit |
| State unchanged on failure | PASS — `test_state_unchanged_on_step_failure` confirms state.json unmodified |
| Permission issue détectée | PASS — `write_permission_missing` matches "I need write permission / Please grant it" and related patterns |
| Quota/provider issue détecté | PASS — 6 quota patterns, 9 provider patterns, all exercised by tests |
| Compatibilité workflow | PASS — 43 pre-existing tests (snapshots, reviews, fix loops, commit/push) all green |

**One non-blocking observation:** in the `auto_run` path, stderr is not passed to the second `classify_runtime_failure` call. If a provider error appears only in stderr and stdout is empty, the log will show `provider_error` (accurate, from `_call_run_step`) followed by `empty_output` (less precise, from `auto_run`). Diagnosis is still present; state invariant is unaffected. This is within acceptable range for T018's scope.
