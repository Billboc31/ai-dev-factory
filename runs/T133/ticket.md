# T133 — T133 — Isolated sandbox deployment runtime

**Source**: GitHub Issue #103

## Description

Add an isolated sandbox deployment runtime for deployer validation workflows.

Scope:
- create isolated deployment sandboxes per ticket/project
- isolated runtime root
- isolated docker compose project names
- isolated env files
- dynamic or offset port allocation
- sandbox lifecycle management
- sandbox logs and status
- dashboard visibility for sandbox state
- cleanup of old sandboxes
- tests for sandbox creation and isolation

Out of scope:
- AI fix loop
- tester agent
- production deployment
- remote deployment
- Kubernetes

Acceptance:
- deployer can create an isolated sandbox runtime
- sandbox does not conflict with main runtime
- ports are isolated
- logs/status are accessible
- cleanup works correctly
- existing runtime remains unaffected
