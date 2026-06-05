# Tester Report — T175

**Date**: 2026-06-05  
**Branch**: ticket/T175-t175-environment-creation-ui-must-expose-and-valid  
**Verdict**: FAIL — 3 test regressions blocking merge

---

## Acceptance Criteria

| # | Criterion | Status | Evidence |
|---|-----------|--------|----------|
| 1 | Environment popup clearly shows deployment target/runtime | PASS | `CreateEnvironmentModal.jsx:239-255` (project-ID flow) and `:280-300` (manual flow): "Runtime target" block with Sandbox path / Runtime root / Source clone |
| 2 | Runtime ownership is understandable from the UI | PASS | `EnvironmentCard.jsx:238-256`: collapsible "Runtime paths" section shows `project_root`, `runtime_root`, `sandbox_dir`, `source_path` post-deploy |
| 3 | Logs clearly distinguish project_root vs source_path vs runtime_root | PASS | `sandbox_runtime_deploy.py:332-342`: 5-line header (`runtime_root`, `sandbox_root`, `source_path`, `project_root`, `script_source`) written to `run.log` and `logger.info` before bootstrap |
| 4 | Runtime mismatch situations fail explicitly | PASS | `environment_provision.py:93-120`: `_validate_runtime_consistency()` raises HTTP 422 for 4 overlap cases; `sandbox_runtime_deploy.py:326-331`: script source existence enforced |
| 5 | Users can verify deploy destination before launching | PASS | Manual flow shows reactive paths as user types; project-ID flow shows "(auto-assigned)" label |
| 6 | Sandbox deploy always uses scripts from sandbox source clone | PASS | `sandbox_runtime_deploy.py:326-331`: raises `RuntimeError` if `source_path/.ai-dev-factory/scripts` missing |
| 7 | No hidden fallback to another runtime root | PASS | Validation prevents path overlaps; all paths logged before operation |

---

## Test Regressions — BLOCKING

Run: `python -m pytest tests/test_environment_routes.py tests/test_environment_supervisor.py -v`  
Result: **3 failed, 32 passed**

---

### Regression 1 — `test_create_environment_auto_creates_nested_custom_sandbox_path`

**File**: `tests/test_environment_routes.py:560`  
**Error**: HTTP 422 `runtime mismatch: sandbox_path parent directory does not exist`  
**Expected**: HTTP 201 (environment created with auto-created nested path)

**Root cause**: `_validate_runtime_consistency()` checks `sandbox.parent.exists()` at line 117. The test deliberately creates a deeply nested `sandbox_path` (`tmp_path/custom/envs/demo/runtime`) whose parent doesn't exist yet — this is a documented use case: `SandboxManager` auto-creates nested paths when deploying. The new parent-existence check rejects a valid scenario.

---

### Regression 2 — `test_supervisor_provision_maps_and_validates_host_project_root`

**File**: `tests/test_environment_supervisor.py:39`  
**Error**: HTTP 422 `runtime mismatch: sandbox_path parent directory does not exist: .../sandboxes`  
**Expected**: HTTP 200

**Root cause**: Same as Regression 1. `custom_sandbox = tmp_path / "sandboxes" / "demo"` has a non-existent parent (`tmp_path/sandboxes`). The `_validate_runtime_consistency` rejects it, but `SandboxManager` would create it.

---

### Regression 3 — `test_provision_endpoint_triggers_infra_bootstrap`

**File**: `tests/test_environment_supervisor.py:106`  
**Error**: `RuntimeError: runtime mismatch: scripts directory not found at /Users/pierrebocquet/sandboxes/ai-dev-factory/<id>/source/.ai-dev-factory/scripts`  
**Expected**: HTTP 200 (deploy succeeds, `mock_infra` asserted called once)

**Root cause**: `_clone_fresh_source` is mocked at `sandbox_runtime_deploy._clone_fresh_source` to return `(True, None, "abc1234")` but does not create the actual `source_path/.ai-dev-factory/scripts` directory. The test creates scripts at `host_project/.ai-dev-factory/scripts` (the project root) — valid for old code, but new code checks `source_path` (under sandbox). The test fixture needs updating to create scripts at `source_path/.ai-dev-factory/scripts`, or the test must mock the scripts existence check.

---

## Required Fixes

### Fix 1 — Remove over-strict parent-directory check

`environment_provision.py:117-120` — remove the `sandbox.parent.exists()` guard:
```python
# REMOVE these 3 lines:
if not sandbox.parent.exists():
    raise ValueError(
        f"runtime mismatch: sandbox_path parent directory does not exist: {sandbox.parent}"
    )
```
**Justification**: `SandboxManager.create()` auto-creates sandbox paths with all parents. The check prevents a legitimate use case. The 3 remaining overlap checks (equal, sandbox-inside-project, project-inside-sandbox) are the real safety net.

### Fix 2 — Update `test_provision_endpoint_triggers_infra_bootstrap`

The test fixture must ensure `source_path/.ai-dev-factory/scripts` exists before the deploy runs. Since `source_path` is computed as `<sandbox_dir>/source`, and the sandbox manager uses the actual runtime root in this test (supervisor uses `AI_DEV_FACTORY_RUNTIME_ROOT`), the test should either:
- Mock `sandbox_runtime_deploy.deploy_operational_runtime` entirely (like `_patch_deploy_ok` does in the routes tests), OR
- Mock the `script_source.is_dir()` call, OR
- Set the supervisor's runtime root to `tmp_path` so the sandbox ID resolves under `tmp_path`, then create `source/.ai-dev-factory/scripts` after learning the sandbox ID

---

## Notes

- All 7 acceptance criteria are satisfied at the code level.
- The regressions are caused by two new checks that are stricter than the code previously allowed.
- Fix 1 is a one-line deletion. Fix 2 requires test infrastructure changes.
- No UI testing was performed (dev server not started); frontend verification is limited to code review.
