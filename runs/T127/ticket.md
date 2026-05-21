# T127 — T127 — Project deployer profiles and dashboard deployment actions

**Source**: GitHub Issue #93

## Description

# Objective

Introduce a generic project deployer system able to analyze a project, generate a deployment profile, and expose deployment actions in the dashboard.

## Included

- Add a project scanner flow from the dashboard.
- Add a deploy profile format, for example:
  - `.ai-dev-factory/deploy.yml`
- Add a deploy profile generator using Claude-assisted analysis.
- Detect:
  - docker services
  - frontend/backend stacks
  - build commands
  - healthchecks
  - required host tools
  - daemon host-side requirements
- Support host-side and docker-based runtime components.
- Add dashboard actions:
  - Scan project
  - Generate deploy profile
  - Deploy main
  - Deploy current branch
  - Restart services
  - View deployment logs
- Add deterministic Python deployment execution.
- Add deployment logs and deployment status tracking.
- Add healthcheck verification after deployment.
- Support ai-dev-factory as the first deployer-enabled project.

## Excluded

- Kubernetes orchestration.
- Cloud autoscaling.
- Multi-host deployment.
- Production secret management.
- SaaS billing.
- Full CI/CD replacement.

## Acceptance criteria

- A project can be scanned from the dashboard.
- A deploy profile is generated and stored in the target project.
- Dashboard shows deployment actions for deployer-enabled projects.
- Deploy actions execute deterministic Python deployment steps.
- Deployment logs are visible from the dashboard.
- Healthchecks run after deployment.
- ai-dev-factory deployment profile supports:
  - docker services
  - host-side daemon
  - gh dependency
  - Claude dependency
- Deployment failures return structured errors instead of silent failures.
