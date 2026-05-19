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
  → intake (_intake worktree, main branch)
  → ticket worktree created (worktrees/TXXX/)
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

The daemon is launched from the dashboard (POST /daemon/start) or restart endpoint. The control API calls `daemon_manager.start(project_root, exec_cmd)` which spawns `run_daemon.py` as a background subprocess with these flags:

```
run_daemon.py
  --exec-cmd <exec_cmd>
  --poll-issues
  --issue-label ai-ready
  --auto-commit
  --auto-push
  --worktrees-dir <project_root>/worktrees
```

- `--auto-commit` / `--auto-push`: checkpoint runtime artifacts after each step and push to the ticket branch
- `--worktrees-dir`: canonical path for per-ticket worktrees (fallback when `AI_DEV_FACTORY_RUNTIME_ROOT` is not set)

The daemon PID is written to `runs/daemon.pid`. Stdout/stderr are appended to `runs/daemon.log`.

---

## Per-Cycle Loop

Each daemon cycle (default: 30s interval):

1. **Poll GitHub issues** (if `--poll-issues`): fetch open issues with label `ai-ready`, skip already-ingested ones, run intake for at most one new issue per cycle.
2. **Scan tickets**: read `runs/*/state.json` and active worktrees to build the current ticket/state map.
3. **Process tickets**: for each auto-runnable ticket, launch `run_ticket.py --auto` inside its worktree.
4. **TEST_COMPLETE lifecycle**: for tickets at `TEST_COMPLETE`, trigger checkpoint → PR create/update → auto-merge → issue close.

---

## Issue Intake

When a new issue is detected:

1. `ensure_intake_worktree()` verifies `worktrees/_intake` exists and forces `git checkout -f main` to prevent lingering ticket branches.
2. `git pull --ff-only origin main` brings the worktree up to date.
3. `run_issue_intake.py` runs inside `_intake`: creates the ticket branch, writes `ticket.md` and `state.json`, commits bootstrap checkpoint, pushes.
4. `create_ticket_worktree()` creates `worktrees/TXXX/` on the ticket branch.

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
| `worktrees/_intake/` | Shared intake worktree on `main` |
| `worktrees/TXXX/` | Per-ticket isolated worktree |
