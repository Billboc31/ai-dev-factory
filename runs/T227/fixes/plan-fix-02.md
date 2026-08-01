# Plan fix 02

## Ticket

T227 — Add pull and local backend/frontend redeployment action to AI Workspace

## Source review

`runs/T227/reviews/plan-review-02.md`

## Decision

PLAN_FIX_REQUIRED

## Required plan corrections

### 1. Add the Control API polling route

Modify `services/control_api/routes/workspace.py` to expose:

```text
GET /projects/{project_id}/workspace/deployments/{deployment_id}
```

The route must:

- use the existing project-resolution dependency;
- forward to Supervisor endpoint `GET /workspace/projects/{project_id}/deployments/{deployment_id}`;
- preserve the Supervisor HTTP status and JSON response;
- return 404 for an unknown deployment or project mismatch.

Update `apps/dashboard/src/api/workspace.js` to call this Control API route consistently.

### 2. Propagate every Supervisor error status, including 409

Update the workspace proxy forwarding logic so any Supervisor response with `status_code >= 400` is returned or raised with the original HTTP status.

In particular, concurrent redeployment must remain:

```text
409 Conflict
```

from Supervisor through Control API to the dashboard. It must not become HTTP 200 with a `detail` field.

Add Control API tests for:

- Supervisor 409 → Control API 409;
- Supervisor 404 → Control API 404;
- successful polling response → Control API 200 with unchanged job state.

### 3. Persist FAILED for every background-job failure

Wrap the complete `_run_redeploy_job` body with a top-level exception boundary.

For every timeout, configuration failure, filesystem/Git error, missing executable, or unexpected exception, update the deployment job under `_deployment_jobs_lock` with:

```python
{
    "status": "FAILED",
    "completed_at": <utc timestamp>,
    "error_stage": <current or safe failure stage>,
    "error_excerpt": <sanitized message, maximum 500 characters>,
}
```

Requirements:

- never leave a terminated job in `RUNNING`;
- handle `subprocess.TimeoutExpired` explicitly;
- handle `FileNotFoundError` explicitly;
- handle invalid/missing project configuration;
- handle missing or non-Git repository paths;
- catch unexpected exceptions, log the full server-side exception, and expose only a sanitized bounded excerpt;
- release the project lock unconditionally in `finally`.

Add tests proving that:

- Git timeout produces `FAILED` and releases the lock;
- Docker timeout produces `FAILED` and releases the lock;
- unexpected exception produces `FAILED` and releases the lock;
- missing executable produces `FAILED`;
- frontend polling stops on each resulting `FAILED` response.

## Requirements to preserve

Do not regress the corrections already present in the current plan:

- execution-time configuration reload;
- configured branch only;
- execution-time branch and dirty checks;
- safe pending-action metadata;
- background job returning immediately;
- per-project conflict locking;
- no host paths in the UI;
- frontend submits only the opaque `action_id`;
- existing capability behavior remains unchanged.

## Expected output

Regenerate `runs/T227/plan.md` with these corrections. Do not implement source code as part of the plan-fix step.
