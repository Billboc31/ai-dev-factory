I have all the information needed for the review.

---

## Review — T177: Fix environment runtime root override propagation

### Summary

The root cause was correctly identified: `EnvironmentProvisionRequest` in `services/supervisor/main.py` was missing the `runtime_root` and `force_source_refresh` field declarations, so Pydantic silently dropped them before they could reach `provision_environment_from_body`. The fix is minimal, targeted, and complete.

---

### Correctness relative to ticket requirements

**Propagation chain — all links verified:**

1. **Frontend → control_api**: Already worked; unchanged.
2. **control_api → supervisor** (`body.model_dump(mode="json")`): Fix adds the two missing fields to `EnvironmentProvisionRequest`. The serialised dict now includes `runtime_root`.
3. **Supervisor → `provision_environment_from_body`**: Handler calls `body.model_dump()`, which now includes `runtime_root`. The downstream function already reads it via `body.get("runtime_root")` (line 319 of `environment_provision.py`).
4. **`SandboxState` → `_resolve_runtime_root`**: Already set `runtime_root_source = "override"` vs `"auto"` and logged both. Already correct; unchanged.

No links in the chain were missed or incorrectly modified.

**Validation alignment:**

The added validation (`is_absolute()` + `..` check) exactly mirrors `control_api/routes/environments.py` lines 105–111. There is a subtlety: `_resolve_runtime_root` does a stronger containment check (`new_sandbox_dir.relative_to(rt.resolve())`), which would be caught by the existing `except ValueError` → 422 fallback anyway. The early 400 is a useful fast-fail and the validation is sufficient.

---

### Scope compliance

- 2 fields added to the model (necessary, minimum)
- 1 validation block (12 lines, exact mirror of existing pattern)
- 2 tests
- Zero unrelated changes

No drift. The plan's "Excluded" list is fully respected — UI, control_api routes, `SandboxState` model, `sandbox_runtime_deploy.py`, and redeploy flow were all correctly left untouched.

---

### Code quality

- `from pathlib import Path` inside the function body is unusual but consistent with the existing style in this handler (which also imports `JSONResponse` and `provision_environment_from_body` inside the function). Not a quality issue.
- Validation error message (`"runtime_root: must be an absolute path without '..'"`), error shape (`{"ok": False, "error": "..."}`), and HTTP status (400) are all consistent with adjacent patterns in the file.
- No dead code introduced.

---

### Test quality

`test_provision_runtime_root_override_propagates`:
- Captures `state.runtime_root` via a mock side-effect — verifies the value reaches `deploy_operational_runtime` at the call site, not just the response body.
- Asserts both `r.json()["state"]["runtime_root"]` and `captured_state["runtime_root"]`. Double assertion is appropriate here given the propagation nature of the bug.

`test_provision_invalid_runtime_root_returns_400`:
- Covers both `"relative/path"` and `"/a/../b"` — correct coverage of the two rejection branches.

`force_source_refresh` field added but not independently tested — acceptable, as it was already exercised by other tests and the ticket's focus is `runtime_root`.

---

### Acceptance criteria — verified

| Criterion | Status |
|---|---|
| Request payload contains selected runtime_root | ✅ Field now declared; Pydantic passes it through |
| Backend persists it | ✅ `provision_environment_from_body` reads and stores it in `SandboxState` |
| Deploy reads the persisted value | ✅ `_resolve_runtime_root` already consumes `state.runtime_root` |
| Logs show auto vs override | ✅ `runtime_root_source` already logged at deploy time |
| Invalid values fail validation | ✅ 400 returned; tested |

---

### Observations (non-blocking)

- The pre-existing `test_supervisor_provision_maps_and_validates_host_project_root` failure is unrelated; no action required.
- The supervisor returns HTTP 400 while the control_api returns 422 for path validation errors. Minor inconsistency, acceptable for an internal service.

---

### Verdict

The fix is correct, minimal, and well-tested. All acceptance criteria from the ticket are satisfied.

IMPLEMENTATION_APPROVED
