# AI Dev Factory — Deployment Guide

## Overview

AI Dev Factory is an autonomous software-development pipeline composed of four components:

| Component | Type | Port | Description |
|-----------|------|------|-------------|
| `api` | Docker (uvicorn) | 8080 | Control API — orchestrates ticket workflows, manages sandboxes, exposes REST surface |
| `web` | Docker (nginx) | 3000 | React dashboard — UI for tickets, daemon status, runtime monitoring |
| `supervisor` | Host (uvicorn) | 8090 | Path-rewriting bridge between the Docker API container and host filesystem |
| `daemon` | Host (Python) | — | Polls GitHub issues, drives ticket execution via `claude` CLI workers |

```
Browser → web (nginx :3000) → /api/ proxy → api (uvicorn :8080)
                                                    │
                                        supervisor (:8090, host)
                                                    │
                                       daemon (host, claude workers)
```

**Start order**: supervisor → Docker stack (api + web) → daemon (optional).  
The supervisor must be running **before** `docker compose up` because the API container contacts it at startup to register path mappings.

---

## Prerequisites

| Tool | Notes |
|------|-------|
| `git` | Clone and worktree operations |
| `docker` + Docker Compose v2 | Container runtime |
| `gh` | GitHub CLI — must be authenticated (`gh auth login`) |
| `claude` | Anthropic Claude Code CLI — must be installed and authenticated on the host |
| Python 3.11+ | Host venv for supervisor and daemon |
| Node 20 | Only needed for local dashboard dev; Docker build handles it otherwise |

---

## Scripts

All scripts live in `.ai-dev-factory/scripts/` and are safe to run multiple times (idempotent).

### `bootstrap.sh`

First-time setup. Run once per machine or after a fresh clone.

```
bash .ai-dev-factory/scripts/bootstrap.sh
```

What it does:
1. Verifies that `git`, `docker`, `gh`, and `claude` are on `PATH`.
2. Copies `deploy/.env.example` → `deploy/.env` if the file does not yet exist.
3. Creates the host Python venv at `.venv` and installs `services/control_api/requirements.txt`.
4. Creates the runtime directory tree under `$AI_DEV_FACTORY_RUNTIME_ROOT` (default: `~/runtime/ai-dev-factory`).

