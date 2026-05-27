# T153 — T153 — Generic smoke tests and bounded auto-fix deployment loop

**Source**: GitHub Issue #158

## Description

Goal: make the Deployer able to converge toward a functional ephemeral environment by running healthchecks, smoke tests, and a bounded AI auto-fix loop.

Context:
The intended Deployer flow is not just `docker compose up`.

Expected Deployer role:
- audit the project
- generate/update deployment scripts
- deploy an ephemeral sandbox environment
- run healthchecks
- run real smoke tests
- if validation fails, ask the configured AI runtime to propose/apply safe fixes
- redeploy and retest
- repeat until success or retry limit
- cleanup/undeploy automatically after success

Current limitation:
- we mostly have healthchecks today
- healthchecks only prove that services respond
- they do not prove that the application actually works
- auto-fixing only against healthchecks risks optimizing for "starts" rather than "works"

Scope:

1. Generic smoke test layer
- define a generic smoke test lifecycle after healthcheck
- support generated project-specific smoke tests
- prefer `.ai-dev-factory/scripts/smoke.sh` or equivalent lifecycle declaration
- smoke tests must use sandbox/proxy URLs when available
- fallback to allocated direct ports only when proxy URLs are absent
- smoke test output must be captured in logs and state

2. Deployer validation pipeline
- deploy ephemeral sandbox
- run healthcheck
- run smoke tests
- collect result state:
  - health status
  - smoke test status
  - failing step
  - logs
  - generated artifacts

3. Bounded AI auto-fix loop
- on failure, collect context and call the configured AI runtime
- no hardcoded provider or Claude-specific SDK
- use existing exec_cmd / AI runtime abstraction
- restrict modifications to allowed deployment artifacts first:
  - `.ai-dev-factory/scripts/*`
  - deploy profile files
  - compose/env/deployment config files explicitly allowed by policy
- apply patch in sandbox/worktree only
- redeploy and retest
- repeat up to configurable max retries
- stop if the same failure repeats without progress
- persist iteration history

4. Safety and observability
- max retry limit required
- each iteration records:
  - failure reason
  - changed files
  - patch summary
  - health result
  - smoke result
  - logs
- never merge automatically
- never modify unrelated application source files in this first version
- final diff must be visible and reviewable

5. Cleanup
- on success, undeploy/cleanup ephemeral validation environment
- on terminal failure, preserve logs/state/artifacts for inspection

Out of scope:
- production deployment
- cloud deployment
- automatic merge to main
- full tester-agent business/UAT tests
- modifying arbitrary product code
- persistent environment management

Acceptance:
- Deployer can run healthcheck plus smoke tests
- smoke tests are clearly distinguished from healthchecks in state/UI
- Deployer can run a bounded auto-fix loop after failures
- AI fixes are constrained to allowed deployment artifacts
- every iteration is persisted and observable
- successful loop ends with a functional ephemeral environment and cleanup
- failed loop ends cleanly with logs and iteration history
- no provider-specific AI SDK is hardcoded
- implementation remains generic and project-agnostic
