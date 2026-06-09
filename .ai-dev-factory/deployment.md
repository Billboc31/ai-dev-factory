# Deployment Guide

## Overview

`ai-dev-factory` is a self-hosted AI ticket-processing system composed of three runtime components:

- **supervisor** — a FastAPI process (`services/supervisor/main.py`) that runs on the **host** and manages daemon lifecycle, sandbox workers, and path mapping between Docker container paths and host paths. It binds to `127.0.0.1:${AI_DEV_FACTORY_SUPERVISOR_PORT}` (default `8090`).
- **api** — a FastAPI control plane (`services/control_api/main.py`) that runs inside a Docker container and exposes the REST API consumed by the dashboard. Bound to `${API_PORT}` (default `8080`).
- **web** — a React dashboard served by nginx inside a Docker container, bound to `${WEB_PORT}` (default `3000`).

The **daemon** (`tools/agent_runner/run_daemon.py`) is a separate host process, optionally launched by the supervisor or manually. It polls GitHub issues and drives the AI ticket workflow.

`deploy/.env` is the single source of truth for all paths, ports, and credentials. Both the host supervisor and the Docker stack read it. Never hard-code host-specific values in scripts.

---

## First-Time Setup

1. **Install required tools**: `git`, `docker`, `gh` (GitHub CLI), `claude` (Claude CLI).
2. Run bootstrap to create the Python venv, install dependencies, and initialise runtime directories:
   ```
   bash .ai-dev-factory/scripts/bootstrap.sh
   ```
3. Edit `deploy/.env` (copied from `deploy/.env.example`) and fill in host-specific paths:
   - `AI_DEV_FACTORY_RUNTIME_ROOT` — host path where runtime state lives (e.g. `~/runtime/ai-dev-factory`).
   - `AI_DEV_FACTORY_PROJECT_ROOT` — absolute path to this repository clone.
   - `HOST_RUNTIME_ROOT` / `HOST_PROJECT_ROOT` — same as above; used by the supervisor path mapper.
   - `GITHUB_TOKEN` and `GITHUB_REPO` — for daemon issue polling.
4. Build Docker images:
   ```
   bash .ai-dev-factory/scripts/build.sh
   ```
5. Start all services:
   ```
   bash .ai-dev-factory/scripts/start.sh
   ```

---

## Scripts

All scripts live in `.ai-dev-factory/scripts/`. They are idempotent and safe to re-run. They must be executed from the repository root or will compute it automatically from `${BASH_SOURCE[0]}`.

### `bootstrap.sh`
Checks required tools, creates `.venv`, installs Python dependencies from `services/control_api/requirements.txt`, copies `deploy/.env.example` → `deploy/.env` if absent, runs `deploy/bootstrap.sh` to create the runtime directory tree, and creates `.ai-dev-factory/run/` for PID files.

### `build.sh`
Builds the `api` and `web` Docker images using `docker compose build --parallel`. Sources `deploy/.env` for build-arg context. Pass a different `PROJECT_NAME` env var to scope the compose project.

### `start.sh`
1. Applies sandbox-injection precedence for `API_PORT`, `WEB_PORT`, `AI_DEV_FACTORY_SUPERVISOR_PORT`.
2. Creates the `ai-dev-factory-runtime` Docker network if absent.
3. Starts the host supervisor via `bash deploy/start_supervisor.sh` (background, PID written to `.ai-dev-factory/run/supervisor.pid`), waiting up to 30 s for `/health` to respond.
4. Starts the Docker compose stack (`api` + `web`) with `docker compose up -d`.

### `stop.sh`
1. POSTs to `${SUPERVISOR_HEALTH_URL}/daemon/stop` to stop the daemon gracefully.
2. Runs `docker compose down` scoped to the project name.
3. Sends `SIGTERM` to the supervisor PID from `.ai-dev-factory/run/supervisor.pid`, escalating to `SIGKILL` after 10 s if needed.

