# T145 — T145 — Harden conflict resolver workflow

**Source**: GitHub Issue #140

## Description

Goal: harden the conflict resolver introduced in T144 before relying on it for parallel-ticket workflows.

Context:
T144 introduced a first conflict resolver agent with dashboard review. It should be treated as an experimental V1.

Issues to fix:
- context may be collected before the real rebase conflict exists
- resolver may only make one AI pass even if conflicts remain
- broad staging is too risky
- rebase continue can require multiple conflict cycles
- failures need clearer logs and terminal state handling

Scope:
- collect conflict context after rebase fails and conflict markers exist
- loop while unresolved conflicted files remain
- after each AI pass, re-check unresolved files
- add a configurable max resolver pass count, default 3
- fail clearly when conflicts remain after the max passes
- avoid broad staging where possible
- improve per-pass logs: pass number, conflicted files, modified files, unresolved files, rebase continue result
- abort the rebase cleanly on failure when a rebase is active
- transition to CONFLICT_RESOLUTION_FAILED on all failures
- transition to CONFLICT_RESOLVED_REVIEW_NEEDED only after rebase fully completes and tests finish
- use origin/main consistently instead of local main for context
- add tests for multi-pass success and max-pass failure

Safety:
- do not run on main
- do not reset the branch
- do not auto-merge main
- do not push unless rebase is complete
- push only with force-with-lease

Out of scope:
- automatic merge to main
- global dependency planning
- semantic ticket tree scheduling
- production deployment conflicts

Acceptance:
- context is collected after real conflicts exist
- resolver supports multiple passes
- unresolved conflicts produce clear failure
- no push happens if conflicts remain
- rebase is aborted cleanly on failure
- logs show each resolver pass clearly
- tests cover multi-pass success and max-pass failure
