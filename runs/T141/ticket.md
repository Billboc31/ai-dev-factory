# T141 — T141 — Full sandbox environments and lifecycle management

**Source**: GitHub Issue #131

## Description

Goal: make each sandbox a complete isolated runtime environment with full lifecycle management.

Context:
T140 introduces isolated runtime roots and isolated supervisors.

The next step is making a sandbox behave like a full independent environment containing all required runtime components for a project.

A sandbox should not only expose isolated API/web ports. It should represent a complete runnable project environment.

Scope:
- sandbox environments must support full runtime component topology
- sandbox deploy profiles must declare runtime components generically
- sandbox startup must start all declared components
- support components such as:
  - api
  - web
  - supervisor
  - daemon
  - workers
  - databases
  - redis
  - custom services
- sandbox dashboard must display runtime components and component states
- add sandbox lifecycle actions:
  - start
  - stop
  - restart
  - cleanup/delete
  - refresh state
- stopping a sandbox must:
  - stop compose services
  - stop supervisor
  - stop daemon/workers
  - release ports
  - clean locks and pid files safely
- cleanup must preserve optional logs/state artifacts when configured
- sandbox dashboard must display:
  - sandbox URLs
  - runtime root
  - allocated ports
  - component health
  - running/stopped state
  - uptime
- support multiple concurrent sandbox environments safely
- runtime topology must remain generic and not ai-dev-factory specific

Out of scope:
- distributed orchestration
- Kubernetes support
- cloud deployment
- production deployment
- automatic AI self-healing loops

Acceptance:
- a sandbox represents a full isolated runtime environment
- sandbox lifecycle actions work safely
- all runtime components stop correctly on sandbox shutdown
- ports and locks are released correctly
- dashboard displays sandbox runtime topology and state
- multiple sandbox environments can coexist safely
- the implementation remains generic and reusable across projects
