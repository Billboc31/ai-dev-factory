---

## Test Report Summary

**Verdict: IMPLEMENTATION_FIX_REQUIRED**

Two blocking issues prevent the primary acceptance criterion from passing.

---

### Blocking Issues

**ISSUE-1 (CRITICAL) — API not accessible externally**

The YAML `>` folded block scalar in `docker-compose.yml` does not collapse newlines when sub-lines are more-indented than the first content line. Docker Compose resolves the command to a multiline shell script, so `--host 0.0.0.0` and `--port 8080` land on separate lines. The shell runs uvicorn without those flags, which defaults to `127.0.0.1:8000`. Port 8080 has nothing listening; all external requests get "connection reset".

**Fix** (one line in `docker-compose.yml`):
```yaml
command: sh -c "/app/deploy/bootstrap.sh && python -m uvicorn services.control_api.main:app --host 0.0.0.0 --port 8080"
```

**ISSUE-2 (BLOCKING) — `docker compose up` fails without `deploy/.env`**

`docker-compose.yml` requires `env_file: deploy/.env` but this file is gitignored and never created. Every `docker compose` command fails immediately with a file-not-found error. The README has no Docker setup instructions at all.

**Fix**: Add a Docker setup section to README.md with `cp deploy/env.example deploy/.env` as step one.

---

### Passing Criteria

- Named volume correctly persists runtime state across container restarts and `--force-recreate` (simulating image upgrades) ✓
- Bootstrap creates all required `/runtime/` subdirectories idempotently ✓
- Runtime data goes to `/runtime/` volume; source code is never modified ✓
- All daemon API endpoints are implemented and return correct JSON ✓
- Worktrees persist across restarts ✓

The full test report is at `runs/T115/tester-report.md`.
