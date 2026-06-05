Here is the plan produced for T175:

---

## Objective

Make the environment creation popup and the deploy flow unambiguous about runtime/deployment target: the user sees exactly where the environment will run before launching it, and the backend fails loudly when runtime paths are inconsistent.

## Included

**UI — `CreateEnvironmentModal.jsx`**
- Add a read-only "Runtime target" info block (derived, not user-editable) showing: `Runtime root`, `Environment path` preview, and `Source clone` path. Updates reactively as `env_name` / `sandbox_path` change.

**UI — `EnvironmentCard.jsx`**
- Add a collapsible "Runtime paths" section (same pattern as the existing Debug section, lines 218–235) showing `project_root`, `sandbox_runtime_root`, `sandbox_dir`, and `source_path`.

**Backend validation — `environment_provision.py`**
- Add `_validate_runtime_consistency()` called after `validate_project_root_on_host()` (line 146): asserts `source_path` is a child of `sandbox_dir`, parent dirs exist, and `project_root ≠ sandbox_dir`. Raises `ValueError` → HTTP 422 with explicit mismatch message.

**Backend validation — `sandbox_runtime_deploy.py`**
- After constructing `source_path` (line 281), assert `source_path.resolve().is_relative_to(sandbox_dir.resolve())` and raise `RuntimeError` with diagnostics if not.

**Logging fix — `environment_provision.py`**
- Fix mislabeled log at lines 150–156: `runtime_root=` → `project_root=`; add `sandbox_path=` alongside.

**Logging — `sandbox_runtime_deploy.py`**
- At start of `deploy_operational_runtime()`, emit to both `logger.info()` and `run.log`: `runtime_root`, `sandbox_root`, `source_path`, `project_root`, `script_source`.

**API response**
- Ensure `sandbox_runtime_root`, `sandbox_dir`, `project_root` are included in the environment detail serialisation so the card can read them.

## Excluded

- Allowing users to select/override the runtime root in the UI
- RuntimeDashboardPage changes (already shows this data)
- Disk space / filesystem compatibility checks
- Changes to the supervisor/remote provisioning path
- Renaming existing `SandboxState` fields
- E2E / integration tests

## Acceptance criteria

- Popup shows `Runtime root` and `Environment path` preview, updating live on input
- EnvironmentCard has a collapsible "Runtime paths" section with the four path fields
- `provision_environment()` returns HTTP 422 with explicit message when `source_path` would escape `sandbox_dir`
- `runtime_root=` label bug in `environment_provision.py` is fixed to `project_root=`
- `deploy_operational_runtime()` writes the five-line path header to `run.log` before bootstrap
- Providing an out-of-scope `sandbox_path` raises a clear mismatch diagnostic instead of silently continuing

Plan written to `runs/T175/plan.md`.