### `restart.sh`
Thin sequential wrapper: calls `stop.sh` then `start.sh`.

### `healthcheck.sh`
Probes three endpoints and exits non-zero if any fail:
- `http://localhost:${API_PORT}/health` — control API
- `http://localhost:${WEB_PORT}/` — web dashboard
- `http://127.0.0.1:${AI_DEV_FACTORY_SUPERVISOR_PORT}/health` — host supervisor

Used by the sandbox runner to validate deployments. Returns `0` only when all three are healthy.

---

## Environment Variables

All variables are read from `deploy/.env`. Sandbox runs may inject overrides via the process environment; injected values always win over `deploy/.env`.

| Variable | Default | Description |
|---|---|---|
| `AI_DEV_FACTORY_RUNTIME_ROOT` | `~/runtime/ai-dev-factory` | Host-side root for runs, state, worktrees, logs |
| `AI_DEV_FACTORY_PROJECT_ROOT` | _(required)_ | Absolute path to this repository clone on the host |
| `HOST_RUNTIME_ROOT` | same as `AI_DEV_FACTORY_RUNTIME_ROOT` | Supervisor path mapper: container `/runtime` → this host path |
| `HOST_PROJECT_ROOT` | same as `AI_DEV_FACTORY_PROJECT_ROOT` | Supervisor path mapper: container `/app` → this host path |
| `CONTAINER_RUNTIME_ROOT` | `/runtime` | Container-side runtime mount point |
| `CONTAINER_PROJECT_ROOT` | `/app` | Container-side project mount point |
| `API_PORT` | `8080` | Host port for the control API container |
| `WEB_PORT` | `3000` | Host port for the web dashboard container |
| `AI_DEV_FACTORY_SUPERVISOR_PORT` | `8090` | Port the host supervisor binds to |
| `AI_DEV_FACTORY_SUPERVISOR_URL` | `http://host.docker.internal:8090` | Supervisor URL used **from inside Docker containers** |
| `AI_DEV_FACTORY_SUPERVISOR_HEALTH_URL` | `http://127.0.0.1:8090` | Supervisor URL used **from host-side scripts** (healthcheck, stop) |
| `SANDBOX_ROOT` | `~/sandboxes` | Root directory for sandbox environments |
| `PROJECT_NAME` | `ai-dev-factory` | Docker compose project name; disambiguates parallel sandboxes |
| `SANDBOX_ID` | _(injected by sandbox runner)_ | Present during sandbox runs; used for network aliases |
| `GITHUB_TOKEN` | _(required for daemon)_ | GitHub PAT with `repo` + `issues` scopes |
| `GITHUB_REPO` | _(required for daemon)_ | GitHub repository in `owner/repo` format |

### Sandbox mode

When `SANDBOX_ID` is set, `tools/agent_runner/run_sandbox.py` injects isolated `API_PORT`, `WEB_PORT`, `AI_DEV_FACTORY_SUPERVISOR_PORT`, and `AI_DEV_FACTORY_SUPERVISOR_URL` into the script process environment. All operational scripts honour the precedence rule: snapshot inbound env → source `deploy/.env` → restore snapshot. This ensures sandbox healthchecks probe the sandbox's own ports, not the main runtime.

---

## Logs and State

| Path | Contents |
|---|---|
| `.ai-dev-factory/run/supervisor.pid` | PID of the running supervisor process |
| `.ai-dev-factory/run/supervisor.log` | stdout/stderr of the supervisor process |
| `${AI_DEV_FACTORY_RUNTIME_ROOT}/.runtime/ai-dev-factory.sqlite` | Persistent runtime database |
| `${AI_DEV_FACTORY_RUNTIME_ROOT}/runs/<TICKET>/` | Per-ticket workflow artifacts |
| `${AI_DEV_FACTORY_RUNTIME_ROOT}/logs/` | Daemon and worker logs |
