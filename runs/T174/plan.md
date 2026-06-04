Now I have a clear picture of the codebase. Let me produce the plan.

## Objective

Redesign the environment creation modal so that, when opened from a project page, it automatically reuses project metadata, removes the manual `project_root` field, and provides branch/name autocomplete — reducing user error and simplifying the flow.

## Included

### Backend

**New endpoint — branch listing**
- `GET /api/projects/{project_id}/branches` in `services/control_api/routes/projects.py`
- Runs `git branch -a --sort=-committerdate` inside the resolved project root
- Returns a JSON list of branch names (local + remote), deduplicated and stripped of `remotes/origin/` prefix
- Limit to 100 results; no auth required beyond existing session

**Loosen `CreateEnvironmentRequest`**
- `services/control_api/routes/environments.py`: make `project_root` optional (`str | None = None`)
- Add optional `project_id: str | None = None`
- `services/control_api/services/environment_provision.py`: if `project_root` is absent, resolve it from `project_id` via `ProjectRegistry`; if resolution fails, raise `400` with message `"project context missing"`

**Deploy log enrichment**
- `services/control_api/services/environment_provision.py`: at provision start, emit structured log lines:
  ```
  project_id=<resolved> repo_url=<resolved> branch=<ref> environment=<env_name> runtime_root=<resolved>
  ```

### Frontend

**New API helper**
- `apps/dashboard/src/api/projects.js`: add `listBranches(projectId)` → `GET /api/projects/{projectId}/branches`

**`CreateEnvironmentModal` refactor** (`apps/dashboard/src/components/CreateEnvironmentModal.jsx`)
- Accept optional `projectId` prop
- When `projectId` is present:
  - Remove `project_root` field entirely from the form
  - Remove `sandbox_path` field (internal detail)
  - Send `project_id` instead of `project_root` in the POST payload
- **Branch autocomplete**: replace the `ref` free-text input + `ref_type` dropdown with a combobox that:
  - Fetches from `listBranches(projectId)` on mount
  - Filters as user types
  - Defaults to current branch (if detectable via `/api/projects/{id}` metadata) or first result
  - `ref_type` is inferred as `branch` when a branch is selected; remains a dropdown for `tag`/`commit`/`pr_ref` via an "advanced" toggle
- **Environment name suggestions**: show a datalist/dropdown with precomputed options: `main`, current ticket id (extracted from branch name if `ticket/TXXX-*`), sanitized branch name, up to 3 recent environment names (from existing `listEnvironments()` response)
- When `projectId` is absent (modal opened outside project context): behavior unchanged — `project_root` field remains

**`ProjectPage` or equivalent** — pass `projectId` prop when opening the modal from a project page. (Identify the trigger call site and add the prop; no page refactor.)

### Tests / validation

- No new test files required; existing test coverage is outside scope for this ticket
- Manual acceptance path: open modal from project page → verify no `project_root` field, branch list populated, name suggestions present, deploy log shows resolved metadata

## Excluded

- Changes to the environment card display or environment list page
- Multi-project support (selecting a different project from within the modal)
- GitHub PR ref autocomplete (only local+remote git branches)
- Modifying the `ref_type` logic for `tag`, `commit`, or `pr_ref` flows
- Authentication or permission changes
- Any database migration or persistent storage changes
- Moving existing environments between projects
- Changes to the supervisor provisioning protocol

## Acceptance criteria

1. Opening the modal from a project page renders no `project_root` field and no `sandbox_path` field.
2. `GET /api/projects/{project_id}/branches` returns a non-empty JSON array when the project has git branches.
3. The branch combobox filters the branch list as the user types.
4. The environment name field displays at least two name suggestions derived from the branch name or ticket ID.
5. Submitting the form from a project context sends `project_id` (not `project_root`) in the POST body, and the backend creates the environment successfully.
6. If `project_id` is invalid or missing from the registry, the API returns `400` with the body containing `"project context missing"`.
7. Environment provisioning logs include the resolved `project_id`, `repo_url`, `branch`, `environment`, and `runtime_root` lines.
8. Opening the modal from a non-project context (e.g., the global environments page) still shows the `project_root` field and behaves as before.
