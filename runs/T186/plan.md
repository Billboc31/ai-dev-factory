I have enough information to write the plan. Here's what I found:

**Current state**: `main.py` lines 89-92 call `ensure_registered(_root.name, _root)` — but `_root.name` is the worktree directory name (e.g., `T186`), not the stable repo name (`ai-dev-factory`), and `ensure_registered` only adds to the in-memory registry without creating runtime dirs (`runs/`, `logs/`, `state/`, `worktrees/`) or `project.yml`. So the project appears in `/projects` with `runtime_root: null`, `stack: null`, and no working daemon/log support.

---

## Objective

Ensure the current AI Dev Factory repository is automatically registered on startup as a fully bootstrapped workspace project — with a stable project ID derived from the real git root, runtime directories created, and behaviour identical to manually imported projects.

## Included

**`services/control_api/services/git_root.py`** (new file)
- `resolve_git_root(path: Path) -> Path`: given a path that may be a normal clone (`.git/` dir) or a git worktree (`.git` file), return the main working tree root by parsing the `.git` file → `commondir` → parent. Falls back to `path` if resolution fails.

**`services/control_api/services/project_bootstrap.py`** (modify)
- Add `auto_bootstrap(project_root, project_id, runtime_root, registry)`:
  - Idempotent: uses `registry.ensure_registered()` instead of `registry.register()` so it does not raise on restart.
  - Worktree-safe: accepts `.git` as a file or directory (no `is_dir()` guard).
  - Creates `{runtime_root}/projects/{project_id}/{runs,logs,state,worktrees}/` with `mkdir(parents=True, exist_ok=True)`.
  - Writes `.ai-dev-factory/project.yml` if absent (same format as existing `bootstrap()`).
  - Validates `project_id` with `validate_project_id()`; logs a warning and returns without raising if invalid.
  - When `runtime_root` is `None`, skips dir creation and project.yml, and only calls `ensure_registered()`.

**`services/control_api/main.py`** (modify, lines 89-92)

Replace:
```python
if (_root / ".git").exists():
    app.state.project_registry.ensure_registered(_root.name, _root)
```
With:
```python
from .services.git_root import resolve_git_root
from .services.project_id import normalize_project_id
from .services.project_bootstrap import auto_bootstrap

_git_root = resolve_git_root(_root)
if (_git_root / ".git").exists():
    _self_id = normalize_project_id(_git_root.name)
    auto_bootstrap(_git_root, _self_id, _runtime_root, app.state.project_registry)
```
This gives a stable project ID (`ai-dev-factory`) regardless of which worktree the API process runs in, and fully bootstraps the runtime dirs when `runtime_root` is configured.

**`tests/test_git_root.py`** (new file)
- `resolve_git_root` on a normal clone (`.git/` dir present) returns the same path.
- `resolve_git_root` on a worktree path (`.git` is a file pointing to `commondir`) returns the main clone root.
- `resolve_git_root` on a non-git path returns the path unchanged (graceful fallback).

**`tests/test_auto_bootstrap.py`** (new file)
- `auto_bootstrap` creates all four runtime subdirs under `{runtime_root}/projects/{project_id}/`.
- `auto_bootstrap` writes `.ai-dev-factory/project.yml` with correct `name` and `stack` fields.
- `auto_bootstrap` called twice does not raise (idempotent).
- `auto_bootstrap` with `runtime_root=None` only calls `ensure_registered`, no dirs created.
- `auto_bootstrap` with an invalid project ID logs a warning and returns without raising.

## Excluded

- Any UI changes (the auto-registered project already appears in the frontend via the existing `GET /projects` poll and `ProjectSidebar` state; no new routes or components are needed).
- Changes to `project_registry.py`, `project_id.py`, or `stack_detector.py` — these are already correct.
- Changes to existing `bootstrap()` function signature or behaviour — `auto_bootstrap` is a separate entry point.
- Daemon supervisor or ticket workflow changes — once runtime dirs exist, existing routes handle them identically for any project.
- Handling repos without a `runtime_root` configured beyond the `ensure_registered` fallback.

## Acceptance criteria

- On API startup with `AI_DEV_FACTORY_RUNTIME_ROOT` set, `GET /projects` returns an entry whose `name` is `ai-dev-factory` (or the normalized repo dir name), `runtime_root` is non-null, and `stack` is non-null.
- The entry survives an API restart without creating a duplicate (`ensure_registered` idempotency).
- When the API runs inside a git worktree (e.g., `/worktrees/T186`), the registered project ID is derived from the main clone name, not the worktree directory name.
- All existing tests in `test_project_bootstrap.py`, `test_project_registry.py`, and `test_projects_endpoint.py` continue to pass without modification.
- `pytest tests/test_git_root.py tests/test_auto_bootstrap.py` passes.
- Manually imported projects are unaffected (no change to `POST /projects/import` behaviour).
