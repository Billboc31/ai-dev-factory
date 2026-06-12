Now I have enough context to produce a precise, bounded plan.

## Objective
Move all host-filesystem and git-inspection logic out of the Control API and into the Supervisor, so that project import and bootstrap work correctly when the API runs in Docker and cannot access host paths like `/Users/...`.

## Included

**Supervisor (`services/supervisor/main.py`)**
- Add a new router section (or inline FastAPI routes) with four new endpoints:
  - `POST /projects/validate-path` — receives `{project_root: str}`, returns `{resolved_path, is_dir, is_git_repo, git_root}` or an explicit error
  - `POST /projects/inspect` — receives `{project_root: str}`, returns `{stack, git_root, repo_name}` (absorbs `stack_detector.py` logic executed on the host)
  - `POST /projects/bootstrap` — receives `{project_root, project_id, runtime_root}`, creates `.ai-dev-factory/project.yml` and the four runtime subdirs (`runs/`, `logs/`, `state/`, `worktrees/`); idempotent; returns `BootstrapResult`-equivalent payload
  - `GET /projects/path-info?path=...` — optional helper for UI path browsing (out of scope, listed here to avoid scope creep by implementers)
- Implement path-validation logic (exists, is_dir, realpath/resolve, symlink resolution, `.git` dir/file detection) in the supervisor, reusing or inlining the existing `git_root.py` logic
- Implement stack detection (currently in `stack_detector.py`) inside the supervisor bootstrap handler

**Control API — routes (`services/control_api/routes/projects.py`)**
- In `import_project()` (line 102–136): replace `Path(body.project_root).expanduser().resolve()` and `if not project_root.exists()` with a call to the supervisor `POST /projects/validate-path`
- Forward any validation error from the supervisor as an HTTP 422/400 to the caller

**Control API — service (`services/control_api/services/project_bootstrap.py`)**
- Replace the body of `bootstrap()` (lines 28–91) with a single HTTP call to the supervisor `POST /projects/bootstrap`
- Parse the response and return a `BootstrapResult` as before
- Keep `auto_bootstrap()` (lines 94–142) as a thin wrapper that calls the updated `bootstrap()`
- Remove direct use of `Path.mkdir`, `Path.write_text`, `Path.is_dir`, `Path.resolve` from this file

**Control API — stack detector (`services/control_api/services/stack_detector.py`)**
- Remove filesystem-reading stack detection; the stack value now comes from the supervisor `POST /projects/bootstrap` response
- File may be deleted or reduced to a pure-data constants file if nothing else uses it

**Control API — supervisor client**
- Add a `_call_supervisor` helper (or reuse the pattern from `daemon_manager.py:177–198`) in `project_bootstrap.py` or a shared `supervisor_client.py` for the three new project-oriented calls
- Must read `AI_DEV_FACTORY_SUPERVISOR_URL` env var (default `http://host.docker.internal:8090`)

**Schemas (`services/control_api/models/schemas.py`)**
- No new public-facing schemas required; the existing `ProjectImportRequest` and `BootstrapResult` remain unchanged

**Error mapping**
- Supervisor returns structured errors (`{"error": "path_not_found" | "not_a_directory" | "git_not_found" | "permission_denied" | "bootstrap_failed"}`) which the Control API translates to meaningful HTTP status codes

## Excluded

- Worktree creation/cleanup (separate supervisor endpoints already exist for sandbox lifecycle)
- Daemon start/stop (existing supervisor endpoints unchanged)
- Log file access (unchanged)
- Any changes to the multi-project workspace UI or project listing endpoints
- Path-browsing UI or autocomplete endpoint (`GET /projects/path-info`)
- Moving `project_id.py` validation or `assert_contained()` to the supervisor (they operate on already-resolved paths and are correct in both environments)
- Docker Compose or deployment configuration changes
- Changes to the auto-register flow for the factory's own repository (T186 work)

## Acceptance criteria

- `POST /projects/import` with a `/Users/...` path succeeds when the Control API is running inside a Docker container (the supervisor, running on the host, performs the filesystem check)
- `POST /projects/validate-path` on the supervisor returns a 200 with `is_git_repo: true` for a valid git directory, and a structured error for a non-existent path
- `POST /projects/bootstrap` on the supervisor is idempotent: running it twice for the same `project_id` does not fail or duplicate the `project.yml`
- `services/control_api/services/project_bootstrap.py` contains no `Path.mkdir`, `Path.is_dir`, `Path.resolve`, or `Path.write_text` calls
- `services/control_api/routes/projects.py` contains no `Path.exists()` or `Path.expanduser()` calls
- Existing imported projects (already in the registry) continue to return correct data from `GET /projects`
- The full multi-project workflow (import → bootstrap → daemon start → analysis) passes an end-to-end smoke test
