# T129 — T129 — Deployer execution and healthchecks

**Source**: GitHub Issue #95

## Description

Continue T127 deployer work by adding real deployment execution from deploy.yml.

Scope:
- load deploy profile
- run deploy steps from Python
- add deploy and restart API actions
- add deployment status and logs
- add healthchecks
- add one-deploy-at-a-time lock per project
- show deploy/restart/logs in the dashboard
- add tests for success, failure, logs and locking

Out of scope:
- Claude profile generation
- installing missing tools
- remote or cloud deployment
- Kubernetes
- secrets management
- automatic deploy after merge

Acceptance:
- deploy API can run a valid project deploy
- status shows running, success or failed
- logs are visible in API and dashboard
- failed steps return useful errors
- healthcheck failure fails the deploy
- concurrent deploy request is rejected clearly
- existing ticket runtime workflow still works
