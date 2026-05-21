# Daemon Lifecycle

## Overview

The ai-dev-factory daemon is a host-side process that runs in a **runtime clone** (separate from the human development clone). It polls GitHub issues and ticket states, then drives the autonomous workflow from intake to `TEST_COMPLETE`.

The daemon must **never run in a human clone**. It requires either:
- `.ai-dev-factory-runtime` sentinel file at the repo root, OR
- `AI_DEV_FACTORY_RUNTIME_ROOT` environment variable

---

## Expected Workflow

```
GitHub issue (label: ai-ready)
  → ephemeral intake (fetch origin/main, branch + worktrees/TXXX/ created directly)
  → planner step (AUTO_RUNNABLE: INIT)
  → PLAN_REVIEW_NEEDED  ← human gate (checkpoint pushed for visibility)
  → human approves plan (sets state to PLAN_APPROVED)
  → coder step (AUTO_RUNNABLE: PLAN_APPROVED)
  → reviewer step (AUTO_RUNNABLE: IMPLEMENTATION_REVIEW_NEEDED)
  → tester step (AUTO_RUNNABLE: IMPLEMENTATION_APPROVED)
  → TEST_COMPLETE  ← PR lifecycle triggered automatically
  → PR created/updated, auto-merged if clean
  → issue closed, ai-ready label removed
```

Only **one mandatory human gate**: `PLAN_REVIEW_NEEDED`.

---

## Daemon Start

The daemon is launched from the dashboard (POST /daemon/start) or restart
endpoint. The control API calls `daemon_manager.start(project_root, exec_cmd)`
which dispatches to one of three paths.

### Architecture: host-side daemon, Dockerized API

The dashboard and control API run inside Docker. The daemon runs on the host
because it needs `gh`, `claude`, the host Python venv, and direct access to
the git worktrees. **The dashboard's Start button never spawns the daemon
inside the API container.**

`daemon_manager.start` picks one of three paths in this order:

| Condition | Behavior |
| --- | --- |
| `AI_DEV_FACTORY_HOST_DAEMON_COMMAND` is set | Run that shell command verbatim (typically an `ssh host -- '…'` wrapper). The host process writes its own `runs/daemon.pid`. The API does not preflight the container's environment. |
| API in Docker, no host launcher | Refuse with `ok=False` and populate the `host_command` field with a copy-paste command for the operator. **No PID file is written.** The dashboard displays the command in a yellow copy block. |
| API on host (no Docker, no override) | Run the preflight described below, then `Popen` the daemon as a local subprocess. |

Docker detection signals (any one triggers Docker mode):

1. `AI_DEV_FACTORY_API_IN_DOCKER=1` env var (set by `docker-compose.yml`),
2. `/.dockerenv` file exists (Docker sentinel),
3. `/proc/1/cgroup` mentions `docker` or `containerd`.

Configure the host launcher with `AI_DEV_FACTORY_HOST_DAEMON_COMMAND`, e.g.
in `deploy/.env`:

```
AI_DEV_FACTORY_HOST_DAEMON_COMMAND=ssh host -- 'cd ~/runtime/ai-dev-factory/clones/ai-dev-factory && source .venv/bin/activate && python tools/agent_runner/run_daemon.py --exec-cmd "claude --dangerously-skip-permissions" --poll-issues --issue-repo <owner>/<repo> --auto-commit --auto-push --auto-include-code --interval 30'
```

Without it, operators copy the command from the dashboard's yellow banner and
run it in a host terminal.

### Host-mode preflight

When the API runs directly on the host:

1. **`check_environment(project_root)`** — a strict preflight that records
   every fact (project_root, cwd, runtime_root, runs_dir, worktrees_dir,
   logs_dir, python, git_path, gh_path) and **refuses** the launch when:
   - `gh` is missing from PATH,
   - `git` is missing from PATH,
   - `project_root` is not a git working tree (no `.git` and `git rev-parse`
     fails),
   - `runs_dir` cannot be written to.
   On refusal, the environment banner and each `ERROR:` line are appended
   to `runs/daemon.log` so the dashboard's `/daemon/activity` endpoint
   surfaces the cause; **no PID file is written**. The dashboard therefore
   never reports a degraded daemon as "running".

2. **Spawns** `run_daemon.py` as a *local* background subprocess with these
   flags (host-mode only — Docker mode delegates to the host launcher):

```
run_daemon.py
  --exec-cmd <exec_cmd>
  --poll-issues
  --issue-label ai-ready
  --auto-commit
  --auto-push
  --auto-include-code         # always stage real code, not just runs/<TID>/
  --worktrees-dir <facts.worktrees_dir>
```

The daemon process itself logs a boot banner at startup with the same
facts, plus a `git rev-parse --show-toplevel` check and a fatal-fail if
`gh` is required but missing.

- `--auto-commit` / `--auto-push`: checkpoint runtime artifacts and code after each step and push to the ticket branch
- `--auto-include-code`: required for the coder's real implementation
  files (apps/, services/, …) to be committed alongside `runs/<TID>/`
- `--worktrees-dir`: canonical path for per-ticket worktrees (fallback when `AI_DEV_FACTORY_RUNTIME_ROOT` is not set)

The daemon PID is written to `runs/daemon.pid` only on a successful spawn. Stdout/stderr are appended to `runs/daemon.log` (the daemon process itself avoids double-writing the same line — `_log` only mirrors to the log file when running interactively, i.e. with a TTY stdout).

