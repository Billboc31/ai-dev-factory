Clean. Both functions and all their references are gone. Here's what was done:

**Removed:**
- `_sync_main_before_intake()` (was lines 713–751) — dangerous `git checkout main` that could strand the daemon on `main` if intake failed
- `_count_active_tickets()` (was lines 754–766) — out-of-scope throttling feature
- `--max-active-tickets` CLI argument from `parse_args()`
- All capacity-check and single-candidate logic from `poll_github_issues()`

**Restored:**
- `poll_github_issues()` now loops over **all** candidates (original behavior from `main`), processing each one in order

The 4 core bug fixes (push before PR, branch guard, dirty tree classification, runtime file untracking) and the 2 plan-review additions (checkpoint before `PLAN_REVIEW_NEEDED`, `_sync_ticket_branch` ff-only pull) remain intact.
