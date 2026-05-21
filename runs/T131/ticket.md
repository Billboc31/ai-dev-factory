# T131 — T131 — Supervisor daemon persistence and unexpected exit handling

**Source**: GitHub Issue #100

## Description

# Objective

Improve the host supervisor so the daemon lifecycle is durable, observable and resilient to unexpected exits.

## Included

- Detect when the supervised daemon process exits unexpectedly.
- Preserve daemon exit metadata:
  - last_exit_code
  - last_exit_time
  - last_error
- Expose daemon runtime state through the supervisor API.
- Add restart policy support:
  - no-restart
  - restart-on-crash
- Ensure the daemon is fully detached from transient API requests.
- Improve PID/liveness handling.
- Surface supervisor/daemon errors clearly in the dashboard.
- Add dashboard visibility for:
  - daemon crashed
  - daemon stopped unexpectedly
  - restart attempts
- Add tests for:
  - unexpected daemon exit
  - stale PID recovery
  - restart policy behavior
  - supervisor status reporting

## Excluded

- Generic job supervisor.
- Multi-process orchestration.
- Deployment supervision.
- Remote host execution.
- Kubernetes/systemd integration.

## Acceptance criteria

- The daemon continues running after dashboard/API requests complete.
- Unexpected daemon exits are detected and reported.
- Dashboard clearly shows daemon crash state.
- Restart-on-crash policy successfully relaunches the daemon.
- Stale PID files are recovered automatically.
- Supervisor status API exposes runtime and crash information.
- Existing daemon workflows continue to work.
