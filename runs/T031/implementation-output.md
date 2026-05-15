All done. Here's a summary of what was implemented:

## T031 — Implementation complete

**300/300 tests pass.**

### Changes made

**`run_daemon.py`** — 3 modifications:
- `scan_tickets()`: skips any ticket with `daemon_archived=true` (with explicit log)
- `create_or_update_pr()`: detects "No commits between" in `gh pr create` stderr → persists `pr_skipped_no_diff=true` + `daemon_archived=true`, never retries
- `run_once()`: before calling `handle_test_complete()`, loads state and skips if `issue_closed=true` or `pr_skipped_no_diff=true`

**`run_ticket.py`** — 4 modifications:
- `COMMIT_SCOPE` extended with `README.md`, `.gitignore`, `package.json`, `package-lock.json`
- New `archive_daemon()` function: writes `daemon_archived=true` to state.json + logs to runtime.log
- `--archive-daemon` CLI flag added
- `--checkpoint` alias for `--commit` added (fixes the unrecognized argument bug)

**`subprocess_runner.py`** — 3 modifications:
- `commit_ticket()`: now passes `--include-code`
- `checkpoint_ticket()`: fixed (was using unrecognized `--checkpoint`), now uses `--commit --include-code`
- New `archive_ticket()` function

**`routes/tickets.py`**: `POST /tickets/{id}/archive` endpoint added

**Frontend**: `archiveDaemon(id)` API call + "Archive daemon" button (danger variant) in the Git/Runtime section

**Tests**: 12 new tests across 4 files covering all acceptance criteria from the ticket.
