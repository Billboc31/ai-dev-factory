# T151 — T151 — Deployment environments dashboard

**Source**: GitHub Issue #149

## Description

Goal: replace the current sandbox-oriented deployment UI with a full deployment environments dashboard supporting branches, persistent environments and deployment lifecycle management.

Context:
The current sandbox UI is still highly technical and runtime-oriented:
- ticket-centric
- manual runtime paths
- sandbox-focused terminology
- limited deployment targeting

As the runtime/deployer stack matures, the product now needs a real environments and deployments experience.

Target examples:
- main
- develop
- integration
- preview
- sandbox
- feature branch deployments
- PR deployments

Scope:
- introduce a dedicated Environments / Deployments page in the dashboard
- support deploying arbitrary refs:
  - branches
  - tags
  - PR refs
  - commits
- support named environments:
  - main
  - develop
  - integration
  - preview
  - sandbox
  - custom
- support deployment modes:
  - Deploy & Test
  - Persistent Environment
- display:
  - deployment status
  - lifecycle state
  - URLs
  - health state
  - branch/ref
  - runtime logs
  - deployment timestamps
- allow:
  - deploy
  - redeploy
  - stop
  - delete
  - refresh
  - open URLs
- support concurrent environments for the same project
- keep environment/deployment concepts generic and project-agnostic
- integrate with isolated runtime roots, supervisor/daemon lifecycle and proxy URLs

Potential future directions:
- environment templates
- automatic preview deployments per PR
- deployment history
- environment snapshots
- environment pinning
- deployment rollback

Tests:
- deploy branch environment
- deploy persistent environment
- concurrent environment deployments
- environment deletion cleanup
- branch/ref display correctness
- environment lifecycle transitions
- dashboard action idempotency

Out of scope:
- Kubernetes
- production rollout orchestration
- cloud deployment
- GitHub Actions integration
- authentication/permissions
- distributed deployment scheduling

Acceptance:
- dashboard exposes a full Environments / Deployments page
- users can deploy arbitrary refs and branches
- users can manage persistent environments from the UI
- multiple environments can coexist simultaneously
- environments expose URLs and lifecycle state clearly
- deployment actions are idempotent
- implementation remains generic and project-agnostic
