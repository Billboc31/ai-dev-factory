# T128 — T128 — Host supervisor for daemon and deployment jobs

**Source**: GitHub Issue #94

## Description

# Objective

Introduce a host-side supervisor process that the Docker dashboard/control API can call to start, stop, monitor and manage host-level AI runtime jobs.

This solves the architecture problem where Docker cannot safely run host-dependent processes such as the coding daemon or deployment jobs that require host Git, worktrees, Docker, GitHub CLI, Claude CLI and local credentials.

## Included

- Add a host supervisor service/process for ai-dev-factory.
- The supervisor runs on the host machine, not inside Docker.
- Expose a minimal local API or command bridge for the Docker control API to call.
- Support starting/stopping/status/logs for:
  - coding daemon
  - future deployer jobs
  - future mapper daemon
  - future guardian daemon
- Use the host Python venv and canonical runtime root.
- Validate host dependencies:
  - git
  - gh
  - Claude CLI
  - Docker CLI
  - project repo/worktrees
- Track job state:
  - job id
  - type
  - pid
  - status
  - started_at
  - finished_at
  - exit_code
  - log path
- Ensure the dashboard can display clear startup failures instead of fake daemon status.
- Keep existing manual host-side daemon launch working.
- Add configuration for supervisor endpoint/command in the control API.

## Excluded

- Full distributed orchestration.
- Remote hosts over SSH.
- Kubernetes/container orchestration.
- Multi-user permissions.
- Production secret management.
- Rewriting the coding daemon workflow.
- Implementing the full deployer loop itself.

## Acceptance criteria

- The supervisor can be started on the host and reports health/status.
- The Docker control API can detect whether the supervisor is available.
- Starting the coding daemon from the dashboard delegates to the host supervisor instead of trying to run inside Docker.
- If the supervisor is unavailable, the dashboard shows a clear error and the manual host command.
- Supervisor-launched coding daemon has access to gh, Claude CLI, git worktrees and the canonical runtime root.
- Job logs and status are visible from the dashboard/control API.
- No fake PID/status files are written when startup fails.
- Existing manual daemon launch and existing runtime workflows still work.
