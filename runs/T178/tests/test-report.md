---

## T178 Test Report — Summary

**Verdict: PASS** — All 4 acceptance criteria satisfied.

| Criterion | Status |
|---|---|
| AC1: Active runtime contains T177 changes | **PASS** |
| AC2: Supervisor restart picks up new model fields | **PASS** |
| AC3: runtime_root override works end-to-end | **PASS** |
| AC4: Logs show `runtime_root_source=override` | **PASS** |

**Test execution**: 5/6 passing. The 1 failure (`test_supervisor_provision_maps_and_validates_host_project_root`) is pre-existing and unrelated to T178 — it fails due to a sandbox path fixture issue, not any runtime_root logic.

**Root cause fixed**: `EnvironmentProvisionRequest` in `services/supervisor/main.py` was missing the `runtime_root` and `force_source_refresh` field declarations, causing `.model_dump()` to silently drop `runtime_root` before reaching the provisioning layer. Adding the two fields (lines 1260-1261) restores end-to-end propagation.

State updated to `TEST_COMPLETE`. Report written to `runs/T178/tests/test-report.md`.
