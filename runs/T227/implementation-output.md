All tests pass. Here's a summary of what was implemented for T227:

## Implementation Summary

The full feature was already implemented across previous attempts. The only missing piece was the frontend test file, which I created.

### Files modified or created

| File | Status |
|------|--------|
| `services/supervisor/workspace_projects.yml` | Created — empty projects config (loaded at runtime) |
| `services/supervisor/workspace_projects.example.yml` | Created — annotated schema documentation |
| `services/supervisor/main.py` | Modified — added: `_workspace_redeploy_locks`, `_deployment_jobs`, `_load_workspace_projects_config()`, `_git_has_local_changes()`, `_get_redeploy_lock()`, `redeploy_project` capability in `_WORKSPACE_CAPABILITIES` and `_WORKSPACE_SYSTEM_PROMPT`, proposal-time validation in `workspace_chat()`, background-job branch in `workspace_action_confirm()`, `_run_redeploy_job()`, `GET /workspace/projects/{project_id}/deployments/{deployment_id}` |
| `services/control_api/routes/workspace.py` | Already had `GET /projects/{project_id}/workspace/deployments/{deployment_id}` and correct 4xx passthrough |
| `apps/dashboard/src/api/workspace.js` | Already had `getDeploymentStatus()` |
| `apps/dashboard/src/components/ProjectWorkspacePanel.jsx` | Already had redeploy confirmation card, dirty warning, and polling loop |
| `tests/supervisor/test_workspace_redeploy.py` | Already complete — 34 tests |
| `tests/control_api/test_workspace_redeploy_proxy.py` | Already complete — 4 tests |
| `apps/dashboard/tests/ProjectWorkspacePanel.test.jsx` | **Created** — 8 frontend tests |

### Test results
- **Python**: 38/38 pass
- **Frontend**: 8/8 pass