**Edit `deploy/.env` before proceeding.** See the [Environment variables](#environment-variables) section.

### `build.sh`

Builds all Docker images.

```
bash .ai-dev-factory/scripts/build.sh
```

Equivalent to `docker compose build --pull`. Run after any change to `Dockerfile` or `apps/dashboard`.

### `start.sh`

Starts all services in the correct order.

```
bash .ai-dev-factory/scripts/start.sh
# To also start the daemon:
START_DAEMON=1 bash .ai-dev-factory/scripts/start.sh
```

Sequence:
1. Starts the host supervisor (nohup, logs to `$RUNTIME_ROOT/logs/supervisor.log`). Waits up to 10 s for `/health` to respond before continuing.
2. Runs `docker compose up -d` (api + web).
3. If `START_DAEMON=1`, starts the daemon (nohup, logs to `$RUNTIME_ROOT/logs/daemon.log`).

If a service is already running it is left untouched.

### `stop.sh`

Gracefully stops all services.

```
bash .ai-dev-factory/scripts/stop.sh
```

Sequence: daemon → Docker stack (`docker compose down`) → supervisor. Sends `SIGTERM`, waits 2 s, then `SIGKILL` if still alive.

### `restart.sh`

Thin wrapper: calls `stop.sh` then `start.sh`.

```
bash .ai-dev-factory/scripts/restart.sh
```

### `healthcheck.sh`

Probes all services and exits 0 only when all required services are healthy.

```
bash .ai-dev-factory/scripts/healthcheck.sh
```

Probes (3 attempts, 5 s delay, 30 s timeout per attempt):
- `http://localhost:8080/health` — API liveness (required)
- `http://localhost:3000` — dashboard nginx (required)
- `http://127.0.0.1:$SUPERVISOR_PORT/health` — supervisor liveness (required)
- `run_daemon.py` process presence — daemon (warning only; daemon is optional)

Override defaults via environment: `HEALTHCHECK_RETRIES`, `HEALTHCHECK_DELAY`, `HEALTHCHECK_TIMEOUT`.

---

## Environment variables

All variables live in `deploy/.env` (gitignored). This file is the **single source of truth** for both the host supervisor and Docker Compose. Copy `deploy/.env.example` and fill in the host-specific values.

### Paths

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AI_DEV_FACTORY_RUNTIME_ROOT` | Yes | `~/runtime/ai-dev-factory` | Host path to the shared runtime tree (runs, worktrees, DB, logs) |
| `AI_DEV_FACTORY_PROJECT_ROOT` | Yes | — | Host path to the cloned repository |
| `HOST_RUNTIME_ROOT` | Yes | — | Same as `AI_DEV_FACTORY_RUNTIME_ROOT`; used as the Docker bind-mount source |
| `HOST_PROJECT_ROOT` | Yes | — | Host-side project root used by the supervisor for path rewriting |
| `CONTAINER_PROJECT_ROOT` | Yes | `/app` | Container-side project root (supervisor mapping source) |
| `CONTAINER_RUNTIME_ROOT` | Yes | `/runtime` | Container-side runtime root (supervisor mapping source) |

### Supervisor

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AI_DEV_FACTORY_SUPERVISOR_PORT` | No | `8090` | Port the supervisor listens on |
| `AI_DEV_FACTORY_SUPERVISOR_URL` | No | `http://host.docker.internal:8090` | URL used by the API container to reach the supervisor |

### GitHub / Daemon

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GITHUB_TOKEN` | Yes (daemon) | — | PAT with `repo` + `issues` scopes |
| `GITHUB_REPO` | Yes (daemon) | — | `owner/repo` for issue polling (e.g. `Billboc31/ai-dev-factory`) |
| `GITHUB_ISSUE_LABEL` | No | `ai-ready` | Label that marks issues ready for AI processing |
| `DAEMON_EXEC_CMD` | No | `claude --dangerously-skip-permissions` | Command passed to each ticket worker |
| `DAEMON_INTERVAL` | No | `30` | Polling interval in seconds |
| `DAEMON_MAX_WORKERS` | No | `1` | Maximum concurrent ticket workers |

### Internal / advanced

| Variable | Default | Description |
|----------|---------|-------------|
| `AI_DEV_FACTORY_API_IN_DOCKER` | `1` (set by compose) | Prevents daemon spawn inside the container |
| `AI_DEV_FACTORY_HOST_DAEMON_COMMAND` | — | Optional SSH wrapper to start the daemon from inside Docker |

---

## Runtime dependencies

- **SQLite** — `$RUNTIME_ROOT/.runtime/ai-dev-factory.sqlite` — persists ticket/run state; created automatically on first API boot via `deploy/bootstrap.sh`.
- **Runtime directory tree** — `$RUNTIME_ROOT/{runs,worktrees,clones,logs,state,registry,sandboxes,.runtime}` — created by `bootstrap.sh`.
- **SSH keys** — mounted read-only into the API container at `/root/.ssh` for git operations.
- **Git config** — mounted read-only at `/root/.gitconfig`.
- **`claude` CLI** — must be installed and authenticated on the host. Not available inside the container by design.
- **`gh` CLI** — must be authenticated on the host (`gh auth login`).

## Known operational constraints

- The **daemon is not containerised**. It must run on the host where `claude` and `gh` are available. The API container will refuse to spawn it locally (`AI_DEV_FACTORY_API_IN_DOCKER=1`).
- `HOST_RUNTIME_ROOT` in `deploy/.env` must exactly match the Docker bind-mount source. A mismatch causes the supervisor path-rewriter to silently pass container paths through unchanged.
- The SQLite database is stored on the host volume (`$RUNTIME_ROOT/.runtime/`). Removing the volume destroys all run history.
- The supervisor must be **healthy** before `docker compose up`. `start.sh` enforces this by polling `/health` for up to 10 s.
