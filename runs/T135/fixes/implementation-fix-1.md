# Fix artifact — IMPLEMENTATION_FIX_REQUIRED

- decision: IMPLEMENTATION_FIX_REQUIRED
- review source: runs/T135/reviews/implementation-review.md
- generated at: 2026-05-22T06:58:56Z

---

The ambiguity is confirmed. Now I'll write the structured review.

---

# PR Review — T135: Isolated analysis and deploy worktrees

## Résumé

The implementation delivers the V1 scope correctly: isolated analysis worktrees, Docker-to-host path mapping in the supervisor, worktree cleanup, state visibility through the dashboard, and test coverage for the two new features. Backwards compatibility is preserved via the optional `--worktrees-dir` argument. One correctness bug in the path mapper requires a fix before approval.

---

## Vérifications effectuées

- `services/supervisor/path_mapper.py` — new file, full read
- `services/supervisor/main.py` — diff reviewed (mapper import, `/analysis/start`, `/supervisor/status`, `--worktrees-dir` forwarding)
- `tools/agent_runner/run_analysis.py` — diff reviewed (new arg, worktree lifecycle, `write_root` redirection, path escape check, `finally` cleanup)
- `tools/agent_runner/worktree_manager.py` — full read (pre-existing, reused unchanged)
- `services/control_api/models/schemas.py` — `AnalysisStatus.worktree_path` addition
- `apps/dashboard/src/pages/DeployerPage.jsx` — `AnalysisStatusPanel` addition
- `tests/test_host_path_mapping.py` — 4 unit tests
- `tests/test_analysis_worktree_isolation.py` — 5 integration tests
- `runs/T135/plan.md` — plan vs implementation cross-check
- Git diff `main...HEAD` to confirm scope bounds

---

## Points validés

- **Path mapping**: `ContainerToHostMapper` is instantiated at module load, applied in `/analysis/start` before subprocess launch, and exposed in `/supervisor/status`. Matches plan §2.
- **Analysis worktree isolation**: `run_analysis.py` creates a timestamped `analysis/{job_id}` worktree, redirects all file writes and `commit_and_push` to `write_root`, and removes the worktree in `finally` on both success and failure paths. Matches plan §3–4.
- **Path escape hardening** (`run_analysis.py:219`): LLM-generated paths are validated against `write_root` before write — correct security measure.
- **Backwards compatibility**: `--worktrees-dir` is optional; when absent, `write_root = project_root` and no worktree is created. Existing tests remain unaffected.
- **Schema**: `AnalysisStatus.worktree_path: str | None = None` is a non-breaking additive change.
- **Dashboard**: `AnalysisStatusPanel` renders worktree path and hides when `null`. Matches plan §5.
- **Test coverage**: `test_host_path_mapping.py` covers all four mapper cases; `test_analysis_worktree_isolation.py` covers worktree creation, file isolation, success cleanup, failure cleanup, and state JSON. Matches plan §6.
- **Scope compliance**: `run_scripts.py` isolation, compose project names, dynamic ports, cleanup endpoints, retry loop, and production deployment are all absent — matching the explicit V1 exclusions.

---

## Problèmes détectés

### [BLOCKING] Path prefix ambiguity in `ContainerToHostMapper.map()` — `path_mapper.py:18`

```python
if path.startswith(self.container_root):
```

Raw string `.startswith()` does not respect path separator boundaries. If `CONTAINER_RUNTIME_ROOT=/app`, the path `/applications/foo` matches and is incorrectly translated to `{HOST_RUNTIME_ROOT}lications/foo`. This violates the acceptance criterion "supervisor always receives valid host paths".

Verified:
```
'/applications/foo'.startswith('/app') = True   # incorrectly matches
```

**Fix required** — replace with:
```python
if path == self.container_root or path.startswith(self.container_root + "/"):
```

The existing test `test_unrelated_path_not_mutated` passes only because `/other/path` does not share a prefix with `/app`; there is no test for the ambiguous case.

---

## Risques éventuels (non bloquants)

1. **Scripts path not mapped** (`main.py:639-645`): `scripts_start` passes `body.project_root` to the subprocess without `mapper.map()`. This is explicitly excluded from V1 scope, but it means scripts jobs launched from a container context will receive container-internal paths. Should be addressed in V2 or documented.

2. **Local analysis branches accumulate**: `remove_ticket_worktree` removes the worktree directory but not the local git branch (`analysis/{job_id}`). After many analysis runs, local branches pile up. The `cleanup_failed_intake` helper (pre-existing) handles both; the analysis path could use a similar approach, or a periodic cleanup routine.

3. **No `fetch_origin_main` before branch creation**: `create_ticket_branch_and_worktree` branches from `origin/main` without fetching first. This is pre-existing behavior, not introduced here. For analysis jobs this is low risk (the branch is only used for file writes, not for running the analysed project), but worth noting for future iterations.

4. **Unusual test lambda** (`test_analysis_worktree_isolation.py:104`): `(_ for _ in ()).throw(RuntimeError("LLM failed"))` is functionally correct but non-obvious. A plain `def` raising helper would be clearer.

---

## Décision

- REQUEST_CHANGES — one blocking fix required before approval

## Actions demandées

1. **[Required]** Fix `path_mapper.py:18` — change `path.startswith(self.container_root)` to `path == self.container_root or path.startswith(self.container_root + "/")`. Add a test case for the ambiguous-prefix scenario (e.g., `CONTAINER_RUNTIME_ROOT=/app`, path=`/applications/foo` → identity, not mapped).

---

IMPLEMENTATION_FIX_REQUIRED
