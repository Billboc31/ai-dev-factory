I now have a complete picture. Here is the implementation plan.

---

## Objective

Make environment deploy always execute committed scripts from a fresh clone of the selected branch (`<sandbox_dir>/source/.ai-dev-factory/scripts/`), never from the host ai-dev-factory checkout. Add a path validation guard that fails immediately if the resolved script root escapes the environment source directory.

## Included

**`services/control_api/services/sandbox_runtime_deploy.py`**

- `deploy_operational_runtime` (line 278): Remove the conditional `sandbox_dir / "source" if state.ref else project_root`. Always set `source_path = sandbox_dir / "source"`.
- `_clone_fresh_source` (line 194): Change `ref: str` → `ref: str | None`. When `ref` is `None`, omit `--branch` from the `git clone` command so the default branch is cloned. Remove the branch-mismatch check when `ref` is `None`.
- `deploy_operational_runtime` (lines 385–401): Change `if state.ref:` clone block to always clone (unconditionally call `_clone_fresh_source`; pass `ref=state.ref` which may be `None`).
- Add a path validation guard immediately after the clone and before `_run_scripts`: resolve `source_path` and assert it is a subpath of `sandbox_dir`; log `resolved script path: <source_path>/.ai-dev-factory/scripts/<script>.sh` for each required script; fail with a clear error message if any resolved path escapes `sandbox_dir`.

**`tests/test_sandbox_runtime_deploy.py`**

- Add test: when `state.ref` is `None`, `deploy_operational_runtime` still clones into `sandbox_dir/source/` and `_run_scripts` receives `sandbox_dir/source` as `worktree_path`.
- Add test: path validation guard fails immediately (returns `OperationalDeployResult(success=False)`) if the resolved script root escapes `sandbox_dir`.
- Update the existing `_sample_state` helper or add a variant that creates scripts inside `sandbox_dir/source/.ai-dev-factory/scripts/` to reflect the new clone-based source path.

## Excluded

- `deployer_runner.py` — uses `deploy.yml`-based component deploy, a separate flow not covered by this ticket.
- `run_sandbox.py` worktree-based validation flow — only used for `validation` mode; the `resolved script path:` log already exists there (line 688); no changes needed.
- Script generation (`run_scripts.py`) — scripts are already committed; generation is out of scope.
- UI / dashboard changes.
- Removing `state.ref` from the data model or changing the environment creation API schema.

## Acceptance criteria

- `deploy_operational_runtime` always sets `source_path = sandbox_dir / "source"` regardless of whether `state.ref` is set.
- Deploying with an explicit branch (`state.ref = "T170"`) clones that branch into `sandbox_dir/source/` and runs scripts from `sandbox_dir/source/.ai-dev-factory/scripts/`.
- Deploying without a branch (`state.ref = None`) clones HEAD into `sandbox_dir/source/` and runs scripts from `sandbox_dir/source/.ai-dev-factory/scripts/`.
- Log contains `resolved script path: <sandbox_dir>/source/.ai-dev-factory/scripts/<script>.sh` for each script before execution.
- If the path validation guard detects that `source_path` resolves outside `sandbox_dir`, `deploy_operational_runtime` returns `success=False` with a clear error and no script is executed.
- Existing test suite passes without modification beyond the new/updated tests described above.
- Host ai-dev-factory scripts (i.e., paths in `_REPO_ROOT / ".ai-dev-factory/scripts/"`) are never passed to `_run_scripts` during an environment deploy.
