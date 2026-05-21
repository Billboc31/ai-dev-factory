# Plan fix request — T127

The current deployer plan is promising but too large for one safe ticket.

Please reduce T127 to a smaller V1.

## T127 V1 objective

Introduce a minimal deployer foundation:
- deploy profile format
- project scanner
- read-only deployer status page
- no real deployment execution yet

## Include in V1

- Define `.ai-dev-factory/deploy.yml` schema.
- Add `.ai-dev-factory/deploy.yml` for ai-dev-factory.
- Add project scanner service.
- Add `GET /projects/{id}/deployer/status`.
- Add `POST /projects/{id}/deployer/scan`.
- Add minimal `DeployerPage` with:
  - Scan Project button
  - status display
  - detected components/tools display
- Add tests for:
  - scanner
  - deploy profile loading
  - deployer status route

## Exclude from V1

- No real deploy execution.
- No restart execution.
- No subprocess orchestration.
- No Claude profile generation.
- No deployment logs JSONL.
- No concurrent deployment locking.
- No branch deployment.
- No healthcheck execution.
- No host process management.

## Follow-up tickets

Later tickets can introduce:
- deploy execution
- restart execution
- healthchecks
- deployment logs
- Claude-assisted profile generation
- deploy orchestration
- environment bootstrap/install

## Acceptance criteria for fixed plan

- ai-dev-factory contains a valid `.ai-dev-factory/deploy.yml`.
- Scanner detects docker services and required tools.
- `/projects/{id}/deployer/status` returns a valid idle status.
- `/projects/{id}/deployer/scan` returns detected components.
- Dashboard deployer page loads successfully.
- Existing dashboard/runtime workflows are not broken.
