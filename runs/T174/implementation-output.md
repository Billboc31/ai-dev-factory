All changes are in place. Here's a summary of what was implemented:

---

## Changes summary

### New files
- **`services/control_api/routes/projects.py`** — `GET /api/projects/{project_id}/branches` endpoint: runs `git branch -a --sort=-committerdate` in the resolved project root, returns up to 100 deduplicated branch names
- **`apps/dashboard/src/api/projects.js`** — `listBranches(projectId)` API helper

### Modified files
- **`services/control_api/routes/environments.py`** — `project_root` is now optional; `project_id` field added; `_resolve_project_root()` helper resolves `project_id → project_root` via the registry (raises `400 "project context missing"` on failure); supervisor path gets the resolved root before proxying
- **`services/control_api/services/environment_provision.py`** — added `project_id` parameter, `_get_repo_url()` helper, and structured log line: `project_id=... repo_url=... branch=... environment=... runtime_root=...`; also updated `provision_environment_from_body` to forward `project_id`
- **`services/control_api/main.py`** — imports and registers `projects.router`
- **`apps/dashboard/src/components/CreateEnvironmentModal.jsx`** — accepts `projectId` prop; in project context: hides `project_root`/`sandbox_path` fields, shows branch combobox (datalist-based with live filtering) defaulting to first branch, environment name suggestions datalist (`main`, ticket ID, sanitized branch, recent names), sends `project_id` in payload; outside project context: unchanged legacy behavior
- **`apps/dashboard/src/pages/EnvironmentsPage.jsx`** — accepts and forwards `projectId` prop to the modal
- **`apps/dashboard/src/App.jsx`** — passes `projectId={activeProject}` to `EnvironmentsPage`
