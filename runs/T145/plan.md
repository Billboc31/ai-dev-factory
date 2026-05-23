Now I have a clear picture of the existing code. Let me write the plan.

## Objective

Harden `run_conflict_resolver.py` and `conflict_context_collector.py` so that context is collected only after real conflict markers exist, the AI resolver loops until all conflicts are cleared or a configurable max-pass limit is hit, staging is scoped to conflicted files only, rebase is aborted cleanly on failure, all failure paths transition to `CONFLICT_RESOLUTION_FAILED`, and multi-pass behaviour is covered by tests.

## Included

### `tools/agent_runner/run_conflict_resolver.py`

- Move context collection call to **after** `git rebase origin/main` returns non-zero and conflicted files are confirmed (currently context is collected before the rebase runs).
- Replace the single AI-pass block with a `while unresolved_files and pass_count < max_passes` loop:
  - Increment `pass_count` at the top of each iteration.
  - Log: pass number, list of conflicted files at loop entry.
  - Call AI resolver with updated context (re-read conflict markers from disk).
  - After AI edits: stage **only** the conflicted files (`git add -- <file1> <file2> ...`) instead of `git add -A`.
  - Log: which files were staged, which still have markers (unresolved).
  - Run `git rebase --continue` (or `--skip` if nothing to commit).
  - Log: rebase continue exit code and stdout/stderr.
  - Re-collect `unresolved_files` via `git diff --name-only --diff-filter=U`; if new conflicts appeared for the next commit, re-enter the loop.
- After the loop: if `unresolved_files` is non-empty → log clearly, abort rebase (`git rebase --abort`), transition to `CONFLICT_RESOLUTION_FAILED`.
- After the loop: if `pass_count >= max_passes` and conflicts still remain → same abort + fail path.
- Add `MAX_RESOLVER_PASSES = 3` constant (configurable via env var `CONFLICT_RESOLVER_MAX_PASSES`).
- Ensure **every** exception and failure path calls the rebase-abort guard and transitions to `CONFLICT_RESOLUTION_FAILED` (audit all existing `except`/failure branches).
- Transition to `CONFLICT_RESOLVED_REVIEW_NEEDED` **only** after rebase fully completes (no conflicted files, rebase process exits 0) and pytest passes.
- Replace any remaining uses of `local main` / bare `main` with `origin/main` for diff/log commands.
- Log format per pass: `[pass N/max] conflicted=<list> | staged=<list> | unresolved=<list> | continue_rc=<N>`.

### `tools/agent_runner/conflict_context_collector.py`

- Move (or guard) the "conflicted files" and "file contents" section so it reads files **after** conflict markers exist on disk, not from the pre-rebase state.
- Use `origin/main` consistently for `git log` / `git diff` base references (replace any `main` bare reference).

### `tests/test_conflict_resolver.py`

- Add test: **multi-pass success** — first pass leaves one file conflicted, second pass clears all; assert state transitions to `CONFLICT_RESOLVED_REVIEW_NEEDED`, assert `pass_count == 2`.
- Add test: **max-pass failure** — all passes leave conflicts unresolved; assert `git rebase --abort` is called, assert state transitions to `CONFLICT_RESOLUTION_FAILED` after exactly `MAX_RESOLVER_PASSES` iterations.
- Existing tests must continue to pass.

## Excluded

- Changes to the dashboard UI (`TicketDetailPage.jsx`).
- Changes to the daemon's conflict detection logic (`run_daemon.py`).
- Changes to the API routes (`services/control_api/routes/tickets.py`).
- Automatic merge to main, global dependency planning, semantic ticket scheduling, production deployment conflicts.
- Adding a new state machine state or altering the existing state transitions other than ensuring all failures reach `CONFLICT_RESOLUTION_FAILED`.

## Acceptance criteria

1. `conflict_context_collector.py` is never called before `git rebase origin/main` has produced conflict markers on disk.
2. The resolver retries AI passes as long as `git diff --name-only --diff-filter=U` returns files, up to `MAX_RESOLVER_PASSES` (default 3, overridable via env var).
3. After each AI pass only the conflicted files (not all tracked files) are staged with `git add -- <files>`.
4. When conflicts remain after the max passes, `git rebase --abort` is executed and the ticket state becomes `CONFLICT_RESOLUTION_FAILED`.
5. The ticket state becomes `CONFLICT_RESOLVED_REVIEW_NEEDED` only after rebase exits cleanly (exit code 0, zero conflicted files) and pytest passes.
6. Every failure path (exception, rebase-continue failure, test failure, push failure) transitions to `CONFLICT_RESOLUTION_FAILED` and logs `CONFLICT_RESOLUTION_FAILED` in `conflict/error.log`.
7. Runtime logs contain a per-pass line matching the format `[pass N/max] conflicted=... | staged=... | unresolved=... | continue_rc=...`.
8. `origin/main` is used exclusively (no bare `main`) for all diff/log base references.
9. `pytest tests/test_conflict_resolver.py` passes, including the two new tests for multi-pass success and max-pass failure.
