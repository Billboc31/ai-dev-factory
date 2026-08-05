# PLAN_FIX_REQUIRED

## Review

Plan review 02 for T227.

## Summary

The regenerated plan resolves the first review's repository, branch, configuration, asynchronous execution, locking, and test-coverage requirements. Three integration and failure-state corrections remain required before implementation.

## Required fixes

### 1. Add the deployment-status proxy to the Control API

The dashboard calls:

```text
GET /api/projects/{project_id}/workspace/deployments/{deployment_id}
```

and the Supervisor exposes:

```text
GET /workspace/projects/{project_id}/deployments/{deployment_id}
```

The regenerated plan must modify `services/control_api/routes/workspace.py` to add:

```text
GET /projects/{project_id}/workspace/deployments/{deployment_id}
```

This route must validate the project through the existing dependency and forward the GET request to the Supervisor while preserving its response status and JSON body.

Without this proxy, frontend polling will return 404.

### 2. Preserve HTTP 409 responses through the Control API

The current Control API forwarding helper explicitly raises only for selected 4xx statuses and for 5xx responses. A Supervisor `409 Conflict` may therefore be returned by the Control API as HTTP 200 with a `detail` body.

The plan must update the workspace proxy so every Supervisor response with `status_code >= 400` is propagated with the original status, including:

- 409 when another deployment is already running;
- 404 for an unknown deployment;
- other validation or execution errors.

Add a test proving that a Supervisor 409 remains a Control API 409.

### 3. Guarantee a terminal job state on timeouts and exceptions

Releasing the per-project lock in `finally` is necessary but insufficient. If `_run_redeploy_job` raises, the daemon thread may terminate while the job remains permanently `RUNNING`.

The regenerated plan must define a top-level exception boundary around the complete background job and ensure all non-success paths write a terminal job state:

- `status = "FAILED"`;
- `completed_at` set;
- `error_stage` set to the active stage or a safe internal stage;
- `error_excerpt` set to a sanitized, bounded message;
- lock released in `finally`.

Handle at least:

- `subprocess.TimeoutExpired`;
- `FileNotFoundError`;
- missing or invalid configuration;
- missing repository path or non-Git repository;
- unexpected exceptions.

Add tests verifying both the released lock and the persisted `FAILED` state for timeout and unexpected-exception paths.

## Preserved requirements

The next plan must preserve all corrections already integrated from plan review 01:

- fresh dirty check after confirmation;
- configured-branch enforcement;
- no LLM/frontend-controlled executable branch, path, service, or command;
- background deployment job and polling;
- safe project identifier in the confirmation card;
- HTTP 409 for concurrent deployment;
- unconditional lock release;
- backend and frontend security/concurrency tests.

## Decision

PLAN_FIX_REQUIRED
