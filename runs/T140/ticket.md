# T140 — T140 — Isolated sandbox runtimes and supervisors

**Source**: GitHub Issue #130

## Description

Goal: make sandbox deployments fully runtime-isolated.

Current sandbox validation already isolates:
- git worktrees
- docker compose project names
- API and web ports
- sandbox directories

But sandbox web/API instances still connect to the main runtime supervisor and main runtime root.

Result:
- sandbox UI shows main runtime state
- sandbox logs include main supervisor activity
- runtime state is shared

Scope:
- each sandbox gets its own runtime root
- each sandbox gets its own supervisor instance and supervisor port
- sandbox API must use sandbox runtime root and sandbox supervisor URL
- sandbox dashboard must display sandbox runtime state only
- inject sandbox runtime root, supervisor URL and supervisor port into sandbox env/config
- sandbox cleanup must stop sandbox supervisor, stop sandbox compose project and remove sandbox runtime safely
- support multiple concurrent isolated sandboxes
- add tests for isolated runtime roots, isolated supervisors, concurrent sandboxes and cleanup safety

Out of scope:
- AI auto-fix loops
- cloud deployment
- production deployment
- distributed runtime federation

Acceptance:
- sandbox UI no longer displays main runtime state
- sandbox API communicates only with sandbox supervisor
- each sandbox has its own runtime root
- each sandbox has its own supervisor instance
- multiple sandboxes can run simultaneously without collisions
- sandbox cleanup does not affect the main runtime
- logs, state and proposals remain isolated per sandbox runtime
