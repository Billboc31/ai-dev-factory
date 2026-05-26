# T147 — T147 — Sandbox daemon isolation

**Source**: GitHub Issue #142

## Description

Goal: isolate sandbox daemons from the main runtime.

Context:
Sandbox API and web instances can run on isolated ports, but daemon lifecycle still depends on the main runtime and manual host commands.

Scope:
- each sandbox runs its own daemon instance
- sandbox daemon uses sandbox runtime root only
- sandbox daemon communicates only with sandbox supervisor
- sandbox daemon ports are sandbox-specific
- sandbox API and dashboard start and stop the daemon through the sandbox supervisor
- no manual host command required
- sandbox daemon logs, state and pid files remain isolated
- cleanup stops sandbox daemon safely without affecting the main daemon
- support multiple concurrent sandbox daemons

Tests:
- isolated daemon startup
- isolated daemon shutdown
- concurrent sandbox daemons
- sandbox runtime root isolation
- cleanup safety

Out of scope:
- AI auto-fix loops
- cloud deployment

Acceptance:
- sandbox daemon no longer requires manual host commands
- each sandbox has its own daemon instance
- sandbox daemon uses sandbox runtime root only
- multiple sandbox daemons can run simultaneously
- sandbox cleanup does not affect the main daemon
- implementation remains generic and project-agnostic
