# Runtime Notes

## Split-Runtime Architecture (Docker API + Host Daemon)

The deliberate split — API in Docker, daemon on host — means two separate process trees must agree on path conventions. The supervisor's path-mapper (`services/supervisor/path_mapper.py`) rewrites container paths (`/app`, `/runtime/…`) to host paths using four variables from `deploy/.env`. If those variables are stale or incorrect, workers are spawned with wrong working directories and fail silently (the supervisor logs a warning but does not abort).

**Operational risk**: after a machine migration or directory rename, all four path variables (`CONTAINER_PROJECT_ROOT`, `HOST_PROJECT_ROOT`, `CONTAINER_RUNTIME_ROOT`, `HOST_RUNTIME_ROOT`) must be updated atomically. Partial updates produce hard-to-diagnose failures.

## `deploy/.env` as Single Source of Truth

Both `start_supervisor.sh` (host) and `docker-compose.yml` (container) consume the same `deploy/.env`. If `.env` is absent, the supervisor emits a warning and falls back to defaults; the compose stack uses its own hardcoded defaults. The two halves can therefore diverge silently on a fresh checkout where `.env` has not yet been created.

## Daemon Startup Is Manual

There is no process supervisor (systemd, supervisord, PM2) managing the daemon. If it crashes it stays down. The dashboard's "Start Daemon" button surfaces a command string for manual copy/paste when `AI_DEV_FACTORY_HOST_DAEMON_COMMAND` is unset — it does not start the process itself.

## SQLite Under Concurrent Workers

`runtime_db.py` uses SQLite. With `DAEMON_MAX_WORKERS > 1`, concurrent workers hit the same database. SQLite's WAL mode can handle modest concurrency, but no connection pooling or retry logic is visible in `requirements.txt` (no `aiosqlite`, no `SQLAlchemy`). Raising `DAEMON_MAX_WORKERS` beyond 1 may cause `database is locked` errors under load.

## Bootstrap Migration Logic

`deploy/bootstrap.sh` includes best-effort migration code that copies the SQLite database and JSON state files from legacy locations. This code runs on every container start. Once the migration has been applied it is harmless, but on a first deploy against a pre-existing runtime tree it will silently copy old state that may be inconsistent with the current schema.

## Sandbox Worktrees in the Runtime Tree

Analysis and deploy workers operate in isolated git worktrees created under `$RUNTIME_ROOT/worktrees/` and `$RUNTIME_ROOT/sandboxes/`. These are not cleaned up automatically on crash. A stale `daemon.lock` file left behind by a crashed run (visible in several `runs/T*/` directories) can block a ticket from being picked up again until deleted manually.

## Node/Dashboard Build Is Not Hot-Reloaded in Production

The `web` Docker image bakes the compiled Vite output at build time. Frontend changes require `docker compose build web && docker compose up -d web`. There is no volume-mounted dev server in the production compose file.
