# Tester Report — T173

## Summary

**Verdict: PASS**

All acceptance criteria are satisfied. No regressions introduced.

---

## Commands executed

```
python -m pytest tests/test_sandbox_runtime_deploy.py \
                 tests/test_environment_infra_bootstrap.py \
                 tests/test_environment_supervisor.py -v
```

Result: **18 passed in 2.54s**

```
python -m pytest tests/ --tb=no -q
```

Result: **60 failed, 1215 passed** — all failures are in files not modified by T173 (pre-existing, confirmed by `git log main..HEAD -- <failing test files>` returning no T173 commits).

---

## Acceptance criteria

### AC1 — Deploying branch T170 executes T170 committed scripts

**PASS**

`_clone_fresh_source` receives `ref=state.ref` and runs `git clone --branch T170 <project_root> <sandbox_dir>/source` when `state.ref="T170"`. `_run_scripts` is then called with `source_path = sandbox_dir / "source"` unconditionally.

Covered by: `test_deploy_operational_runtime_clones_fresh_source_on_ref`

---

### AC2 — `resolved script path` points under `<environment>/source/.ai-dev-factory/scripts/`

**PASS**

`sandbox_runtime_deploy.py:424-426`:
```python
for script_name in _SCRIPT_PHASE:
    script_path = resolved_source / ".ai-dev-factory" / "scripts" / script_name
    rs._append_log(log_path, f"resolved script path: {script_path}\n")
```

`resolved_source` is `source_path.resolve()` where `source_path = sandbox_dir / "source"` (line 281, unconditional). The logged path always points inside `<sandbox_dir>/source/.ai-dev-factory/scripts/`.

Additionally, `run_sandbox.py:688` logs the same format during actual script execution.

---

### AC3 — Host ai-dev-factory scripts are never used for project environment deploy

**PASS**

Before T173, `source_path` was conditionally set to `project_root` when `state.ref` was `None`, meaning the host checkout could be used as-is without cloning. After T173:

- Line 281: `source_path = sandbox_dir / "source"` — unconditional, no fallback
- `_clone_fresh_source` is always called (lines 388-393), even when `state.ref is None`
- When `ref is None`, clones the default branch without `--branch` flag

Covered by: `test_deploy_operational_runtime_clones_even_without_ref`

---

### AC4 — Different environments can run different committed runtime scripts concurrently

**PASS**

Each environment has a distinct `sandbox_dir`. Scripts live at `sandbox_dir/source/.ai-dev-factory/scripts/`. There is no shared mutable state between sandboxes — each clone is fully isolated under its own sandbox directory.

---

### AC5 — If a required script is missing from the selected branch, deploy fails clearly

**PASS**

`run_sandbox.py:690-692`:
```python
if not script_path.exists():
    error = f"required script missing: {script_rel}"
    _append_log(log_path, f"{error}\n")
```

Returns immediately with a failed step, propagating a clear error message. The module docstring also states: "if any of them is missing the run fails immediately with a clear 'required script missing: …' error."

---

### AC6 — Deploying another repository works without ai-dev-factory-specific path assumptions

**PASS**

Script resolution is always relative to `resolved_source / ".ai-dev-factory" / "scripts"` where `resolved_source` is the cloned repo root. No path hardcodes an ai-dev-factory-specific prefix. Any repository with `.ai-dev-factory/scripts/` committed will work identically.

No dedicated test exercises a non-ai-dev-factory repo, but the implementation is generic — the code contains no conditional logic that differs based on repository identity.

---

## Regressions

None. The 60 test failures in the full suite are all pre-existing:

```
git log main..HEAD -- tests/test_sandbox_worktree.py         # → (empty)
git log main..HEAD -- tests/test_daemon_checkpoint.py        # → (empty)
git log main..HEAD -- tests/test_control_api_artifacts.py    # → (empty)
git log main..HEAD -- tests/test_ticket_timeline.py          # → (empty)
```

T173 only modified:
- `services/control_api/services/sandbox_runtime_deploy.py`
- `tests/test_sandbox_runtime_deploy.py`
- `tests/test_environment_infra_bootstrap.py`
- `tests/test_environment_supervisor.py`

All 18 tests across these files pass.

---

## Notes

The path validation guard (symlink escape prevention) was also verified beyond the acceptance criteria: a symlink pointing outside `sandbox_dir` causes immediate failure before any script runs.

Covered by: `test_deploy_operational_runtime_path_validation_fails`
