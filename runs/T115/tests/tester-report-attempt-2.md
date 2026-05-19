# Test Report — T115 Docker Compose Runtime (Attempt 2)

**Date**: 2026-05-20
**Branch**: ticket/T115-t115-package-ai-dev-factory-as-installable-docker
**State entering**: IMPLEMENTATION_APPROVED
**Verdict**: **IMPLEMENTATION_FIX_REQUIRED**

---

## Summary

Two blocking issues survive from the previous tester cycle. The original ISSUE-1 (YAML uvicorn binding) was documented in the first test report but was NOT fixed in the subsequent `IMPLEMENTATION_FIX_REQUIRED` commit (0188de4). That commit only removed the `daemon` service from docker-compose.yml. The `api` service retains the same YAML folded-scalar bug. Additionally, a new regression was introduced: the `AI_DEV_FACTORY_RUNTIME_ROOT` env var unconditionally overrides `--runs-dir` in `run_daemon.py`, breaking two existing tests when the env var is present.

---

## Acceptance Criteria Results

### Ticket Tests Section

| Criterion | Status | Evidence |
|-----------|--------|---------|
| `docker compose up` fonctionne | **FAIL** | API binds `127.0.0.1:8000` instead of `0.0.0.0:8080`; port 8080 inaccessible |
| restart container conserve runtime state | **PASS** | Named volume persists data across new containers (verified via docker volume) |
| upgrade image conserve runtime state | **PASS** | New container on existing volume reads state written by previous container |
| plusieurs projets peuvent être gérés | **PASS (multi-instance)** | Multi-instance via separate compose stacks; documented in env.example |
| clone humain jamais modifié | **PASS** | Source copied into `/app`; runtime at `/runtime` (separate volume) |
| daemon fonctionne après restart | **PARTIAL** | Host-side daemon by V1 design decision; RUNTIME_ROOT integration works |
| worktrees runtime persistent | **PASS** | `/runtime/worktrees` persists in named volume |

### Invariants Section

| Invariant | Status | Evidence |
|-----------|--------|---------|
| produit installé ≠ repo source | **PASS** | Docker volume isolates runtime; source in `/app` |
| runtime data persistante | **PASS** | Named volume driver=local, survives compose restart |
| runtime redémarrable | **PASS** | bootstrap.sh is idempotent; container restart restores structure |
| runtime remplaçable | **PASS** | New image + same volume = preserved state |
| plusieurs runtimes possibles | **PASS** | Separate named volumes via compose project name |
| plusieurs projets gérés possibles | **PASS (V1)** | Multi-instance; single-project per instance |
| worktrees runtime isolés | **PASS** | `/runtime/worktrees` in volume, not in image |

### Git/Runtime Section

| Criterion | Status | Evidence |
|-----------|--------|---------|
| aucun runtime state versionné | **FAIL** | `runs/workers.json`, `runs/daemon.log`, `.runtime/ai-dev-factory.sqlite` tracked in T115 branch but not in main |
| aucun log versionné | **FAIL** | `runs/daemon.log` tracked; .gitignore rule exists but file was not untracked (`git rm --cached`) |
| aucun pycache versionné | **PARTIAL** | 51 `__pycache__/*.pyc` files tracked in branch diff vs main; fix commit only cleaned 2 specific files |

---

## Blocking Issues

### ISSUE-1 (CRITICAL) — YAML Bug: uvicorn binds 127.0.0.1:8000, not 0.0.0.0:8080

**Status**: Was identified in attempt 1. Was NOT fixed in commit 0188de4. Still present.

**Root cause**: `docker-compose.yml` uses YAML folded block scalar (`>`):
```yaml
command: >
  sh -c "
    /app/deploy/bootstrap.sh &&
    python -m uvicorn services.control_api.main:app
      --host 0.0.0.0
      --port 8080
  "
```
Lines with greater indentation than the first content line are preserved as literal newlines in the folded scalar. Docker Compose shell-splits the result, giving `sh -c` a multi-line script. The shell runs `python -m uvicorn services.control_api.main:app` on one line, then `--host 0.0.0.0` as a separate command (which is a no-op or error). Uvicorn defaults to `127.0.0.1:8000`.

**Verified**: Container log confirms `Uvicorn running on http://127.0.0.1:8000`.

**Fix**:
```yaml
command: sh -c "/app/deploy/bootstrap.sh && python -m uvicorn services.control_api.main:app --host 0.0.0.0 --port 8080"
```

**Impact**: `docker compose up` starts containers but API is unreachable on port 8080. Primary acceptance criterion fails.

---

### ISSUE-2 (BLOCKING) — Runtime state files tracked in git

**Status**: New finding (not in previous report).

