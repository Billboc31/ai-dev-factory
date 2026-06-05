---

## Test Report — T177

All **5 acceptance criteria pass**. No regressions introduced.

### Acceptance criteria results

| AC | Description | Status |
|---|---|---|
| AC1 | Request payload contains the selected runtime root | **PASS** |
| AC2 | Backend persists the value | **PASS** |
| AC3 | Deploy reads the persisted value | **PASS** |
| AC4 | Logs show auto vs override mode | **PASS** |
| AC5 | Invalid values return 400 instead of being ignored | **PASS** |

### New tests

Both T177 tests pass:
- `test_provision_runtime_root_override_propagates` — valid override reaches `SandboxState` and `deploy_operational_runtime`
- `test_provision_invalid_runtime_root_returns_400` — `"relative/path"` and `"/a/../b"` both return HTTP 400

### Regressions

None. The single failure in `test_environment_supervisor.py` (`test_supervisor_provision_maps_and_validates_host_project_root`) is pre-existing on `main` — confirmed by running it after stash. The 62 suite-wide failures are all pre-existing in unrelated test files, none touching files modified by this ticket.

### Root cause confirmed

The fix is minimal and correct: adding `runtime_root: str | None = None` to `EnvironmentProvisionRequest` was the only missing piece. All downstream layers (persistence, deploy resolution, logging) were already wired up correctly.

Report saved to `runs/T177/test-report.md`.
