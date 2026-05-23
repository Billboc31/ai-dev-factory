# T142 — T142 — Sandbox root separation and portable environments

**Source**: GitHub Issue #133

## Description

Goal: fully separate sandbox environments from the main runtime root and make sandbox environments portable across projects.

Context:
T140 introduces isolated runtime roots and supervisors.
T141 introduces full sandbox environments and lifecycle management.

The next step is moving sandbox environments outside the main runtime hierarchy.

Target layout example:

~/runtime/
  ai-dev-factory/
  doc-platform/

~/sandboxes/
  ai-dev-factory/
    sandbox-001/
    sandbox-002/
  doc-platform/
    sandbox-001/

Each sandbox should contain:
- isolated runtime root
- isolated clone or worktree
- isolated env files
- isolated logs and state
- isolated compose project
- isolated supervisor and daemon
- isolated runtime artifacts

Scope:
- add configurable sandbox root outside the main runtime root
- move sandbox runtime state outside the main runtime hierarchy
- support generic project structures
- remove ai-dev-factory-specific sandbox assumptions
- support sandbox-local logs, state and artifacts
- support sandbox-local supervisor and daemon lifecycle
- improve cleanup so deleting a sandbox removes the entire environment safely
- support concurrent sandbox environments across multiple projects
- dashboard must display sandbox root and topology

Out of scope:
- cloud orchestration
- Kubernetes support
- production deployment
- automatic AI self-healing loops

Acceptance:
- sandbox environments no longer depend on the main runtime root
- sandbox runtime state is fully isolated
- sandbox layouts work generically across projects
- deleting a sandbox removes the full environment safely
- multiple projects can own concurrent sandbox environments
- sandbox topology and roots are visible in the dashboard
- the implementation remains reusable and project-agnostic
