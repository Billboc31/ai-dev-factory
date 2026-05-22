# AI Dev Factory — Deployment Guide

## Overview

AI Dev Factory is an autonomous software-development pipeline composed of four components:

```
Browser → web (nginx :3000) → /api/ proxy → api (uvicorn :8080)
                                                   │
                                       supervisor (:8090, host)
                                                   │
                                      daemon (host, claude workers)
```

| Component | Runtime | Description |
|-----------|---------|-------------|
| `api` | Docker | Control API (FastAPI/uvicorn) — orchestrates ticket workflows, manages sandboxes, exposes REST surface |
| `web` | Docker | React dashboard served via nginx |
| `supervisor` | Host | FastAPI process bridging Docker containers and the host environment; rewrites container paths to host paths |
| `daemon` | Host | Polls GitHub issues, drives ticket execution by spawning `claude` CLI workers |

The **supervisor must be running before** `docker compose up` because the API container contacts it at startup to register path mappings.

The **daemon is not containerised**. It requires `claude` and `gh` installed and authenticated on the host.

---

## Prerequisites

| Tool | Notes |
|------|-------|
| `git` | Clone and worktree operations |
| `docker` + Docker Compose v2 | Container runtime |
| `gh` | GitHub CLI — authenticate with `gh auth login` before use |
| `claude` | Anthropic Claude Code CLI — must be authenticated |
| Python 3.11+ | Host venv for supervisor and daemon |

---

## First-Time Setup

```bash
# 1. Clone the repository
git clone <repo-url>
cd ai-dev-factory

# 2. Copy and populate deploy/.env (gitignored — never committed)
cp deploy/.env.example deploy/.env
# Edit deploy/.env: set AI_DEV_FACTORY_RUNTIME_ROOT, AI_DEV_FACTORY_PROJECT_ROOT,
# HOST_RUNTIME_ROOT, HOST_PROJECT_ROOT, GITHUB_TOKEN, GITHUB_REPO

# 3. Bootstrap — creates venv, installs Python deps, creates runtime directories
bash .ai-dev-factory/scripts/bootstrap.sh

# 4. Build Docker images
bash .ai-dev-factory/scripts/build.sh
```

---

## Scripts

All scripts live in `.ai-dev-factory/scripts/`. They are safe to run from any working directory and source `deploy/.env` automatically.

### `bootstrap.sh`

**Purpose:** First-time and idempotent environment setup.

- Creates the runtime directory tree under `$AI_DEV_FACTORY_RUNTIME_ROOT`
- Creates `.ai-dev-factory/run/` (PID file directory)
- Runs best-effort SQLite and state-file migrations
- Creates the Python venv at `.venv/` if it does not exist
- Installs/upgrades `services/control_api/requirements.txt`
- Warns if required tools (`git`, `docker`, `gh`, `claude`) are missing from PATH

Run this on every fresh machine before anything else.

### `build.sh`

**Purpose:** Build all Docker images.

Runs `docker compose build` (with `--env-file deploy/.env` when available). Re-run after any `Dockerfile` or source change.

### `start.sh`

**Purpose:** Start all project services.

1. Activates `.venv` and starts the supervisor via `deploy/start_supervisor.sh` in background; writes its PID to `.ai-dev-factory/run/supervisor.pid`. Skips if the supervisor is already running.
2. Runs `docker compose up -d` to start the `api` and `web` containers. Already-running containers are left untouched by Docker Compose.

Does **not** start the daemon — use the dashboard's Start Daemon button or launch it manually (see below).

### `stop.sh`

**Purpose:** Gracefully stop all project services.

1. **Daemon** — POST to `http://127.0.0.1:$SUPERVISOR_PORT/daemon/stop` (supervisor HTTP API). Tolerates supervisor being unreachable.
2. **Docker stack** — `docker compose down` (project-scoped by working directory).
3. **Supervisor** — reads `.ai-dev-factory/run/supervisor.pid`, sends SIGTERM, waits up to 10 s for clean exit, then SIGKILL if still alive. Cleans up the PID file.

### `restart.sh`

**Purpose:** Thin wrapper — calls `stop.sh` then `start.sh`.

### `healthcheck.sh`

**Purpose:** Probe all services and exit non-zero if any are unhealthy.

Probes (up to 3 attempts with 5 s delay, 30 s timeout each):

| Service | URL |
|---------|-----|
| API | `http://localhost:8080/health` |
| Web | `http://localhost:3000` |
| Supervisor | `http://127.0.0.1:$AI_DEV_FACTORY_SUPERVISOR_PORT/health` |

