All 72 tests pass. I have a complete picture of the implementation.

---

## Implementation Review — T190

### Summary

The implementation correctly fixes the supervisor runtime base resolution bug. The core crash (`OSError: Read-only file system: '/runtime'`) is eliminated and replaced by the correct local path model.

---

### Requirement coverage

#### 1. Explicit runtime base root resolution (`_runtime_base_root()` in supervisor)

✅ Correct. Resolution order matches the ticket exactly:
1. `RUNTIME_BASE_ROOT` env var
2. Parent of `AI_DEV_FACTORY_RUNTIME_ROOT`
3. `~/runtime` (safe local fallback — never `/runtime`)

#### 2. Bootstrap under `<RUNTIME_BASE_ROOT>/<project_id>`

✅ `project_runtime_root = runtime_base_root / body.project_id` — no `/projects/` segment. The five dirs (`runs`, `logs`, `state`, `worktrees`, `clones`) are all created correctly.

`_project_runtime_root()` for the per-project daemon endpoints is also updated to use `_runtime_base_root() / project_id`. For the existing `ai-dev-factory` project where `AI_DEV_FACTORY_RUNTIME_ROOT=/Users/pierrebocquet/runtime/ai-dev-factory`, the derived base root is `/Users/pierrebocquet/runtime` and `_project_runtime_root("ai-dev-factory")` → `/Users/pierrebocquet/runtime/ai-dev-factory`, which preserves the existing path.

#### 3. Fail loudly on unsafe root

✅ Pre-flight `os.access` check on the writable ancestor returns a structured 422 with `error: runtime_base_root_not_writable` before attempting `mkdir`. A catch-all `except OSError` on `mkdir` provides a second safety net.

#### 4. Diagnostics

✅ Log format includes all four required fields: `project_id`, `project_root`, `runtime_base_root`, `project_runtime_root`.

---

### Code quality

- **`project_runtime_root` persisted in registry** — `ProjectEntry` stores the path, persisted to `workspace.json`, rehydrated on load. `ensure_registered` correctly preserves the existing value on re-registration (no env-var drift). Routes thread the persisted value through `resolve_project_runtime_root` dep → all resolver calls.
- **`runtime_resolver.py`** — All four functions accept `project_runtime_root` as first-priority override and their env-var fallback also drops the `/projects/` segment.
- **`assert_contained()` updated** — Now validates against `{runtime_root}/` directly (no `/projects/` level).
- **Tests** — 72/72 pass. Coverage includes: new path layout, `clones` dir, persistence round-trip, 422 on non-writable root, derivation from `AI_DEV_FACTORY_RUNTIME_ROOT`, traversal guard with new layout, `ensure_registered` stability.

---

### Minor observations (non-blocking)

1. **`body.runtime_root` in `ProjectBootstrapHostRequest` is accepted but silently ignored.** The supervisor derives its base from env vars. Passing `"ignored"` in the updated tests documents this. Removing the field would be an API break; the current behaviour is correct for the migration.

2. **`list_projects` fallback path for legacy projects** — When no `project_runtime_root` is persisted (pre-T190 imports), the fallback is `runtime_root / p.name` where `runtime_root` = `AI_DEV_FACTORY_RUNTIME_ROOT`. This is semantically wrong for projects bootstrapped under the old `/projects/` layout, but the result is gated by `.is_dir()` so it safely returns `None` if the directory doesn't exist. All new imports after T190 will have the correct persisted value.

3. **`clones_dir` is created but not returned in the supervisor JSON response.** The caller doesn't currently consume it, so this is a minor omission with no functional impact.

---

### Acceptance criteria

| Criterion | Status |
|---|---|
| No attempt to create under `/runtime/projects` | ✅ |
| Dirs created under `<RUNTIME_BASE_ROOT>/<project_id>/` | ✅ |
| Structured 422 if runtime base root not writable | ✅ |
| No unhandled `OSError: Read-only file system` | ✅ |
| Logs show resolved `runtime_base_root` and `project_runtime_root` | ✅ |
| Existing `ai-dev-factory` runtime path unaffected | ✅ |

All acceptance criteria satisfied. No blocking issues.

IMPLEMENTATION_APPROVED
