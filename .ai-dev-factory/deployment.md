# AI Dev Factory — Deployment Guide

## Project Overview

AI Dev Factory is an autonomous software-development pipeline. A **supervisor** (host-side FastAPI process) bridges the containerised **control API** and the host environment. The **control API** (Docker) orchestrates ticket workflows, manages sandboxes, and exposes a REST surface. A **React dashboard** (Docker/nginx) provides the UI. A **daemon** (host-side Python process) polls GitHub issues and drives ticket execution by invoking `claude` CLI workers.

```
Browser → web (nginx :3000) → /api/ proxy → api (uvicorn :8080)
                                                    │
                                        supervisor (:8090, host)
                                                    │
                                       daemon (host, claude workers)
```

## Prerequisites

| Tool | Notes |
|------|-------|
| `git` | Clone and worktree operations |
| `docker` + Docker Compose v2 | Container runtime |
| `gh` | GitHub CLI, authenticated (`gh auth login`) |
| `claude` | Anthropic Claude Code CLI |
| Python 3.11+ | Host venv for supervisor and daemon |
| Node 20 | Only needed for local dashboard dev; Docker build handles it otherwise |

## First-Time Setup

```bash
# 1. Clone
git clone <repo-url>
cd ai-dev-factory

# 2. Create and populate deploy/.env
cp deploy/.env.example deploy/.env
# Edit deploy/.env — set AI_DEV_FACTORY_RUNTIME_ROOT, AI_DEV_FACTORY_PROJECT_ROOT,
# HOST_RUNTIME_ROOT, HOST_PROJECT_ROOT, GITHUB_TOKEN, GITHUB_REPO

# 3. Create the host Python venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r services/control_api/requirements.txt
```

## Build Commands

```bash
# Build all Docker images
docker compose build

# Build dashboard only (development)
cd apps/dashboard && npm ci && npm run build
```

## Startup Commands

Start in this order:

```bash
# 1. Host supervisor (terminal 1)
bash deploy/start_supervisor.sh

# 2. Docker stack (terminal 2)
docker compose up -d

# 3. Daemon (terminal 3, optional — only needed for autonomous issue polling)
source .venv/bin/activate
python tools/agent_runner/run_daemon.py \
  --exec-cmd "claude --dangerously-skip-permissions" \
  --poll-issues \
  --issue-repo <owner>/<repo> \
  --auto-commit --auto-push \
  --interval 30
```

Alternatively, configure `AI_DEV_FACTORY_HOST_DAEMON_COMMAND` in `deploy/.env` and use the dashboard's **Start Daemon** button to surface the launch command.

## Restart Procedure

```bash
# Restart Docker services
docker compose restart

# Restart supervisor
pkill -f "uvicorn services.supervisor.main" || true
bash deploy/start_supervisor.sh &

# Restart daemon
pkill -f "run_daemon.py" || true
# Re-run daemon start command above
```

## Healthcheck Procedure

```bash
# API liveness
curl -sf http://localhost:8080/health
# Expected: {"status":"ok"}

# Web (dashboard)
curl -sf http://localhost:3000

# Supervisor
curl -sf http://localhost:8090/health

# Full stack (as used by the deploy profile)
curl -sf http://localhost:8080/health && echo "healthy"
```

## Environment Variables

All variables live in `deploy/.env` (gitignored). Source of truth for both the host supervisor and Docker Compose.

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `AI_DEV_FACTORY_RUNTIME_ROOT` | Yes | `~/runtime/ai-dev-factory` | Host path to the shared runtime tree |
| `AI_DEV_FACTORY_PROJECT_ROOT` | Yes | — | Host path to the cloned repository |
| `HOST_RUNTIME_ROOT` | Yes | — | Same as `AI_DEV_FACTORY_RUNTIME_ROOT`; used for Docker bind-mount |
| `HOST_PROJECT_ROOT` | Yes | — | Host-side project root for path rewriting by supervisor |
| `CONTAINER_PROJECT_ROOT` | Yes | `/app` | Container-side path for supervisor path mapping |
| `CONTAINER_RUNTIME_ROOT` | Yes | `/runtime` | Container-side runtime path for supervisor mapping |
| `AI_DEV_FACTORY_SUPERVISOR_PORT` | No | `8090` | Port the supervisor listens on |
| `AI_DEV_FACTORY_SUPERVISOR_URL` | No | `http://host.docker.internal:8090` | URL used by API container to reach the supervisor |
| `GITHUB_TOKEN` | Yes (daemon) | — | PAT with `repo` + `issues` scopes |
| `GITHUB_REPO` | Yes (daemon) | — | `owner/repo` for issue polling |
| `GITHUB_ISSUE_LABEL` | No | `ai-ready` | Label that marks issues for AI processing |
| `DAEMON_EXEC_CMD` | No | `claude --dangerously-skip-permissions` | Command passed to ticket workers |
| `DAEMON_INTERVAL` | No | `30` | Polling interval in seconds |
| `DAEMON_MAX_WORKERS` | No | `1` | Max concurrent ticket workers |
| `AI_DEV_FACTORY_API_IN_DOCKER` | Internal | `1` (set by compose) | Prevents daemon from spawning inside the container |
| `AI_DEV_FACTORY_HOST_DAEMON_COMMAND` | No | — | SSH wrapper to start daemon from inside Docker |

## Runtime Dependencies

- **SQLite** — `$RUNTIME_ROOT/.runtime/ai-dev-factory.sqlite` — persists ticket/run state; created automatically by `bootstrap.sh`.
- **Runtime directory tree** — `$RUNTIME_ROOT/{runs,worktrees,clones,logs,state,registry,sandboxes,.runtime}` — created by `deploy/bootstrap.sh` on every API container start.
- **SSH keys** — mounted read-only into the API container at `/root/.ssh` for git operations.
- **Git config** — mounted read-only at `/root/.gitconfig`.
- **`claude` CLI** — must be installed and authenticated on the host; not available inside the container by design.
- **`gh` CLI** — must be authenticated on the host (`gh auth login`).

## Known Operational Constraints

- The **daemon is not containerised**. It must run on the host where `claude` and `gh` are available. The API container will refuse to spawn it locally (`AI_DEV_FACTORY_API_IN_DOCKER=1`).
- The supervisor must be running **before** `docker compose up`, because the API container contacts it at startup to register path mappings.
- `HOST_RUNTIME_ROOT` in `deploy/.env` must match the actual bind-mount source. A mismatch causes the supervisor path-rewriter to silently pass container paths through unchanged.
- The SQLite database is stored on the host volume (`$RUNTIME_ROOT/.runtime/`). Removing the volume destroys all run history.
