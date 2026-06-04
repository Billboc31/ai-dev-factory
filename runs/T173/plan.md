Now I have a clear picture of the codebase. Let me write the plan.

---

## Objective

Guarantee that environment deployments exclusively run scripts committed under `.ai-dev-factory/scripts/` in the cloned source branch, and never silently fall back to host/global paths. Two targeted gaps must be closed: (1) `deploy_operational_runtime()` must reject deployments without a `ref` rather than falling back to `project_root`; (2) `_run_scripts()` must assert that every resolved script path stays within the declared source directory before executing.

## Included

**`services/control_api/services/sandbox_runtime_deploy.py`**

- In `deploy_operational_runtime()`, replace the implicit `project_root` fallback (line 278: `source_path = sandbox_dir / "source" if state.ref else project_root`) with an explicit fail-fast guard: when `mode == "environment"` and `state.ref` is empty/None, abort immediately with a clear error — e.g. `"environment deploy requires a ref (branch); refusing to run scripts from project_root"`. For non-environment modes (e.g. `"validation"`), the existing fallback to `project_root` is acceptable and must be kept.

**`tools/agent_runner/run_sandbox.py`**

- In `_run_scripts()`, immediately after the existing `resolved script path` log line (line 688), add a path boundary assertion: resolve both `source_dir` (`worktree_path.resolve()`) and `script_path.resolve()`, then verify `script_path.resolve().is_relative_to(source_dir)`. If the check fails → return `(False, "resolved script path escapes source directory: <path>", steps)` without executing the script. This is a defence-in-depth guard; it catches any future regression where a script name or path component could escape the source tree.

**`runs/T173/prompts/plan.md`** (new file)

- Write this plan to that path as the versioned plan artefact.

## Excluded

- The supervisor bug (`main.py:658,799` calling the non-existent `create_with_worktree()`) — that affects analysis/scripts jobs, not environment deploy; it is a separate ticket.
- `run_sandbox.py`'s `_do_sandbox()` validation-sandbox path — it already creates an isolated worktree from the project repo; it is not the environment deploy code path.
- Script generation (`run_scripts.py`) — scripts are generated once and committed; this ticket explicitly forbids regenerating during deploy.
- Docker Compose, network, port, or proxy configuration — unrelated to script path resolution.
- `SandboxState` model changes — `state.ref` already exists and is populated by callers.

## Acceptance criteria

- Deploying an environment with a valid `ref` (e.g. `T170`) clones the branch and logs `resolved script path: <sandbox_dir>/source/.ai-dev-factory/scripts/<script>.sh` for every script before it runs.
- Deploying an environment with `state.ref = None` or `state.ref = ""` fails immediately with a message containing `"environment deploy requires a ref"` — no script is executed.
- If any resolved script path does not resolve to a path under `<sandbox_dir>/source/`, deploy fails immediately with a message containing `"resolved script path escapes source directory"`.
- If a required script (e.g. `bootstrap.sh`) is absent from the cloned branch, deploy fails clearly with `"required script missing"` (existing behaviour, verified unchanged).
- Two concurrent environment deploys on different branches each resolve and execute their own committed scripts independently — confirmed by log inspection.
- Non-environment deploy modes (e.g. `mode="validation"`) are unaffected; they continue to use `project_root` when `state.ref` is absent.
