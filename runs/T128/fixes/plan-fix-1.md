# Plan fix request — T128

Please reduce T128 to a minimal host-supervisor V1.

## T128 V1 objective

Allow the Docker dashboard/control API to delegate daemon lifecycle operations to a small host-side supervisor service.

V1 only needs to support:
- dashboard start daemon
- dashboard stop daemon
- dashboard daemon status

using a host-side runtime instead of trying to run the daemon inside Docker.

## Include in V1

- Minimal host supervisor service.
- Local host execution only.
- Minimal HTTP endpoints:
  - /health
  - /daemon/status
  - /daemon/start
  - /daemon/stop
- Supervisor launches the existing daemon command using the host venv.
- Docker control API delegates to the supervisor when AI_DEV_FACTORY_SUPERVISOR_URL is configured.
- Dashboard displays supervisor reachability.
- Structured errors when supervisor is unavailable.
- Minimal tests for health and delegation.

## Exclude from V1

- deployment jobs
- generic job registry
- deployment orchestration
- advanced locking
- filesystem job persistence
- deploy queue
- deployment logs
- dependency auto-install
- multi-job scheduling

## Acceptance criteria

- Dashboard can start the daemon through the supervisor.
- Dashboard can stop the daemon through the supervisor.
- Dashboard can display daemon status through the supervisor.
- Daemon runs host-side with gh, claude and git access.
- Dashboard no longer attempts to spawn the daemon inside Docker.
- Unreachable supervisor returns a structured error.
- Existing manual daemon flow still works.
