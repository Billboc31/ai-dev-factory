# Fix artifact — IMPLEMENTATION_FIX_REQUIRED

- decision: IMPLEMENTATION_FIX_REQUIRED
- review source: runs/T159/reviews/implementation-review.md
- generated at: 2026-05-29T09:16:23Z

---

Now I have everything I need for the review. Let me write the structured review.

---

## T159 — Implementation Review

### Context

This is a review of the implementation for ticket T159 (Harden runtime SQLite architecture and degraded-mode recovery). I conducted the review by reading the five changed source files, running the test suites, comparing results against the baseline (main branch), and checking each acceptance criterion.

---

### Test results

| Suite | Main baseline | T159 branch | Delta |
|---|---|---|---|
| `test_runtime_db.py` | 19/19 | 19/19 | — |
| `test_run_daemon.py` | 34/36 (2 pre-existing failures) | 35/36 (1 pre-existing failure) | **+1 test fixed** |

The one remaining failure (`test_main_returns_2_when_runs_dir_missing`) is pre-existing on main — confirmed by running both branches. It fails because `AI_DEV_FACTORY_RUNTIME_ROOT` is set in the dev environment, which causes `main()` to ignore `--runs-dir` and use the real runs directory. T159 did not introduce this regression; it actually fixed the other pre-existing failure (`test_run_once_calls_launch_for_auto_runnable_state`).

---

### Acceptance criteria check

| Criterion | Status |
|---|---|
| Runtime dashboard works if SQLite corrupted | ✅ |
| Daemon does not crash-loop on malformed DB | ✅ |
| Runtime state observable through filesystem fallback | ✅ |
| Only one global runtime DB used | ✅ |
| Worktrees create no local SQLite DBs | ✅ |
| Corruption probability reduced (WAL + pragmas) | ✅ |
| Startup integrity checks run automatically | ✅ |
| Broken DBs quarantined automatically | ✅ |
| **Users receive explicit degraded-mode warnings** | **❌** |
| Existing flows continue functioning | ✅ |

---

### Blocking issue — Missing user-visible degraded warning

**Criterion**: "Users receive explicit degraded-mode warnings" — not met.

**Ticket requirement** (`Runtime dashboard degraded UX` section):
> Runtime UI should display:
> `SQLite runtime database unavailable`
> `Showing filesystem-derived runtime state`

**What was implemented**: `BoardResponse.degraded: bool = False` is populated correctly (`board_service.py:247–252`) and `RuntimeHealth.sqlite_degraded: bool = False` is surfaced in the health endpoint (`runtime_dashboard.py:443–448`). Both backend signals are correct.

**What is missing**: `BoardPage.jsx` reads `res.data.columns` but never reads `res.data.degraded` — confirmed by `grep -n "degraded" apps/dashboard/src/pages/BoardPage.jsx` returning nothing. The warning banner specified in the ticket is never shown to the user.

**Impact**: The entire degraded-mode UX concept is invisible to the operator. A backend flag that no frontend code reads delivers zero user value for this acceptance criterion. The tester's report (`runs/T159/tests/test-report.md`) independently identifies this as "PARTIAL FAIL" and recommends adding the banner.

**Required fix**: In `BoardPage.jsx`, when `res.data.degraded` is `true`, render a visible warning. Example (3 lines):

```jsx
{boardData.degraded && (
  <div className="...">SQLite runtime database unavailable — showing filesystem-derived state</div>
)}
```

The plan's exclusion clause ("frontend UI changes beyond the JSON warning field") was approved, but the approval missed that the ticket acceptance criterion requires a visible UI warning — not just a JSON field. The acceptance criterion takes precedence.

---

### Non-blocking observations

**Observation 1 — `_try_load_runtime_db` degraded detection is weak**
`_try_load_runtime_db` (`board_service.py:88–104`) returns `degraded=True` only when the module itself fails to import. If the DB exists but is corrupt, it returns `(mod, db_path, False)`, so `sqlite_degraded` in `RuntimeHealth` will be `False` for a malformed DB. The board endpoint is correct (degraded fires on actual query failures). The health endpoint's `sqlite_degraded` is misleading for the corruption case. Low priority — the board signal is what operators see.

**Observation 2 — `upsert_ticket_runtime` column names are not whitelisted**
`runtime_db.py:244–248` interpolates `**fields` keys directly into SQL. All callers are internal with known constant keys, so there is no practical risk, but the pattern is fragile if the function's API expands. Not a blocker.

**Observation 3 — `check_and_recover_db` on `.recover` path does not call `init_runtime_db`**
`runtime_db.py:173–177`: when `sqlite3 CLI .recover` succeeds, `init_runtime_db` is not called afterward. If `.recover` extracted partial tables, the schema is incomplete until the next `_ensure_db` call. Since `_ensure_db` always calls `init_runtime_db` after `check_and_recover_db`, this gap only affects direct callers of `check_and_recover_db`. Low probability, not a blocker.

---

### Code quality and scope compliance

The implementation is clean, stdlib-only, well-structured and stays within plan scope. `fcntl`-based locking, WAL mode, `busy_timeout`, and the singleton guard are all correct. The filesystem fallback in `board_service.py` covers all three SQLite call sites. No new dependencies were introduced.

---

### Verdict

One acceptance criterion from the ticket is not met: the user-visible degraded-mode warning banner in the dashboard. The backend is complete; the missing piece is ~3–5 lines in `BoardPage.jsx`. All other criteria pass.

IMPLEMENTATION_FIX_REQUIRED
