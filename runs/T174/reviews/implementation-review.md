Now I have a complete picture of the implementation. Let me write the review.

---

## Implementation Review — T174: Redesign environment creation popup with project-context defaults and autocomplete

### Summary

The implementation covers all ticket requirements. Every acceptance criterion is met. The scope is bounded, the architecture is clean, and no regressions to the legacy flow are introduced.

---

### Acceptance Criteria Verification

| # | Criterion | Status |
|---|-----------|--------|
| 1 | Modal from project page has no `project_root` / `sandbox_path` fields | ✅ `CreateEnvironmentModal.jsx` guards these fields behind `!projectId` |
| 2 | `GET /api/projects/{id}/branches` returns a JSON array | ✅ `routes/projects.py` — runs `git branch -a`, deduplicates, limits to 100 |
| 3 | Branch combobox filters as user types | ✅ `<input list="branch-list">` + `<datalist>` provides native filtering |
| 4 | Environment name shows ≥2 suggestions | ✅ `buildNameSuggestions` adds `main`, ticket ID, sanitized branch, recent names |
| 5 | Project context POST sends `project_id`, not `project_root` | ✅ `submit()` builds correct payload per mode |
| 6 | Invalid `project_id` returns 400 "project context missing" | ✅ `_resolve_project_root` raises `HTTPException(400, "project context missing")` |
| 7 | Deploy logs show resolved project/repo/branch/env/runtime | ✅ `provision_environment` logs all five fields |
| 8 | Non-project context still shows `project_root` field | ✅ Legacy branch rendered when `projectId` is falsy |

---

### Correctness

**Backend — `_resolve_project_root` (`environments.py:84`)**: Logic is sound. Falls back correctly: explicit `project_root` wins, then `project_id` → registry lookup, then 400. The empty-string case is handled by Python truthiness.

**Backend — supervisor path**: `body.model_dump(mode="json")` includes `project_id` and the resolved root is injected at `payload["project_root"]`. The supervisor's `provision_environment_from_body` correctly reads both. No double-resolution.

**Backend — `projects.py` `_list_branches`**: Uses `--format=%(refname:short)` which already strips the `remotes/origin/` prefix for remote refs at the git level. The manual prefix-strip loop on lines 28–31 is redundant but harmless. The `HEAD`/`->` filter is correct.

**Frontend — `activeProject` is project name = registry `entry.id`**: `App.jsx` sets `activeProject = projects[0].name` → `ProjectInfo.name` = `entry.id` = `subdir.name`. The registry's `resolve(project_id)` matches on `entry.id`. These are consistent — the `projectId` prop carries the correct identifier.

**Frontend — `handleRefChange` inference**: `branches.includes(ref)` is evaluated at the moment the user changes the input, so `ref_type` is set to `'branch'` only when an exact branch name is typed or selected. Correct.

---

### Minor Observations (non-blocking)

1. **`_list_branches` ignores `result.returncode`** (`projects.py:15`): If `git` exits non-zero (e.g., corrupted repo), the function returns an empty list silently. The registry already guarantees `.git/` exists, so this is low-risk, but a non-zero exit code would produce a misleading 200 with `[]` instead of a 500.

2. **Branch fetch errors swallowed silently** (`CreateEnvironmentModal.jsx:71`): The `.catch(() => {})` leaves the branch input empty with no user feedback. A brief error note ("Could not load branches") would improve debuggability. Not blocking.

3. **`activeProject` is `null` before projects load**: The modal can open in legacy mode during the initial project fetch. The form degrades gracefully, but a user who is very fast might see the wrong form briefly.

4. **`_resolve_project_root` when registry is absent**: If `app.state.project_registry` doesn't exist (non-standard deployment), a `project_id` lookup silently falls through to the 400. In practice, `create_app` always sets the registry, so this is purely theoretical.

None of these observations affect correctness or the specified acceptance criteria.

---

### Scope Compliance

No drift detected. The implementation touches exactly the files listed in the plan. Nothing outside the plan is modified. The legacy flow is preserved. No new dependencies were introduced.

---

### Security

- `subprocess.run` in `_list_branches` uses a fixed arg list (`["git", "branch", ...]`) with `cwd=project_root` resolved from the registry — no injection surface.
- No filesystem paths are exposed in the UI when `projectId` is set.
- Repository is not derived from shell CWD.
- Silent fallback to a different repository is impossible — resolution raises 400 on any failure.

---

IMPLEMENTATION_APPROVED
