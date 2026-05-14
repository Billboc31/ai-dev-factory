127/127 passing. Implementation complete.

---

## Summary

**3 files created/modified:**

- `tools/agent_runner/run_issue_intake.py` *(new)* — 8 focused functions: `validate_ticket_id`, `check_state_absent`, `check_working_tree_clean`, `fetch_issue`, `branch_name`, `create_branch`, `write_ticket_md`, `write_state_json`. No import of `run_ticket.py`. Guards run in strict order (validate → state absent → clean tree → gh fetch → branch create → write).

- `tests/test_run_issue_intake.py` *(new)* — 20 tests covering: valid/invalid ticket-id, branch name slugification, gh success/failure/auth-hint, `--repo` flag forwarding, happy path (files created), ticket.md format, state.json format (INIT state + correct branch), and three guards (state exists, dirty tree, branch exists).

- `tools/agent_runner/README.md` *(updated)* — added "## Issue intake" section with usage example, option description, and sequence of operations.

**Known limits:** `gh` must be installed and authenticated; `--repo` must be provided for repos where remote detection by `gh` would fail (non-standard remotes).
