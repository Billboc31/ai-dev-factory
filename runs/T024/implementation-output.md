All 166 tests pass. Here's the summary:

---

## Implementation Summary

### Files modified

**`tools/agent_runner/run_daemon.py`** — Added 7 new functions and 3 new CLI args:
- `load_issue_index(runs_dir)` — reads `runs/.issue-intake.json`, returns `{}` on any failure
- `save_issue_index(runs_dir, index)` — atomic write via temp file rename
- `next_ticket_id(runs_dir, reserved=None)` — scans `runs/T*/` + optional reserved set to avoid collisions when multiple issues are ingested in one cycle
- `slugify_title(title)` — lowercase, non-alnum → `-`, truncate 50 chars, fallback `"issue"`
- `fetch_ready_issues(label, repo)` — calls `gh issue list --json number,title`, returns `[]` silently on any failure (no `gh`, auth error, bad JSON)
- `call_issue_intake(issue_number, ticket_id, branch_slug, repo)` — subprocess `run_issue_intake.py`, returns bool
- `poll_github_issues(runs_dir, label, repo)` — orchestrates the above, updates index only on success, retries failed intakes next cycle
- CLI: `--poll-issues`, `--issue-label` (default `ai-ready`), `--issue-repo`
- Loop integration: `poll_github_issues()` called before `run_once()` each cycle when `--poll-issues` is set

**`tests/test_daemon_issue_polling.py`** (new, 39 tests) — covers all new functions with mocked subprocess; no real GitHub or git calls.

### Notable fix vs. plan

`next_ticket_id` accepts an optional `reserved` set so that multiple issues ingested in the same cycle receive distinct sequential IDs (the plan's design assumed only one issue per cycle; the fix makes it correct for batches too).
