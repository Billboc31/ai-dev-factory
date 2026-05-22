# T136 — T136 — Deploy sandbox isolation and runtime separation

**Source**: GitHub Issue #109

## Description

Continue T135 after the isolation V1 by introducing fully isolated deploy sandbox runtimes.

Scope:
- isolated deploy worktrees for script generation and deploy validation
- isolated compose project names
- isolated env files
- isolated runtime directories per deploy job
- dynamic or reserved sandbox ports
- deploy sandbox lifecycle management
- sandbox cleanup after completion/failure
- dashboard visibility for sandbox runtime state
- tests for sandbox isolation and concurrent deploy jobs

Out of scope:
- deploy/test/fix retry loop
- tester agent
- production deployment
- remote/cloud deployment
- Kubernetes

Acceptance:
- deploy validation jobs never use the main runtime worktree
- multiple sandbox deploys can run concurrently without conflicts
- compose projects, ports and env files are isolated per sandbox
- cleanup removes sandbox resources correctly
- existing analysis/runtime workflows continue to work
