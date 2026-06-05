---

## Test Report — T175

**Verdict: FAIL — IMPLEMENTATION_FIX_REQUIRED**

### Acceptance Criteria — 7/7 PASS

All 7 acceptance criteria are satisfied at the code level:
- "Runtime target" block appears in both modal flows (project-ID and manual)
- `EnvironmentCard` shows collapsible "Runtime paths" with all 4 fields
- 5-line path header logged before bootstrap, with corrected labels
- `_validate_runtime_consistency()` catches 4 overlap scenarios + explicit HTTP 422
- Script source enforced from `source_path/.ai-dev-factory/scripts`

### Test Regressions — 3 BLOCKING

```
3 failed, 32 passed
```

**Regression 1 & 2** — `sandbox.parent.exists()` check too strict (`environment_provision.py:117-120`).  
The new validation rejects any sandbox path whose parent doesn't exist yet — but `SandboxManager` auto-creates nested paths. Two existing tests that document this behavior now get HTTP 422 instead of 201/200.  
**Fix**: Remove the 3-line parent-existence guard; the 3 overlap checks (equal, sandbox-inside-project, project-inside-sandbox) are the real safety net.

**Regression 3** — Script source check fires inside `test_provision_endpoint_triggers_infra_bootstrap`.  
`_clone_fresh_source` is mocked to succeed but doesn't create `source_path/.ai-dev-factory/scripts`. The test creates scripts under `host_project/` (old behavior), but the new check looks under `source_path/`. The test fixture needs updating to align with the new scripts-from-source-clone contract.

Report saved to: `runs/T175/tests/tester-report.md`
