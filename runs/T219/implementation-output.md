All four review actions are addressed and tests are green. Here's the summary.

## Summary of changes

**Files modified to satisfy review (PR-relevant):**

| File | Change |
|---|---|
| `.gitignore` | Added `postgres:adf#*` to block the Postgres-handle-as-path leak at the source |
| `tests/api/test_batches_routes.py` | `_make_app` now aliases `resolve_db_path_for_project` onto the SQLite module so route handlers don't end up calling `sqlite3.connect("postgres:adf#…")` and creating a file in CWD |
| `services/control_api/routes/batches.py` | `_build_insights`: hoisted `_ticket_runtime_map(db_path)` above the loop (N+1 fix) |
| `apps/dashboard/src/components/ProjectSidebar.jsx` | Added `end: true` to the Dispatcher nav entry; threaded `end` through `NavLink` so `/dispatcher/batches` no longer also highlights the Dispatcher tab |
| `postgres:adf#ai-dev-factory`, `postgres:adf#proj-a` | Deleted (tracked + on-disk) |
| `apps/dashboard/node_modules/.vite/vitest/results.json` | Restored to pre-T219 (commit `65da148a`) content |

**Verification:**
- `pytest tests/api/test_batches_routes.py` → **17 passed**
- `npx vitest run` on `BatchesPage` + `BatchDetailPage` + `BatchDependencyGraph` + `ProjectSidebar` → **26 passed**
- After the backend run, no `postgres:adf#*` files appeared in CWD — the fixture patch holds.

The other modifications shown in `git status` (`runs/T219/daemon.lock`, `runs/T219/runtime.log`, untracked files under `runs/T219/`) are daemon-managed runtime artifacts, untouched by this fix.
