All 4 source files modified as planned (the `runtime.log` update is the auto-generated run log, not a code change). Implementation is complete.

---

## Summary

**Files modified:**

### Backend
- **`environment_provision.py`** — Added `_validate_runtime_consistency()` (called after `validate_project_root_on_host`): detects `project_root == sandbox_path`, either path nested inside the other, or missing parent dir; raises `ValueError` with explicit mismatch diagnostics. Also fixed the mislabeled `runtime_root=` log field to `project_root=` and added `sandbox_path=`.

- **`sandbox_runtime_deploy.py`** — Added an early assertion that `source_path` is inside `sandbox_dir` (explicit guard, fails with a clear RuntimeError). Added a five-line path header written to both `run.log` and `logger.info` at the start of every deploy: `runtime_root`, `sandbox_root`, `source_path`, `project_root`, `script_source`.

### Frontend
- **`CreateEnvironmentModal.jsx`** — Added a static "Runtime target" info block in the manual-entry form (non-project-id flow), showing `sandbox_path`, `sandbox_path/runtime`, and `sandbox_path/source`; updates reactively. Displays "(auto-assigned)" when no sandbox path is set.

- **`EnvironmentCard.jsx`** — Added a collapsible "Runtime paths" toggle (same pattern as Debug section) showing `project_root`, `runtime_root`, `sandbox_dir`, and `source_path` from the API response; only rendered when at least one field is non-empty.
