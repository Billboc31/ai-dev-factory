---

## Test Report — T115 Docker Compose Runtime

**Verdict: IMPLEMENTATION_FIX_REQUIRED**

Three blocking issues found. The previous `IMPLEMENTATION_APPROVED` checkpoint was premature — the original critical YAML bug was never actually fixed.

---

### Blocking Issues

**ISSUE-1 (CRITICAL) — Uvicorn binds 127.0.0.1:8000, not 0.0.0.0:8080**

The YAML `>` folded scalar in `docker-compose.yml` preserves newlines for more-indented lines. Docker Compose shell-splits the result and passes a multi-line script to `sh -c`. The shell runs `python -m uvicorn` without `--host`/`--port` flags; uvicorn defaults to `127.0.0.1:8000`. Port 8080 has nothing listening — API is inaccessible.

Confirmed by running the container: `Uvicorn running on http://127.0.0.1:8000`.

The fix commit (`0188de4`) only removed the `daemon` service — it did not fix the `api` service command.

**Fix** (`docker-compose.yml:14`):
```yaml
command: sh -c "/app/deploy/bootstrap.sh && python -m uvicorn services.control_api.main:app --host 0.0.0.0 --port 8080"
```

---

**ISSUE-2 (BLOCKING) — Runtime state files tracked in git on this branch**

Files present in the T115 branch but NOT in `main`:
- `runs/workers.json`, `runs/daemon.log`, `.runtime/ai-dev-factory.sqlite` — added by checkpoint commits in this worktree
- 51 `__pycache__/*.pyc` files (branch diff vs main)

The `.gitignore` rules are correct and block NEW additions, but the existing tracked files were not untracked. Fix commit only cleaned 2 specific `.pyc` files.

**Fix**: `git rm --cached runs/workers.json runs/daemon.log .runtime/ai-dev-factory.sqlite` + rm cached on all `__pycache__` dirs

---

**ISSUE-3 (REGRESSION) — `AI_DEV_FACTORY_RUNTIME_ROOT` silently overrides `--runs-dir`, breaking 2 tests**

When `AI_DEV_FACTORY_RUNTIME_ROOT` is set (as in any runtime clone), `run_daemon.py` ignores the `--runs-dir` CLI argument entirely. Two tests fail:
- `test_main_returns_2_when_runs_dir_missing` — expects rc=2 for nonexistent path; gets rc=0 because real runtime is used
- `test_main_poll_issues_flag_calls_poll_before_run_once` — mock path assertion fails

**Fix**: Tests need `monkeypatch.delenv("AI_DEV_FACTORY_RUNTIME_ROOT", raising=False)` in setup.

---

### Passing Criteria

- Docker build (multi-stage): PASS
- Bootstrap script + idempotency: PASS
- Named volume persistence across restarts: PASS
- Named volume persistence after image upgrade: PASS
- `RUNTIME_ROOT` env var controls path resolution: PASS
- SQLite DB resolves from `RUNTIME_ROOT`: PASS
- Source code isolation (app ≠ runtime): PASS
- `.dockerignore` excludes runtime state: PASS
- Multi-instance multi-project support: PASS
- 145 unit tests pass (2 regression failures)

Report written to `runs/T115/tests/tester-report-attempt-2.md`. State updated to `IMPLEMENTATION_FIX_REQUIRED`.
