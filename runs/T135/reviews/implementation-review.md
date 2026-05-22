I have a complete picture of the implementation. Let me write the review.

---

# PR Review — T135: Isolated analysis and deploy worktrees (attempt 2)

## Résumé

This is a re-review after the coder applied the single blocking fix requested in attempt 1 (path prefix ambiguity in `ContainerToHostMapper`). The fix was applied correctly and a test was added for the ambiguous-prefix case. The V1 scope is fully delivered: Docker-to-host path mapping, isolated analysis worktrees, cleanup, state visibility, and test coverage.

---

## Vérifications effectuées

- `services/supervisor/path_mapper.py` — full read, fix verified
- `services/supervisor/main.py` — lines 31–33 (mapper instantiation), 402–407 (status endpoint), 524–538 (mapping + `--worktrees-dir` forwarding)
- `tools/agent_runner/run_analysis.py` — full read
- `tools/agent_runner/worktree_manager.py` — full read
- `services/control_api/models/schemas.py` — `AnalysisStatus.worktree_path` addition
- `apps/dashboard/src/pages/DeployerPage.jsx` — lines 96–98
- `tests/test_host_path_mapping.py` — 5 unit tests (was 4 pre-fix)
- `tests/test_analysis_worktree_isolation.py` — 5 integration tests
- Previous review (`runs/T135/reviews/implementation-review.md`) — cross-checked all blocking and non-blocking items
- `runs/T135/plan.md` and `runs/T135/reviews/plan-review.md` — confirmed scope reduction was explicitly approved

---

## Points validés

**Blocking fix from attempt 1 correctly applied:**
- `path_mapper.py:18` now reads `path == self.container_root or path.startswith(self.container_root + "/")` — exact fix requested
- `test_ambiguous_prefix_not_mapped` added to `tests/test_host_path_mapping.py` — the case `CONTAINER_RUNTIME_ROOT=/app`, path=`/applications/foo` → identity, as required

**Full V1 scope delivered:**
- `ContainerToHostMapper` instantiated at module load (`main.py:33`), applied in `/analysis/start` (`main.py:524`), exposed in `/supervisor/status` (`main.py:402–407`)
- `run_analysis.py` derives a timestamped `job_id`, creates an isolated `analysis/{job_id}` worktree, redirects all writes and `commit_and_push` to `write_root`, and removes the worktree in `finally` on both success and failure paths
- LLM path-traversal guard (`run_analysis.py:219`) uses the correct boundary check (`str(write_root) + "/"`) — consistent with the same fix applied to the mapper
- `--worktrees-dir` is optional with `default=None`; when absent, `write_root = project_root` and no worktree lifecycle runs — full backwards compatibility preserved
- `AnalysisStatus.worktree_path: str | None = None` is additive and non-breaking
- Dashboard `AnalysisStatusPanel` renders the field conditionally when non-null
- Scope correctly excludes `run_scripts.py` isolation, compose names, ports, retry loop, production deploy — matching the approved plan exclusions

---

## Problèmes détectés

### [Non-blocking] `remove_ticket_worktree` has no `repo_root` parameter — `worktree_manager.py:188`

The `git worktree remove` call runs without an explicit `cwd`. It works in production because the supervisor spawns `run_analysis.py` with `cwd=_project_root()`, so the subprocess inherits a valid git context. However the function signature is inconsistent with `create_ticket_branch_and_worktree`, which does accept `repo_root`. If called from a different CWD (e.g. future test without the mock), it would silently fail with an unrelated git error. Recommend adding `repo_root` parameter for symmetry in a follow-up.

### [Non-blocking] Analysis branches accumulate — `worktree_manager.py:205`

`remove_ticket_worktree` deletes the worktree directory but not the local git branch (`analysis/{job_id}`). After many analysis runs, local branches pile up. `cleanup_failed_intake` (pre-existing) handles both worktree and branch removal; the analysis path could use a similar approach. Raised in the previous review, still present — acceptable for V1.

### [Non-blocking] Stale `worktree_path` in state JSON after cleanup

The success/failure state is written to JSON before the `finally` block removes the worktree. After cleanup completes, `state.worktree_path` points to a directory that no longer exists. The dashboard could display a stale path after job completion. No functional impact, but a future iteration should either clear the field post-cleanup or rename it to `worktree_path_was` to indicate historical context.

### [Non-blocking] Scripts path not mapped — `main.py` scripts_start endpoint

`scripts_start` passes `body.project_root` to its subprocess without `mapper.map()`. Flagged in the previous review, explicitly deferred to V2 per approved scope — noted for completeness.

---

## Décision

The one blocking fix requested in the previous review is correctly applied. All previously validated points remain correct. No new blocking issues were found. Non-blocking observations are carried forward for V2.

IMPLEMENTATION_APPROVED
