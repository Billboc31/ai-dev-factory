Both new tests pass. Here's a summary of all changes made:

**Files modified:**

1. **`tools/agent_runner/run_conflict_resolver.py`** — Complete rewrite of the conflict resolution logic:
   - Added `MAX_RESOLVER_PASSES = int(os.environ.get("CONFLICT_RESOLVER_MAX_PASSES", "3"))`
   - Context collection moved to **after** rebase fails and conflict markers are confirmed
   - Single AI pass replaced with a `while conflicted_files and pass_count < MAX_RESOLVER_PASSES` loop
   - Each pass: stages only the conflicted files (`git add -- <files>`), not `git add -A`
   - Per-pass log line: `[pass N/max] conflicted=... | staged=... | unresolved=... | continue_rc=...`
   - After failed `git rebase --continue`: checks for new conflicts from next commit vs real failure
   - After max passes with conflicts remaining: aborts rebase, transitions to `CONFLICT_RESOLUTION_FAILED`
   - Added `_has_conflict_markers()` helper to detect remaining markers after AI edit
   - Added `_abort_rebase()` helper called on every failure path
   - `CONFLICT_RESOLVED_REVIEW_NEEDED` transition only after clean rebase + passing tests
   - Test failures now also transition to `CONFLICT_RESOLUTION_FAILED`

2. **`tools/agent_runner/conflict_context_collector.py`** — Added `conflicted_files: list[str] | None = None` parameter to `collect_context()`, overriding the pre-rebase list from `state.json` when post-rebase real conflicts are supplied.

3. **`tests/test_conflict_resolver.py`** — Added two new tests:
   - `test_resolve_conflicts_multi_pass_success`: 2-pass scenario, asserts `CONFLICT_RESOLVED_REVIEW_NEEDED`
   - `test_resolve_conflicts_max_pass_failure`: all passes fail, asserts `git rebase --abort` called and `CONFLICT_RESOLUTION_FAILED`

**Result: 32/32 tests pass.**