### Overriding `project_root` from the environment

When the API runs in a container whose CWD is *not* a git working tree
(e.g. Docker `working_dir: /app` without `.git` mounted), set
`AI_DEV_FACTORY_PROJECT_ROOT` to the path of the host clone that *is*
mounted into the container. `create_app()` reads this variable before
falling back to `Path.cwd()`.

---

## Per-Cycle Loop

Each daemon cycle (default: 30s interval):

1. **Poll GitHub issues** (if `--poll-issues`): fetch open issues with label `ai-ready`, skip already-ingested ones, run intake for at most one new issue per cycle.
2. **Scan tickets**: read `runs/*/state.json` and active worktrees to build the current ticket/state map.
3. **Process tickets**: for each auto-runnable ticket, launch `run_ticket.py --auto` inside its worktree.
4. **TEST_COMPLETE lifecycle**: for tickets at `TEST_COMPLETE`, trigger checkpoint → PR create/update → auto-merge → issue close.

---

## Issue Intake (ephemeral)

Intake is fully ephemeral — there is **no persistent `_intake` worktree**. When a new issue is detected the daemon runs:

1. `fetch_origin_main(REPO_ROOT)` — pure ref operation (`git fetch origin main`), does not touch any branch or working tree.
2. `create_ticket_branch_and_worktree(ticket_id, branch, worktrees_dir, REPO_ROOT)` — atomically creates the ticket branch from `origin/main` and adds `worktrees/TXXX/` on that branch. If the worktree add fails the branch ref is rolled back.
3. `run_issue_intake.py` runs **inside the new `worktrees/TXXX/`** which is already on the ticket branch: writes `ticket.md` + `state.json`, commits the bootstrap checkpoint, pushes.
4. On any failure during the intake call, `cleanup_failed_intake(...)` removes the worktree and deletes the branch so the next daemon cycle can retry from scratch.

There is no return-to-main checkout, no shared `_intake` worktree, and no `runs/TXXX/runtime.log` produced during intake — the per-ticket runtime.log is created later by `run_ticket.py`.

### runtime.log and intake preflight

`runtime.log` is **excluded from all git operations**. It is never staged, never committed, never checked out. The intake preflight (`check_working_tree_clean`) classifies it as an ignorable runtime path. `_cleanup_ignorable_runtime_paths` skips `git checkout HEAD` for untracked files (checked via `git ls-files --error-unmatch`).

---

## Worktree-Based Execution

Each ticket runs in isolation inside its own worktree (`worktrees/TXXX/`).

- The daemon acquires a `daemon.lock` inside the worktree's `runs/TXXX/` before launching a worker.
- Branch sync uses `git pull --rebase origin <branch>` to handle non-fast-forward cases without aborting.
- If `worktrees_dir` is set but the worktree is absent, the daemon attempts **on-demand creation** before each launch. If creation fails, the ticket is skipped — no legacy single-repo fallback.

---

## Checkpoint Lifecycle

After each successful workflow step:

- `run_ticket.py --auto-commit --auto-push` commits and pushes `runs/TXXX/` artifacts.
- runtime.log is **never included** in checkpoint commits (excluded by `collect_runtime_artifacts`).
- At `PLAN_REVIEW_NEEDED`, the daemon triggers an additional checkpoint push so the plan is visible on the remote before the human reviews it.
- At `TEST_COMPLETE`, the daemon does a final checkpoint push before creating the PR.

---

## Human Gate: PLAN_REVIEW_NEEDED

The daemon detects `PLAN_REVIEW_NEEDED` and:
1. Triggers a checkpoint commit + push (so the plan is visible in the PR/branch).
2. Logs `skipping <ticket>: human gate` and does not advance the ticket.

A human must review `runs/TXXX/plan.md` and update `state.json` to `PLAN_APPROVED`. Everything after that runs automatically.

---

## Failure and Retry

Failures are classified from `runtime.log` (pattern: `runtime failure: <class>`):

| Class | Policy |
|---|---|
| `quota_exceeded` | cooldown 1h |
| `provider_error` | exponential backoff, max 5 retries, then 1h cooldown |
| `process_crashed` | exponential backoff, max 5 retries, then 1h cooldown |
| `process_failed` | fixed delay 5m, max 3 retries |
| `empty_output` | fixed delay 5m, max 3 retries |
| `write_permission_missing` | stop (requires human attention) |
| `unknown` | stop (requires human attention) |

Retry state is persisted in `runs/TXXX/retry-state.json`.

---

## Daemon Stop / Restart

- **Stop**: sends SIGTERM to the daemon PID, removes `runs/daemon.pid`.
- **Restart**: stop + start (tolerates "not running" on stop).
- The daemon exits cleanly on SIGTERM / KeyboardInterrupt.

---

## Files

| Path | Purpose |
|---|---|
| `runs/daemon.pid` | PID + start timestamp (JSON) |
| `runs/daemon.log` | Daemon stdout/stderr log |
| `runs/.issue-intake.json` | Anti-duplicate issue index |
| `runs/workers.json` | Active worker registry |
| `runs/TXXX/state.json` | Ticket workflow state |
| `runs/TXXX/runtime.log` | Per-ticket step logs (never committed) |
| `runs/TXXX/daemon.lock` | Per-ticket execution lock |
| `runs/TXXX/retry-state.json` | Retry/cooldown state |
| `worktrees/TXXX/` | Per-ticket isolated worktree (created directly by ephemeral intake, no shared `_intake`) |
