The corrected plan is written to `runs/T176/plan.md`. Here is a summary of what changed and why:

**Root cause of the rejection:** The previous plan accepted `runtime_root` in the API request but explicitly excluded wiring it to any backend behavior — making the UI field a no-op that misleads users.

**Key changes in the fix:**

1. **`SandboxState`** now gains three fields: `runtime_root` (user input), `effective_runtime_root` (resolved at deploy time), and `force_source_refresh`.

2. **`_resolve_runtime_root()`** added to `sandbox_runtime_deploy.py` — selects between the user override and auto-detected default, validates path safety (absolute, no `..`, within allowed roots, sandbox_dir descends from it), and returns `(path, "auto"|"override")`.

3. **`deploy_operational_runtime()`** calls `_resolve_runtime_root` early, logs `runtime_root=… runtime_root_source=…`, derives `sandbox_dir` from the effective root when the user supplied one, and persists `effective_runtime_root` back to state.

4. **API boundary validation** rejects non-absolute or path-traversal `runtime_root` values with a `400` before they reach the service layer.

5. **UI live preview** updates the displayed sandbox destination as the user types in the `runtime_root` field.

The source-clone rehydration logic (`_is_source_clone_valid`, `_rehydrate_source_clone`) is unchanged from the prior attempt.
