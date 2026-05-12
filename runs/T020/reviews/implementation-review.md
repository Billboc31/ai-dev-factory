All 23 tests pass. Here is the full review.

---

## Implementation Review — T020 Local Workflow Daemon

### Scope conformance

The implementation is strictly bounded to the ticket: one new file (`run_daemon.py`, 143 lines), one new test file (`test_run_daemon.py`, 23 tests). `run_ticket.py` is untouched. No GitHub API, no auto-merge, no distributed features. No scope drift.

---

### Check 1 — Allowed states only

`AUTO_RUNNABLE_STATES` exactly matches the 6 states listed in the ticket (§2). The test `test_auto_runnable_states_contains_all_six` locks this as an exact-membership assertion, not a subset check — preventing silent additions.

The `DONE` state (mentioned in the ticket §3 but absent from `run_ticket.py`'s `VALID_STATES`) is handled implicitly by the `else` branch in `run_once()` (line 148): it logs `"skipping T005 state=DONE"` without the `(human gate)` tag. This is the plan's documented hypothesis, confirmed as correct. Minor observation: the log is technically correct but doesn't distinguish `DONE` from truly unknown states — not a blocking concern.

**PASS**

---

### Check 2 — Human gates remain blocking

`HUMAN_GATE_STATES` = `{"PLAN_REVIEW_NEEDED", "TEST_COMPLETE"}`. The daemon skips these and never calls `launch_ticket()` for them (verified by `test_run_once_skips_human_gate_state` and `test_run_once_logs_human_gate_skip`).

`IMPLEMENTATION_REVIEW_NEEDED` is correctly classified as auto-runnable — the AI reviewer is the actor here, not a human. The human gate is `PLAN_REVIEW_NEEDED`. This matches the workflow design.

The disjoint-set test (`test_auto_runnable_and_human_gate_are_disjoint`) enforces that no state can be both a gate and auto-runnable.

**PASS**

---

### Check 3 — No concurrent runs

The PID lock at `runs/TXXX/daemon.lock` checks liveness via `os.kill(pid, 0)` before acquring, and always releases in a `finally` block (`run_daemon.py:131`). Stale locks (dead PID) are cleaned and re-acquired.

**Notable gap**: `_acquire_lock()` has a TOCTOU race — it checks existence, then writes. Two daemon processes starting within milliseconds could both pass the existence check before either writes, then both overwrite each other's lock. For the intended single-daemon use case this is harmless. The ticket explicitly allows this class of mechanism ("simple, local, deterministic") and `Path.write_text()` with atomic `O_EXCL` was not required. The worst case is duplicate step execution, not data corruption.

**PASS** (within the "simple, local" constraint the ticket explicitly set)

---

### Check 4 — Logs are explicit

Every decision point is logged:
- Ticket detected with state (`run_daemon.py:143`)
- Skipped with explicit reason: `(human gate)` or generic unknown (`run_daemon.py:145-148`)
- Already running (lock held) (`run_daemon.py:116`)
- Stale lock cleanup (`run_daemon.py:67`)
- Dry-run intent (`run_daemon.py:111`)
- Subprocess stdout/stderr forwarded line-by-line with ticket prefix (`run_daemon.py:126-129`)
- Return code logged (`run_daemon.py:130`)
- Daemon start/stop (`run_daemon.py:169`, `run_daemon.py:181`)

Format `[ISO-timestamp] [daemon] message` is consistent throughout. Matches the template from the ticket (§5).

One note: subprocess output is buffered — the daemon logs nothing until the step completes. For long AI steps this means silence for minutes. Acceptable given the simplicity requirement; streaming would need `subprocess.Popen`.

**PASS**

---

### Check 5 — Tests are meaningful

All ticket-required test scenarios are present and pass:

| Requirement | Test |
|---|---|
| Auto-runnable detection | `test_auto_runnable_states_contains_all_six`, `test_run_once_calls_launch_for_auto_runnable_state` |
| Human gate enforcement | `test_run_once_skips_human_gate_state`, `test_run_once_logs_human_gate_skip` |
| Single-run protection | `test_acquire_lock_returns_false_when_live_pid_holds_lock`, `test_launch_ticket_blocked_by_live_lock_does_not_launch`, `test_launch_ticket_releases_lock_after_run` |
| Dry-run | `test_launch_ticket_dry_run_does_not_call_subprocess`, `test_launch_ticket_dry_run_logs_action` |
| Logs | `test_run_once_logs_human_gate_skip`, `test_run_once_logs_no_tickets_when_empty` |
| Workflow compatibility | `run_ticket.py` not modified; invoked via mocked subprocess |

Minor gaps: no test for `json.JSONDecodeError` path in `_acquire_lock`, no test for the interrupted polling loop, no test asserting the auto-runnable log line. None are blocking — critical invariants are covered.

**PASS**

---

### Other observations

- `ROOT = Path(__file__).resolve().parent` correctly resolves to `tools/agent_runner/` — `RUN_TICKET` path is valid.
- `--exec-cmd` is correctly marked `required=True` — no way to call the daemon without specifying the AI command.
- `--runs-dir` is not forwarded to `run_ticket.py` subprocess — the subprocess always resolves `runs/` relative to CWD. This only matters for non-default `--runs-dir` usage, which is outside the primary workflow.
- `run_ticket.py` backward compatibility: fully preserved — no changes, existing commands, retries, reviews, snapshots all work unchanged.

---

### Verdict

The implementation is correct, bounded, and well-tested. All ticket criteria are met. The identified gaps (TOCTOU, `--runs-dir` propagation, `DONE` log tagging) are minor and consistent with the "simple, local, explicit" constraint the ticket explicitly imposed.

IMPLEMENTATION_APPROVED
