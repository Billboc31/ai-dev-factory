# Deploy — host + Docker bootstrap

A fresh machine deployment of ai-dev-factory should only require editing
**one file**: `deploy/.env`. Everything else (supervisor, Docker stack,
host daemon) reads its configuration from there.

## 1. Configure paths once

```bash
cp deploy/.env.example deploy/.env
# Edit deploy/.env and fill the four host paths:
#   AI_DEV_FACTORY_RUNTIME_ROOT, AI_DEV_FACTORY_PROJECT_ROOT,
#   HOST_PROJECT_ROOT, HOST_RUNTIME_ROOT
```

`deploy/.env` is **gitignored** and never committed.

## 2. Start the host supervisor

```bash
bash deploy/start_supervisor.sh
```

The script sources `deploy/.env` so the supervisor sees all the
`CONTAINER_*` ↔ `HOST_*` mapping rules and binds to the configured
`AI_DEV_FACTORY_SUPERVISOR_PORT` (default `8090`). It prints the resolved
configuration at startup so you can verify the mapping.

## 3. Start the global Traefik reverse proxy (once per host)

```bash
docker compose --profile infra up -d traefik
```

Traefik is **shared infrastructure**, not a per-sandbox service. It
binds port `80` and watches `${HOST_RUNTIME_ROOT}/proxy/routes` for the
dynamic route files written by `proxy_manager.py`. Sandboxes only
register/unregister route files there.

Traefik is gated behind the `infra` Docker Compose profile so that a
plain `docker compose up -d` (used by sandbox compose runs inside an
isolated worktree) never tries to spawn a per-sandbox Traefik. Without
the gate, every sandbox after the first one would fail with:

```text
Bind for 0.0.0.0:80 failed: port is already allocated
```

To verify the profile gating is in place:

```bash
docker compose config --services                # api, web (no traefik)
docker compose --profile infra config --services  # api, traefik, web
```

To stop the global Traefik:

```bash
docker compose --profile infra down
```

## 4. Start the application Docker stack

```bash
docker compose --env-file deploy/.env up -d
```

This starts only `api` and `web` — Traefik is excluded by the profile
gate, so sandbox compose runs (`docker compose -p sandbox-… up -d`)
will behave identically: no extra Traefik, no port-80 collision.

The `--env-file deploy/.env` flag is what makes the variables available
for `${HOST_RUNTIME_ROOT}` interpolation in `docker-compose.yml`. Without
it, compose still works but falls back to the documented defaults under
`~/runtime/ai-dev-factory`. If you prefer not to pass the flag every
time, symlink `.env -> deploy/.env`:

```bash
ln -s deploy/.env .env
docker compose up -d
```

## How the path mapping works

The control API runs **inside Docker** and emits container paths like
`/app` (the project root) and `/runtime/...`. The supervisor runs on
the **host** and must rewrite those paths before spawning subprocesses.
`services/supervisor/path_mapper.py` walks the configured rules
(longest prefix wins, identity fallback) and logs the strategy used —
for example:

```
path_mapper: mapped via project-root: '/app' -> '/Users/.../clones/ai-dev-factory'
path_mapper: mapped via runtime-root: '/runtime/worktrees/T142' -> '/Users/.../worktrees/T142'
path_mapper: no rule matched, identity: '/tmp/some-tool'
```

Operators see the same lines in `~/runtime/ai-dev-factory/logs/` and
in `runs/daemon.log`, which makes misconfigured `.env` immediately
diagnosable.
