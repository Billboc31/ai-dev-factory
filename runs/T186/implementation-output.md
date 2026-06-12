Everything looks correct. Here's a summary of what was implemented:

---

## Changes

**`services/control_api/services/git_root.py`** (new)
- `resolve_git_root(path)`: follows the `.git` file → `commondir` chain to find the main clone root when running inside a git worktree. Falls back gracefully on any error.

**`services/control_api/services/project_bootstrap.py`** (modified)
- Added `auto_bootstrap(project_root, project_id, runtime_root, registry)`: idempotent startup registration that accepts `.git` as file or dir, creates all four runtime subdirs, writes `project.yml` if absent, and calls `ensure_registered()` — never raises on restart or duplicate.

**`services/control_api/main.py`** (modified, lines 89-98)
- Replaced the bare `ensure_registered(_root.name, _root)` call with `resolve_git_root` + `normalize_project_id` + `auto_bootstrap`, giving a stable project ID (`ai-dev-factory`) and full runtime dir creation regardless of whether the API runs inside a worktree.

**`tests/test_git_root.py`** (new) — 5 tests covering normal clone, non-git path, worktree resolution, malformed `.git` file, missing `commondir`.

**`tests/test_auto_bootstrap.py`** (new) — 8 tests covering runtime dir creation, `project.yml` writing, idempotency, `runtime_root=None` fallback, invalid ID warning, and worktree path acceptance.

All 13 new tests pass; all 30 pre-existing related tests pass without modification.
