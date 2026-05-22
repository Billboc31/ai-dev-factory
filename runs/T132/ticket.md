# T132 — T132 — AI-generated operational scripts

**Source**: GitHub Issue #102

## Description

Generate reviewable operational scripts for a managed project using the configured AI runtime.

Scope:
- add a deployer action to generate scripts from scan result, deploy.yml and project files
- generate .ai-dev-factory/scripts/bootstrap.sh
- generate .ai-dev-factory/scripts/build.sh
- generate .ai-dev-factory/scripts/start.sh
- generate .ai-dev-factory/scripts/stop.sh
- generate .ai-dev-factory/scripts/restart.sh
- generate .ai-dev-factory/scripts/healthcheck.sh
- generate/update .ai-dev-factory/deployment.md
- commit generated files to a dedicated branch
- create/update a PR for human review
- show generation status/errors in the dashboard
- add tests with mocked AI/Git/PR calls

Out of scope:
- executing scripts
- sandbox deployment
- healthcheck loop
- tester agent
- auto-merge

Acceptance:
- scripts are generated on a branch
- PR is created or updated
- scripts are executable and documented
- deployment.md explains usage
- existing deployer workflows still work
