# T134 — T134 — Deploy and healthcheck fix loop in sandbox

**Source**: GitHub Issue #104

## Description

Add a deploy/test/fix loop inside isolated deployment sandboxes.

Scope:
- execute generated deployment scripts inside sandbox runtime
- run healthcheck.sh after deployment
- capture deployment and healthcheck logs
- detect deployment failures
- send failures/logs back to the configured AI runtime
- allow the AI runtime to update generated scripts and deployment files
- retry deployment after fixes
- configurable retry limit
- update PR branch with fixes
- dashboard visibility for deploy/test/fix iterations
- tests for deploy failure and retry loop

Out of scope:
- tester agent
- production deployment
- remote/cloud deployment
- auto-merge to main
- full E2E business testing

Acceptance:
- sandbox deploy loop can detect a failed deployment
- AI runtime can update scripts after a failed deployment
- deployment retries are visible in the dashboard
- successful healthcheck marks sandbox deploy as healthy
- retry limit stops infinite loops
- main runtime is never impacted by sandbox failures
