# PLAN_FIX_REQUIRED

## Summary

The deployment plan is directionally correct, but several issues must be fixed before implementation because they affect execution safety, concurrency, deployment correctness, history persistence, and end-to-end validation semantics.

## Blocking issues

### 1. Do not execute free-form shell commands from deploy config

The proposed schema allows arbitrary values such as:

```yaml
deploy:
  command: docker compose up -d --build
  healthcheck: curl -sf http://localhost:3000/health
```

This must not become `shell=True` or equivalent free-form command execution.

Prefer a declarative deployment configuration, for example:

```yaml
deploy:
  type: docker-compose
  compose_file: docker-compose.yml
  preview_url: http://localhost:3000
  healthcheck_url: http://localhost:3000/health
```

If custom scripts are supported, they must be repository-relative, validated after path normalization, already present in the repository, and executed without `shell=True`. Frontend or LLM input must never provide arbitrary command strings, paths, service names, or shell arguments.

### 2. `docker-compose.yml` presence alone must not imply deployability

A repository containing a compose file is not automatically safe or meaningful to deploy. Define an explicit deployment policy and precedence. Prefer an explicit `deploy` config as the source of truth, with any compose auto-detection limited to a conservative documented fallback.

### 3. Deployment history needs a real persistence model

`project-deploy-state.json` cannot simultaneously represent only the latest state and also provide the last five deployment records unless its schema explicitly contains history.

Define either:

- separate `project-deploy-state.json` and `project-deploy-history.json`, or
- one structured document containing `latest` plus bounded `history`.

Retention and atomic writes must be defined.

### 4. Add atomic per-project deployment concurrency protection

Only one deployment may run per project at a time. A second POST while one is active must return HTTP 409 with a structured `DEPLOYMENT_IN_PROGRESS` response. The check-and-register operation must be atomic and cleanup must happen in `finally`, including after exceptions or timeouts.

### 5. Define deployed SHA and dirty-working-tree policy

Capture `git rev-parse HEAD` before starting the deployment and attach it to the deployment record. Define what happens when the working tree is dirty. The plan should reject dirty deployments by default unless an explicit project-level policy allows them.

### 6. Define the deployment job registry contract

Each job should have a stable `deployment_id` and server-side state containing at least:

- `deployment_id`
- `project_id`
- `stage`
- `status`
- `started_at`
- `completed_at`
- `deployed_sha`
- `log_tail`
- `preview_url`
- `error`

Polling must validate that a deployment belongs to the requested `project_id`.

### 7. Healthcheck must be part of deployment success

A successful build/start command alone is not sufficient for an end-to-end validation deployment. Define stages such as:

`BUILDING -> STARTING -> HEALTHCHECK -> SUCCEEDED`

If a healthcheck is configured, the deployment must only become `succeeded` after it passes. Define timeout, retry interval, retry count, and clear failure reporting.

### 8. Bound and sanitize deployment logs

Do not keep unlimited stdout/stderr in memory or return unbounded logs through polling. Keep only a bounded tail in memory (at least the acceptance-criterion 50 lines), define file rotation/retention, and redact obvious secret values before exposing logs in the dashboard.

## Required tests

Add tests covering at minimum:

- no deploy config -> 422 `not_deployable`;
- invalid deploy config -> explicit 422;
- concurrent deployment -> second request returns 409;
- per-project lock/session released after exception;
- deployed SHA captured before launch;
- dirty repository follows the chosen policy;
- arbitrary command/script/path/service values are rejected;
- successful healthcheck;
- deploy command success + healthcheck failure -> failed;
- healthcheck timeout -> failed;
- history retains and returns the last five deployments;
- deployment ID cannot be queried under another project;
- polling `log_tail` is bounded to 50 lines;
- retry is allowed after a terminal state;
- frontend disables/restricts duplicate deploy while active;
- frontend displays preview URL only after success;
- frontend renders `not_deployable` cleanly.

## Decision

PLAN_FIX_REQUIRED
