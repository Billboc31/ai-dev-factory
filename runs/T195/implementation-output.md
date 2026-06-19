Implementation complete. Here's the summary:

---

**Files modified:**

- `tools/agent_runner/run_step.py`
  - `compose_runtime_prompt` gains a `project_root: Path | None = None` parameter. A new `_resolve(rel)` inner function checks `project_root / rel` first; falls back to `Path(rel)` (factory-relative CWD) when absent or when `project_root` is `None`. Applied to global-context, role file, and all skill files.
  - `parse_args` gains `--project-root` argument.
  - `main` reads `args.project_root` and passes it to `compose_runtime_prompt`.

- `tools/agent_runner/run_ticket.py`
  - `_call_run_step` gains `project_root: Path | None = None`; passes `--project-root` to the `run_step.py` subprocess when set.
  - `execute_once` gains `project_root: Path | None = None`; passes `--project-root` to subprocess when set.
  - `auto_run` gains `project_root: Path | None = None`; threads it into `_call_run_step`.
  - `parse_args` gains `--project-root` argument.
  - `main` reads `args.project_root` and passes to `auto_run` / `execute_once`.

**File created:**

- `tests/test_run_step_project_root.py` — 10 tests covering: project_root global-context preferred, fallback to factory, no project_root unchanged, role preferred/fallback, skill preferred/fallback, task always included, CLI `--project-root` flag with and without project context.

**Result:** 1312 passed (10 new), no regressions.
