Implementation complete. Here's the summary:

## Changes made

**`tools/agent_runner/run_ticket.py`** — three git primitives hardened, two new flags:

| Function | What changed |
|---|---|
| `checkout_branch()` | Adds `_check_working_tree_clean()` guard before any git op; logs refused/switching/creating/done to `runtime.log` |
| `commit_ticket()` | Guards with `git status --porcelain runs/<id>/` (returns `rc=1` if nothing to commit); default message is now state-aware (`TXXX: checkpoint [STATE]`); logs SHA on success |
| `push_branch()` | Loads `state.json` and verifies current branch == `state["branch"]` before pushing; warning-only if `state.json` absent; full logging |
| `auto_run()` | Accepts `auto_commit` and `auto_push` params; triggers commit then push after each successful state transition; failures are warnings only |
| `parse_args()` / `main()` | New flags: `--ensure-branch` (alias for `--branch`), `--auto-commit`, `--auto-push` |

**`docs/ai/git-workflow.md`** — fully updated to document all new flags, guards, log entries, and the `--auto-commit`/`--auto-push` behavior.
