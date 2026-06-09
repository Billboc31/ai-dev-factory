I have enough information to write the review. Let me compile the complete assessment.

---

## Implementation Review — T181: Multi-project workspace & existing project bootstrap

### Summary

The implementation covers all plan acceptance criteria. The architecture shift from environment-centric to project-centric is coherent, the security design is sound, and the new endpoints follow the existing code conventions. No scope drift detected.

---

### 1. Correctness relative to ticket requirements

**All plan acceptance criteria are met:**

| AC | Status |
|---|---|
| `GET /projects` returns runtime_root and stack | ✓ |
| `POST /projects/import` creates runtime dirs + writes project.yml + persists to workspace.json | ✓ |
| 4xx on non-git path, invalid ID, duplicate ID | ✓ |
| Containment assertion in unit test | ✓ |
| Supervisor: per-project daemon start/stop/status with isolated PID file | ✓ |
| Supervisor: registry validation before daemon start | ✓ |
| Two projects can run simultaneous daemons | ✓ |
| Global daemon state untouched | ✓ |
| ProjectsPage + ImportProjectPage functional | ✓ |
| Existing tests pass | ✓ |

---

### 2. Security & correctness issues

**`normalize_project_id` — truncation can produce a trailing dash (minor, non-blocking)**

`project_id.py:23-26`:
```python
slug = slug.strip("-")   # strip THEN truncate
slug = slug[:_MAX_LEN]   # a name like "a"*63+"-b" → truncates to "a"*63+"-"
```

If a 65-char input truncates at a dash (char 64), the result ends with `-`, which fails `_VALID_RE`. The user would see a seemingly-valid preview in the UI but receive a 422 on submit.

Fix: strip after truncation.
```python
slug = slug[:_MAX_LEN].strip("-")
```

The frontend `normalizeProjectId` in `ImportProjectPage.jsx:6-12` has the same issue.

**Supervisor path parameters — no `validate_project_id` call (minor, guarded)**

`supervisor/main.py`, all three `/projects/{project_id}/daemon/*` handlers call `_project_runtime_root(project_id)` which does a raw path join without calling `assert_contained`. The registry lookup acts as a practical guard (unregistered `..` returns 404 before path use), but the explicit validation is absent. A `validate_project_id(project_id)` call at the top of each handler would close this gap.

---

### 3. Design observations

**`ProjectRegistry.__init__` — `_workspace_file` only mode is undocumented but used in tests**

`project_registry.py:26-34`: passing only `_workspace_file=...` without `_entries` raises ValueError. The constructor requires `_entries=[]` to be explicit. Tests do this correctly, but the constructor signature is easy to misuse. No immediate bug, but worth a short comment or a dedicated factory.

**`_project_daemon_states` not cleaned on stop**

`supervisor/main.py`: `project_daemon_stop` nulls `state.pid` and `state.started_at` but leaves the `DaemonState` object in `_project_daemon_states`. Correct runtime behavior (status returns `running=False`), but the dict grows indefinitely with stopped-project entries. Acceptable for MVP.

**`_scan` fallback — uses raw directory names as project IDs**

`project_registry.py:40-44`: the legacy scan mode doesn't validate directory names against `_VALID_RE`. Project IDs in legacy mode could contain uppercase or dots. Since bootstrap and import always call `validate_project_id` first, only projects created outside this workflow are affected. Acceptable as a legacy compatibility path.

---

### 4. Code quality

- Files are well-scoped, no unnecessary abstractions introduced.
- Bootstrap is idempotent (project.yml not overwritten).
- Registry persistence error is caught and logged without crashing the API.
- Frontend normalization preview with inline yellow warning is the right UX pattern.
- 45 new tests, 0 regressions.

---

### 5. Scope compliance

No scope drift. Traefik, deploy environments, SQLite partitioning, and URL-scheme refactor are correctly excluded per plan. The known out-of-scope limitation (ticket/worktree collision across projects) is documented.

---

### Verdict

The implementation is correct and production-grade for an MVP. The truncation bug in `normalize_project_id` should be fixed before merge (it's a 1-line fix) but is not a blocking architecture or security issue. The supervisor validation gap is defense-in-depth; the registry guard is sufficient for MVP.

IMPLEMENTATION_APPROVED
