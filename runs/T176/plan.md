The plan is written to `runs/T176/plan.md`. Here is what it contains:

## Objective
Self-healing redeploy (source clone rehydration) + fully wired `runtime_root` override end-to-end.

## Included — 4 files, concrete changes

| File | What changes |
|---|---|
| `models/sandbox.py` | `SandboxState` gains `runtime_root`, `effective_runtime_root`, `force_source_refresh` |
| `routes/environments.py` | `CreateEnvironmentRequest` gets `runtime_root` + `force_source_refresh`; API boundary validates absolute path, rejects `..` with 400 |
| `sandbox_runtime_deploy.py` | `_is_source_clone_valid`, `_rehydrate_source_clone` (with all 3 required log lines); `_resolve_runtime_root` that validates ownership, derives `sandbox_dir` from override, persists `effective_runtime_root`, logs `runtime_root_source=auto|override` |
| `CreateEnvironmentModal.jsx` | Advanced section (collapsed by default) with `runtime_root` text input + `force_source_refresh` checkbox; live sandbox destination preview |

## Excluded
Automated tests, per-existing-environment UI for refresh, sandbox root / source path overrides (follow-up), changes to `_validate_runtime_consistency`.

## Acceptance criteria
13 verifiable conditions covering rehydration, logging, `force_source_refresh`, runtime root override behavior, API validation, persistence, and UI.
