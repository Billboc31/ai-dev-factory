# T137 — T137 — Sandbox isolated ports and UI management

**Source**: GitHub Issue #123

## Description

Goal: improve sandbox deploy validation with isolated ports, sandbox env files, and dashboard management.

Context:
The sandbox runner now works host-side and executes scripts. The first real run failed because the sandbox reused the main runtime ports: supervisor 8090 and API 8080. The sandbox also needs its own deploy env file.

Scope:
- create a sandbox-specific deploy env file in each sandbox worktree
- include sandbox runtime root, project root, supervisor port, API port, web port, compose project name and sandbox id
- allocate ports that do not collide with the main runtime
- persist allocated ports in sandbox state
- run docker compose with a sandbox-specific project name
- list sandbox runs in the dashboard
- show sandbox id, project id, state, timestamps, last step, ports, worktree path and logs
- add refresh, view logs and cleanup actions
- cleanup removes only the selected sandbox worktree and sandbox directory
- cleanup must not affect the main runtime

Out of scope:
- AI fix loop
- tester agent
- cloud or remote deployment
- automatic merge

Acceptance:
- sandbox validation no longer conflicts with main ports
- every sandbox has its own env file
- every sandbox uses a unique compose project name
- ports are visible in UI and logs
- historical sandboxes are visible in UI
- cleanup works safely
- existing sandbox validation still works
