Now I have a complete picture. Let me write the review.

---

## Implementation Review — T176: Redeploy source clone rehydration + runtime root override

### Summary

The implementation is correct, well-scoped, and addresses all ticket acceptance criteria. No blocking issues found. Several minor observations noted below.

---

### File-by-file analysis

#### `models/sandbox.py`

Clean minimal addition of three fields (`runtime_root`, `effective_runtime_root`, `force_source_refresh`). Correct defaults. ✅

---

#### `routes/environments.py`

- `runtime_root` and `force_source_refresh` added to `CreateEnvironmentRequest` ✅
- API-boundary validation at lines 105–111 runs **before** the supervisor path check, so it fires in both proxy and direct modes ✅
- The `..` check uses `rt.parts` which correctly catches literal `..` components (Python `Path` does not normalize `..` until `.resolve()`) ✅
- Both fields forwarded to `provision_environment` ✅

**Minor**: The error-handling in `submit()` (`CreateEnvironmentModal`) does not parse `"runtime_root: ..."` error prefixes. A 400 from path validation shows as a generic bottom-level error instead of a field-level one. Non-blocking UX issue.

---

#### `environment_provision.py`

- `provision_environment` and `provision_environment_from_body` correctly accept and propagate both new fields ✅
- Fields are applied to `SandboxState` via `model_copy` after `mgr.create()`, so they persist in `state.json` for future redeploys ✅
- `redeploy_environment` reads the saved `runtime_root` and `force_source_refresh` from existing state — this is correct, the override should survive across redeploysunless changed ✅

**Observation**: `force_source_refresh=True` persists forever once set at create time; every subsequent redeploy will force-reclone. This is per-plan but may surprise operators — the flag has no one-shot semantic. Worth documenting as a known behavior.

---

#### `sandbox_runtime_deploy.py`

**`_is_source_clone_valid`**: Checks `.git` and `.ai-dev-factory/scripts` — matches ticket's validation spec ✅

**`_rehydrate_source_clone`**: All required log lines are present:
- `"source clone missing or invalid"` ✅
- `"rehydrating sandbox source clone"` ✅
- `"repo=..."` ✅
- `"branch=..."` ✅
- `"source_path=..."` ✅
- `"sandbox source clone restored successfully"` ✅

**`_resolve_runtime_root`**: Absolute path, no `..`, symlink escape prevention via `relative_to(rt.resolve())`, directory creation, correct `"auto"|"override"` label ✅

**`deploy_operational_runtime` logic** (lines 470–496):
```python
needs_rehydration = (
    not _is_source_clone_valid(source_path) or current[0].force_source_refresh
)
```

Correct routing: rehydration logs + clone, vs. silent clone. ✅

**Notable observation — misleading logs on fresh create**: On every first `provision_environment`, `source_path` does not exist yet, so `_is_source_clone_valid()` returns `False`, triggering the rehydration path with its "source clone missing or invalid" message. This message is semantically designed for the redeploy-after-source-loss scenario, and will appear in all fresh deploy logs. Per-plan behavior, but will confuse anyone reading logs expecting this to indicate a recovery event vs. a normal first deploy.

**`effective_runtime_root` assignment** (line 405): Stores `sandbox_dir.parent`, which is the runtime root directory (not the sandbox directory itself). This is consistent with the `runtime_root` concept (parent under which `{id}/` is created) ✅

---

#### `CreateEnvironmentModal.jsx`

- `runtime_root` and `force_source_refresh` in form state ✅
- Advanced section collapsed by default (`showAdvancedRuntime = false`) ✅
- `▸`/`▾` toggle ✅
- "Runtime target" preview updates live when `runtime_root` is set, showing `<runtime_root>/<id>/`, `/<id>/runtime`, `/<id>/source` ✅
- Both fields sent in create payload (both `projectId` and non-`projectId` paths) ✅
- Advanced section appears for both the `projectId` and manual-path forms — acceptable ✅

---

### Acceptance criteria verification

| Criterion | Status |
|---|---|
| Redeploy no longer fails when `source/.ai-dev-factory/scripts` is missing | ✅ |
| Missing source clone is automatically recreated | ✅ |
| Correct branch/ref is restored automatically | ✅ |
| Logs clearly indicate clone rehydration | ✅ |
| Advanced runtime options available but collapsed by default | ✅ |
| Users can force source refresh/reclone | ✅ |
| Runtime validation still prevents cross-runtime path mismatches | ✅ (unchanged `_validate_runtime_consistency`) |

---

### Scope compliance

Excluded items from plan (tests, per-existing-env refresh UI, sandbox root / source path overrides) are correctly absent. No scope creep detected.

---

### Verdict

Implementation is correct and complete. All ticket requirements are satisfied. Minor observations are non-blocking.

IMPLEMENTATION_APPROVED
