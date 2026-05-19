# Test Report — T115: Package ai-dev-factory as installable Docker Compose runtime

Date: 2026-05-19
Tester: AI Tester (automated)
Status: **FAIL — 2 blocking issues**

---

## Environment

- Docker 29.3.1 / Docker Compose v5.1.1
- macOS Darwin 25.4.0
- Branch: `ticket/T115-t115-package-ai-dev-factory-as-installable-docker`
- Commit tested: `a5b37bc` (IMPLEMENTATION_APPROVED checkpoint)

---

## Acceptance Criteria Results

| # | Criterion | Status | Notes |
|---|-----------|--------|-------|
| 1 | `docker compose up` fonctionne | **FAIL** | API inaccessible externally; web port conflict |
| 2 | restart container conserve runtime state | **PASS** | Named volume persists |
| 3 | upgrade image conserve runtime state | **PASS** | `--force-recreate` test passed |
| 4 | plusieurs projets peuvent être gérés | **PARTIAL** | Multi-instance yes; single project per instance |
| 5 | clone humain jamais modifié | **PASS** | Source not mounted; runtime goes to `/runtime` |
| 6 | daemon fonctionne après restart | **PARTIAL** | Endpoints exist; daemon is host-side V1 by design |
| 7 | worktrees runtime persistent | **PASS** | `/runtime/worktrees/` persists across restarts |

---

## Blocking Issues

### ISSUE-1 (CRITICAL): uvicorn binds to `127.0.0.1:8000` — API inaccessible externally

**Observed**: `docker compose up -d` starts the api container, but any external request to `localhost:8080` receives "connection reset". The API is running but not reachable.

**Root cause**: YAML `>` folded block scalar in `docker-compose.yml` does NOT collapse newlines when sub-lines are more-indented than the first content line. Docker Compose resolves the command to a multiline shell script where `--host 0.0.0.0` and `--port 8080` are on separate lines. The shell runs `python -m uvicorn services.control_api.main:app` (without flags), uvicorn starts in the foreground with defaults (`127.0.0.1:8000`), and the remaining lines are never reached.

**Evidence**:
```
# docker exec shows:
sh -c
  /app/deploy/bootstrap.sh &&
  python -m uvicorn services.control_api.main:app   ← runs here, blocks
    --host 0.0.0.0                                   ← never reached
    --port 8080                                      ← never reached

# /proc/net/tcp shows:
0100007F:1F40  →  127.0.0.1:8000  (uvicorn, wrong binding)
# Port 0x1F90 = 8080 is NOT present
```

**API responds internally** (`curl http://127.0.0.1:8000/health` inside container returns `{"status":"ok"}`), confirming uvicorn is up but inaccessible from outside.

**Fix**:
```yaml
# docker-compose.yml — replace the > scalar with a single-line command:
command: sh -c "/app/deploy/bootstrap.sh && python -m uvicorn services.control_api.main:app --host 0.0.0.0 --port 8080"
```

---

### ISSUE-2 (BLOCKING): `docker compose up` fails without `deploy/.env`

**Observed**: Without `deploy/.env`, every `docker compose` command fails immediately:
```
env file deploy/.env not found: stat .../deploy/.env: no such file or directory
```

The file is gitignored and must be created manually from `env.example`. This is intentional for credential security, but there is no documentation instructing the user to perform this step before running Docker Compose. The README makes no mention of Docker setup.

**Impact**: First-time `docker compose up` fails with no actionable error guidance.

**Fix**: Add a Docker deployment section to README.md:
```bash
cp deploy/env.example deploy/.env
# Edit deploy/.env with your GITHUB_TOKEN and GITHUB_REPO
docker compose up -d
```

Alternatively, make `env_file` optional in docker-compose.yml and document the env vars inline.

---

## Non-Blocking Issues

### ISSUE-3: Port 3000 hardcoded — collision risk

`docker-compose.yml` maps port `3000:80` for the web service with no env var override. Any pre-existing service on port 3000 (as observed: open-webui occupied port 3000 during testing) will silently fail the web service startup while api starts normally.

**Fix**: Make the port configurable:
```yaml
ports:
  - "${WEB_PORT:-3000}:80"
```
Add `WEB_PORT=3000` to `env.example`.

### ISSUE-4: Runtime directories leaked into Docker image

`COPY . /app/` + `.dockerignore` excluding only specific files (not directories) causes `runs/`, `clones/`, `state/`, `logs/`, `registry/` to be present at `/app/` inside the image. These are runtime-state directories that have no place in the application image. The API correctly resolves state to `/runtime/` via `AI_DEV_FACTORY_RUNTIME_ROOT`, so there is no functional impact, but the image contains empty or stale state directories.

**Fix**: Add directory-level exclusions to `.dockerignore`:
```
clones/
logs/
registry/
state/
```
(The `runs/` directory has tracked content like prompts, so needs selective exclusion — current pattern is sufficient.)

### ISSUE-5: Multi-project support is multi-instance only

The ticket requires "support multi-project". The implementation supports multi-instance (run separate docker-compose stacks per project) and multi-instance sharing a runtime root is possible. However, the control-api is single-project per deployment — `create_app()` takes one `project_root` and there are no endpoints to register or switch projects at runtime. If the requirement means a single runtime orchestrating N projects, this is not implemented.

### ISSUE-6: .gitignore has duplicate entries

The `.gitignore` file contains the same patterns repeated multiple times (e.g., `__pycache__/`, `*.pyc`, `runs/daemon.log`). No functional impact, but the file is difficult to maintain.

---

## Passed Verifications

**Runtime structure bootstrap**
```
bootstrap.sh creates: /runtime/{runs,worktrees,clones,logs,state,registry,.runtime}
Idempotent (mkdir -p). Correct. ✓
```

**Named volume persistence (restart)**
```
echo 'test-data' > /runtime/state/test-persistence.txt
docker compose restart api
cat /runtime/state/test-persistence.txt → test-data ✓
```

**Named volume persistence (image upgrade)**
```
docker compose up -d --force-recreate api
cat /runtime/state/test-persistence.txt → test-data ✓
```

**Worktree persistence**
```
mkdir /runtime/worktrees/T999-test && echo 'data' > .../state.txt
docker compose restart api
cat .../state.txt → data ✓
```

**Clone humain jamais modifié**
Source code is `COPY`'d into `/app/` at build time; not bind-mounted. Runtime state writes go to `/runtime/` volume. The source repository on the host is never touched by the container. ✓

**Daemon API endpoints**
`/daemon/status`, `/daemon/start`, `/daemon/stop`, `/daemon/restart`, `/daemon/activity`, `/daemon/board` are all implemented. The daemon is intentionally host-side in V1 (documented in `env.example`). Endpoints return correct JSON shapes. ✓

**CORS / API shape**
All tested endpoints (`/health`, `/tickets`, `/daemon/status`, `/project-map`) return valid JSON. ✓

---

## Conclusion

The implementation has the right structural foundations: the named volume correctly persists runtime state, the bootstrap is idempotent, the API routes are implemented, and the runtime/source separation is correct by design.

However, **the primary deliverable criterion — `docker compose up` producing a working, accessible service — fails** due to a YAML parsing bug that prevents uvicorn from binding to the correct address. This is a single-line fix in `docker-compose.yml`. The missing `deploy/.env` documentation is a second blocker for first-time setup.

**Recommendation**: Fix ISSUE-1 (YAML command), fix ISSUE-2 (README setup docs), then re-test. The two remaining issues (ISSUE-3, ISSUE-4) are low-risk and can be addressed in a follow-up.

**Verdict: IMPLEMENTATION_FIX_REQUIRED**
