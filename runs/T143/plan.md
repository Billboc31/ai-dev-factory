Here is the plan:

---

## Objective

Add a conflict resolver agent workflow that detects when a PR branch conflicts with main, collects full ticket context, rebases in the existing ticket worktree, resolves conflicts via an AI agent, runs tests, and pushes the resolved branch with `--force-with-lease` — gated by mandatory human review before the ticket workflow resumes.

## Included

### 1. New workflow states — `tools/agent_runner/run_ticket.py`

- Add to `VALID_STATES`: `CONFLICT_RESOLUTION_NEEDED`, `CONFLICT_RESOLVING`, `CONFLICT_RESOLVED_REVIEW_NEEDED`, `CONFLICT_RESOLUTION_FAILED`.
- Add to `TRANSITIONS`:
  - `CONFLICT_RESOLUTION_NEEDED` → `("conflict-resolver", True, ["CONFLICT_RESOLVED_REVIEW_NEEDED", "CONFLICT_RESOLUTION_FAILED"])`
  - `CONFLICT_RESOLVED_REVIEW_NEEDED` → `("review", False, ["PRE_CONFLICT", "CONFLICT_RESOLUTION_FAILED"])`
  - `CONFLICT_RESOLUTION_FAILED` → `None` (terminal)
- Add to `REVIEW_DECISION_KEYWORDS`: `CONFLICT_RESOLVED_REVIEW_NEEDED → {"approve": "PRE_CONFLICT", "fix": "CONFLICT_RESOLUTION_FAILED"}`
- Add sentinel resolution in transition logic: when the computed next state is `"PRE_CONFLICT"`, read `state["pre_conflict_state"]` from `state.json` and use that as the actual target.
- Add `"conflict-resolver": "conflict/resolution.md"` to `DEFAULT_OUTPUTS`.

### 2. Conflict detection — `tools/agent_runner/run_daemon.py`

- `detect_pr_conflict(ticket_id, run_dir, repo)`: calls `gh pr view <pr_number> --json mergeable`, returns `True` if `"CONFLICTING"`.
- `detect_rebase_conflict(ticket_id, worktree_path)`: attempts `git rebase --no-commit origin/main` in the ticket worktree, aborts on failure, returns `True` if conflicts found.
- Both checks integrated in the daemon polling loop for active (non-terminal, non-conflict) tickets that have a branch and PR number.
- On conflict: write `pre_conflict_state` to `state.json`, transition to `CONFLICT_RESOLUTION_NEEDED`.

### 3. New step type — `tools/agent_runner/run_step.py`

- Add `"conflict-resolver"` / alias `"conflict"` to `STEP_ALIASES`, `DEFAULT_OUTPUTS`, `STEP_ROLE_FILES`, `STEP_SKILL_FILES`.
- Add `"conflict"` to `RUN_SUBDIRS`.
- New function `collect_conflict_context(ticket_id, run_dir, repo_root, worktrees_dir)`: reads `ticket.md`, `plan.md`, `reviews/`, `fixes/`, and runs `gh pr diff`, `git diff $(git merge-base HEAD origin/main)`, `git diff --name-only --diff-filter=U`, `git log --oneline origin/main ^HEAD`; writes the assembled document to `runs/TXXX/conflict/context.md`.
- `collect_conflict_context` is called before spawning the agent.

### 4. `ai/roles/conflict-resolver.md` (new file)

- Mission, safety rules (no `reset --hard`, no blind `--ours`/`--theirs`, `--force-with-lease` only), and expected output format for `conflict/resolution.md`.

### 5. `prompts/generic/conflict-resolver.md` (new file)

- Assembles: global context, role, `git-discipline` + `workflow-discipline` skills, context document reference, output template, forbidden-phrase list.

### 6. Schema extension — `services/control_api/models/schemas.py`

- `TicketSummary`: add `conflict_status: str | None`, `conflicted_files: list[str] | None`, `conflict_summary: str | None`.

### 7. Artifact reader — `services/control_api/services/artifact_reader.py`

- `get_ticket()`: populate the three new fields from `state.json`, `conflict/context.md`, and `conflict/resolution.md`.
- `get_ticket_artifacts()`: include conflict directory files when present.

### 8. New API endpoints — `services/control_api/routes/tickets.py`

- `POST /{ticket_id}/approve-conflict-resolution`: reads `pre_conflict_state` and calls `checkpoint_transition` to it.
- `GET /{ticket_id}/conflict`: returns `conflict/resolution.md` as plain text.
- Both mirrored in the project-scoped router.

### 9. Dashboard frontend — `apps/dashboard/src/`

- Conflict badge on ticket cards in any conflict state.
- Conflict detail section: conflicted files list, resolver summary, test result, Approve / Mark-Failed buttons.
- Timeline renderer: four new states mapped to `TimelineStep` entries (`waiting_human` for review gate, `failed` for `CONFLICT_RESOLUTION_FAILED`).

### 10. Tests — `tests/test_conflict_resolver.py` (new file)

- New states in `VALID_STATES`, correct `TRANSITIONS`, `CONFLICT_RESOLUTION_FAILED` terminal, `PRE_CONFLICT` sentinel resolution, `collect_conflict_context` output shape, `detect_pr_conflict` mock, `--force-with-lease` push assertion.

## Excluded

- Resolving production deployment conflicts.
- Automatic merge to main after resolution.
- Multi-branch global planning or semantic dependency-graph construction.
- Memory update triggered by conflict resolution (normal memory workflow after `TEST_COMPLETE`).
- UI changes outside conflict-specific display.
- Conflict resolution for tickets before `PLAN_APPROVED`.

## Acceptance criteria

1. Four new states present in `VALID_STATES` in `run_ticket.py`.
2. Transitioning to `CONFLICT_RESOLUTION_NEEDED` persists the previous state as `pre_conflict_state` in `state.json`.
3. `run_ticket.py --auto` auto-launches the `conflict-resolver` step from `CONFLICT_RESOLUTION_NEEDED`.
4. `runs/TXXX/conflict/context.md` is created before the agent runs, containing ticket, plan, reviews, PR diff, conflicted files, and latest main delta.
5. Resolver agent produces `runs/TXXX/conflict/resolution.md` with per-file rationale and test outcome.
6. Push uses `git push --force-with-lease` (verified in tests).
7. Successful resolution → `CONFLICT_RESOLVED_REVIEW_NEEDED`; failure → `CONFLICT_RESOLUTION_FAILED`.
8. `POST approve-conflict-resolution` transitions the ticket back to `pre_conflict_state`.
9. `CONFLICT_RESOLUTION_FAILED` is terminal — no automatic retry.
10. Dashboard shows conflict badge, files, summary, and review gate buttons for all conflict-state tickets.
11. `tests/test_conflict_resolver.py` passes; no regressions in existing suite.

---

The plan is saved to `runs/T143/plan.md`. The two key design decisions worth noting: the `"PRE_CONFLICT"` sentinel in `REVIEW_DECISION_KEYWORDS` to dynamically resolve the resume state (avoids duplicating each possible pre-conflict state as a separate transition), and `detect_rebase_conflict` aborts cleanly after detection so the worktree is never left in a mid-rebase state before the resolver agent runs.