**Files tracked in T115 branch but NOT in main**:
- `runs/workers.json` — added by older checkpoint commits in this worktree
- `runs/daemon.log` — same
- `.runtime/ai-dev-factory.sqlite` — same

The `.gitignore` rules are correct and will block new additions. But the existing tracked files were not untracked via `git rm --cached`. The fix commit (0188de4) only removed 2 `.pyc` files, not these runtime state files.

Additionally, 51 `__pycache__/*.pyc` files appear in the branch diff vs main.

**Fix**:
```bash
git rm --cached runs/workers.json runs/daemon.log .runtime/ai-dev-factory.sqlite
git rm --cached -r services/__pycache__ services/control_api/__pycache__ \
  tools/agent_runner/__pycache__ tests/__pycache__
```

**Impact**: Ticket invariant "aucun runtime state versionné" / "aucun pycache versionné" fails.

---

### ISSUE-3 (BLOCKING REGRESSION) — `AI_DEV_FACTORY_RUNTIME_ROOT` overrides `--runs-dir` CLI flag, breaking tests

**Status**: New regression introduced by T115.

**Failing tests**:
- `tests/test_run_daemon.py::test_main_returns_2_when_runs_dir_missing` — expects rc=2 when `--runs-dir` points to a nonexistent path; T115's code uses RUNTIME_ROOT env var instead, finds real runs dir, returns rc=0
- `tests/test_daemon_issue_polling.py::test_main_poll_issues_flag_calls_poll_before_run_once` — mock assertion fails because the path is the real runtime instead of the temp dir

**Root cause** (`tools/agent_runner/run_daemon.py`, around line 1409):
```python
runtime_root = os.environ.get("AI_DEV_FACTORY_RUNTIME_ROOT")
if runtime_root:
    runs_dir = rt / "runs"
    worktrees_dir = rt / "worktrees"
else:
    runs_dir = Path(args.runs_dir)
    worktrees_dir = Path(args.worktrees_dir)
```
When `AI_DEV_FACTORY_RUNTIME_ROOT` is set in the environment (as it is in any runtime clone), `--runs-dir` is silently ignored. The tests were not updated to mock or clear this env var.

**Fix options**:
1. Tests clear `AI_DEV_FACTORY_RUNTIME_ROOT` in setup: `monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)`
2. Daemon gives priority to explicit `--runs-dir` over env var

**Impact**: 2 tests fail in any environment where `AI_DEV_FACTORY_RUNTIME_ROOT` is set (runtime clones, production deployments).

---

## Non-Blocking Observations

1. `deploy/.env` missing by default — documented in env.example; `docker compose config` fails without it. The user must run `cp deploy/env.example deploy/.env` before first use. README has no Docker setup section. Low severity (documented in env.example).

2. `.gitignore` has significant redundancy (entries repeated 3–5×). No functional impact.

3. Port 3000 hardcoded in docker-compose.yml; minor flexibility issue.

---

## Passing Tests

**Unit tests (145 passed)**:
```
tests/test_runtime_resolver.py     10 passed
tests/test_runtime_db.py           15 passed
tests/test_run_daemon.py           (minus 1 regression)
tests/test_daemon_issue_polling.py (minus 1 regression)
tests/test_intake_runtime_ignore.py  passed
... 145 total passed, 2 failed
```

**Container tests**:
- Docker build: **PASS** — multi-stage build produces `runtime` and `web` targets
- Bootstrap script: **PASS** — creates all 7 runtime subdirectories
- Bootstrap idempotency: **PASS** — safe to run twice
- Named volume persistence: **PASS** — data survives across containers
- Image upgrade persistence: **PASS** — new container reads old volume data
- RUNTIME_ROOT path resolution: **PASS** — `resolve_runs_dir()`, `resolve_worktrees_dir()` respect env var
- SQLite DB path from RUNTIME_ROOT: **PASS** — resolves to `RUNTIME_ROOT/.runtime/ai-dev-factory.sqlite`
- Source code isolation: **PASS** — image has source at `/app`, runtime at `/runtime`
- .dockerignore: **PASS** — excludes runtime state, caches, credentials from image

---

## Verdict

**IMPLEMENTATION_FIX_REQUIRED**

Three blocking issues must be resolved:

1. **ISSUE-1** (critical): Fix YAML command in `docker-compose.yml` so uvicorn binds `0.0.0.0:8080`
2. **ISSUE-2** (blocking): `git rm --cached` runtime state files (workers.json, daemon.log, sqlite, pyc) that are tracked in this branch
3. **ISSUE-3** (regression): Fix the 2 failing tests caused by `AI_DEV_FACTORY_RUNTIME_ROOT` overriding `--runs-dir`