Prints `PASS`/`FAIL` per probe, exits 0 only when all pass.

---

## Starting the Daemon Manually

The daemon runs on the host (not in Docker) and requires `claude` and `gh`:

```bash
source .venv/bin/activate
python tools/agent_runner/run_daemon.py \
  --exec-cmd "claude --dangerously-skip-permissions" \
  --poll-issues \
  --issue-repo <owner>/<repo> \
  --auto-commit --auto-push --auto-include-code \
  --interval 30
```

Alternatively, set `AI_DEV_FACTORY_HOST_DAEMON_COMMAND` in `deploy/.env` and use the dashboard's **Start Daemon** button to surface or trigger the command.

---

## Environment Variables

All variables are read from `deploy/.env` (gitignored). This file is the single source of truth for both the host supervisor and Docker Compose. Copy `deploy/.env.example` and fill in values on each machine.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AI_DEV_FACTORY_RUNTIME_ROOT` | Yes | `~/runtime/ai-dev-factory` | Host path to the shared runtime tree (`runs/`, `worktrees/`, SQLite, etc.) |
| `AI_DEV_FACTORY_PROJECT_ROOT` | Yes | — | Host path to the cloned repository |
| `HOST_RUNTIME_ROOT` | Yes | — | Same as `AI_DEV_FACTORY_RUNTIME_ROOT`; used as Docker bind-mount source |
| `HOST_PROJECT_ROOT` | Yes | — | Host-side project root; used by the supervisor path rewriter |
| `CONTAINER_PROJECT_ROOT` | Yes | `/app` | Container-side project path for supervisor path mapping |
| `CONTAINER_RUNTIME_ROOT` | Yes | `/runtime` | Container-side runtime path for supervisor path mapping |
| `AI_DEV_FACTORY_SUPERVISOR_PORT` | No | `8090` | Port the supervisor listens on (host, `127.0.0.1`) |
| `AI_DEV_FACTORY_SUPERVISOR_URL` | No | `http://host.docker.internal:8090` | URL Docker containers use to reach the supervisor |
| `GITHUB_TOKEN` | Yes (daemon) | — | Personal access token with `repo` + `issues` scopes |
| `GITHUB_REPO` | Yes (daemon) | — | `owner/repo` for issue polling |
| `GITHUB_ISSUE_LABEL` | No | `ai-ready` | Label that marks issues for AI processing |
| `DAEMON_EXEC_CMD` | No | `claude --dangerously-skip-permissions` | Command passed to ticket workers |
| `DAEMON_INTERVAL` | No | `30` | Polling interval in seconds |
| `DAEMON_MAX_WORKERS` | No | `1` | Maximum concurrent ticket workers |
| `AI_DEV_FACTORY_API_IN_DOCKER` | Internal | `1` (set by compose) | Prevents daemon from being spawned inside the container |
| `AI_DEV_FACTORY_HOST_DAEMON_COMMAND` | No | — | Shell command (e.g. SSH wrapper) used by the dashboard to start the daemon on the host |

---

## Runtime Layout

```
$AI_DEV_FACTORY_RUNTIME_ROOT/
├── .runtime/ai-dev-factory.sqlite   # ticket and run state (persisted across restarts)
├── runs/                            # per-ticket artifact trees
├── worktrees/                       # git worktrees for isolated ticket execution
├── clones/                          # project clones
├── logs/                            # daemon and worker logs
├── state/                           # workers.json, .issue-intake.json
├── registry/                        # project registry
└── sandboxes/                       # sandbox isolation roots
```

The SQLite database stores all ticket and run history. **Deleting the volume or `$RUNTIME_ROOT` destroys this history** — back it up before removing.

---

## Known Operational Constraints

- The supervisor must be running **before** `docker compose up`. The API container registers path mappings with the supervisor at startup; a missing supervisor causes worker path resolution to fall back to identity mapping (container paths pass through unchanged).
- `HOST_RUNTIME_ROOT` in `deploy/.env` must exactly match the bind-mount source in `docker-compose.yml`. A mismatch causes the supervisor path rewriter to silently return container-side paths to workers.
- The daemon is **not containerised** and must run on the host where `claude` and `gh` are installed and authenticated.
- PID files for the supervisor are stored in `.ai-dev-factory/run/supervisor.pid`. If the supervisor crashes without removing this file, `start.sh` will detect a stale PID (`kill -0` fails) and start a new instance automatically.
