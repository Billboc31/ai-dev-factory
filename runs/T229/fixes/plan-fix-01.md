# Plan Fix Instructions — T229

Revise `runs/T229/plan.md` to incorporate all blocking points from `runs/T229/reviews/plan-review-01.md`.

## Required changes

1. Replace free-form `deploy.command` / shell-style `healthcheck` execution with a declarative, server-controlled deployment model. Prefer structured fields such as deployment type, repository-relative compose/script selection, `preview_url`, and `healthcheck_url`. Do not allow frontend/LLM-supplied shell commands or arbitrary filesystem paths. If custom scripts are supported, constrain them to validated repository-relative files and execute without `shell=True`.

2. Define deployability explicitly. Do not treat the mere existence of `docker-compose.yml` as sufficient. Specify source-of-truth precedence, preferably explicit project `deploy` config first, with only a conservative documented fallback if retained.

3. Define persistent deployment history correctly. Use either separate latest-state/history files or one bounded structure containing both. The history endpoint must deterministically return the last five deployment records, and writes must not corrupt previous history.

4. Add atomic per-project concurrency protection. Only one deployment may be active per project. A concurrent POST must return HTTP 409 `DEPLOYMENT_IN_PROGRESS`. Register/check under a lock and guarantee cleanup in `finally` after success, failure, timeout, or unexpected exception.

5. Capture `git rev-parse HEAD` before deployment and persist it as `deployed_sha`. Explicitly define the working-tree dirty policy; default to refusing dirty deployments unless a project-level option deliberately allows them.

6. Define a deployment job/session registry with stable `deployment_id`, `project_id`, `stage`, `status`, timestamps, SHA, bounded log tail, preview URL, and error. Polling must verify that the deployment belongs to the project in the route.

7. Make healthcheck part of success semantics. Define deployment stages such as `BUILDING`, `STARTING`, `HEALTHCHECK`, then `SUCCEEDED`/`FAILED`. If configured, healthcheck failure or timeout must make the deployment fail even if the build/start command succeeded. Specify timeout/retry/interval behaviour.

8. Bound deployment logs. Keep the polling tail to the last 50 lines, define persistent log retention/rotation, and avoid exposing obvious secrets in dashboard-visible logs.

9. Add explicit backend and frontend tests for all of the above, including 422 non-deployable/invalid config, 409 concurrency, lock release on exception, dirty-tree policy, SHA capture, unsafe config rejection, healthcheck success/failure/timeout, five-entry history retention, cross-project deployment-id rejection, bounded logs, retry after terminal state, and dashboard behaviour.

## Preserve

Keep the good parts of the current plan:

- workspace project deployment remains separate from AI Dev Factory's own deployer;
- T227 redeploy behaviour is not changed;
- execution remains asynchronous with polling;
- production/cloud/Kubernetes/rollback/multi-environment features remain out of scope;
- the dashboard exposes a one-click action, progress, logs, retry, and preview URL.

## Expected result

Rewrite `runs/T229/plan.md` with a materially revised plan that incorporates these constraints and includes verifiable acceptance criteria and tests. Do not merely describe these requested fixes in prose outside the plan.
