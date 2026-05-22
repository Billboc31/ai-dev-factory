# Runtime Notes

## Split-Runtime Architecture (Docker API + Host Daemon)

The deliberate split — API in Docker, daemon on host — means two separate process trees must agree on path conventions. The supervisor's path-mapper (`services/supervisor/path_mapper.py`) rewrites container paths (`/app`, `/runtime/…`) to host paths using four variables from `deploy/.env`. If those variables are stale or incorrect, workers are spawned with wrong working directories and fail.

**Operational risk**: after a machine migration or directory rename, all four path variables (`CONTAINER_PROJECT_ROOT`, `HOST_PROJECT_ROOT`, `CONTAINER_RUNTIME_ROOT`, `HOST_RUNTIME_ROOT`) must be updated atomically.

## `deploy/.env` as Single Source of Truth

Both `start_supervisor.sh` (host) and Docker Compose consume the same `deploy/.env`. Incorrect or missing values can cause the supervisor to resolve container paths incorrectly.

## Supervisor and Daemon Lifecycle

The daemon runs on the host because `claude` and `gh` are intentionally not installed in the Docker API container.

The supervisor can:
- expose daemon status
- start/stop the daemon
- surface launch commands to the dashboard

depending on the configured runtime mode.

If the daemon crashes unexpectedly, stale PID/lock files may block future runs until cleanup logic removes them.

## SQLite Under Concurrent Workers

`runtime_db.py` uses SQLite. With `DAEMON_MAX_WORKERS > 1`, concurrent workers hit the same database. SQLite WAL mode supports modest concurrency, but higher worker counts may still produce `database is locked` errors under load.

## Bootstrap Migration Logic

`deploy/bootstrap.sh` includes best-effort migration code that copies the SQLite database and JSON state files from legacy locations. This code runs on every container start.

## Sandbox Worktrees in the Runtime Tree

Analysis and deploy workers operate in isolated git worktrees created under `$RUNTIME_ROOT/worktrees/` and `$RUNTIME_ROOT/sandboxes/`.

These worktrees must remain isolated from the main runtime worktree to prevent AI-generated deployment/testing loops from modifying the active runtime.

## Node/Dashboard Build Is Not Hot-Reloaded in Production

The `web` Docker image bakes the compiled Vite output at build time. Frontend changes require rebuilding the web image.
