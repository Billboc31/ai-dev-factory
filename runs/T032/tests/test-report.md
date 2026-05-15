Now let me produce the test report.

---

## Test Report — T032: Fix daemon command contract with run_ticket.py

### Environment

- Branch: `ticket/T032-t032-fix-daemon-command-contract-with-run-ticket-p`
- Python: 3.14.4, pytest 9.0.3
- Key files: `tools/agent_runner/run_daemon.py`, `tests/test_run_daemon.py`, `tests/test_daemon_checkpoint.py`

---

### Acceptance Criteria

**AC1 — Le daemon lance `run_ticket.py` avec le ticket id en premier argument positionnel**
**PASS**

`build_run_ticket_command` (line 452) constructs:
```python
cmd = [sys.executable, str(RUN_TICKET), ticket_id, "--auto"]
```
`ticket_id` is always at index 2 (first positional after the script path). Test `test_build_run_ticket_command_positional_structure` asserts `cmd[2] == "T032"`.

---

**AC2 — `--auto` est bien passé**
**PASS**

`"--auto"` is hardcoded into the base command on line 452 and always present. Confirmed by `test_build_run_ticket_command_positional_structure` asserting `"--auto" in cmd`.

---

**AC3 — `--exec-cmd` est transmis comme une seule string complète**
**PASS**

Line 454: `cmd.extend(["--exec-cmd", exec_cmd])` — `exec_cmd` is appended as a single list element, never split. Test `test_build_run_ticket_command_exec_cmd_not_split` explicitly asserts:
```python
assert cmd[idx + 1] == "claude --dangerously-skip-permissions"
assert "--dangerously-skip-permissions" not in cmd
```

---

**AC4 — La commande exacte exécutée est visible dans les logs**
**PASS**

Line 486: `_log(f"Running ticket command: {shlex.join(cmd)}")` fires before `subprocess.run()`. Uses `shlex.join` for unambiguous quoting, exactly as required by the ticket.

---

**AC5 — Les tests passent**
**PASS**

All 36 tests pass in 0.03s:
- `test_run_daemon.py`: 32/32 passed
- `test_daemon_checkpoint.py`: 4/4 passed

The four tests directly covering T032 scope all pass:
- `test_build_run_ticket_command_positional_structure`
- `test_build_run_ticket_command_exec_cmd_not_split`
- `test_build_run_ticket_command_optional_flags_included`
- `test_build_run_ticket_command_optional_flags_absent_by_default`

---

**AC6 — Aucun changement direct de `state.json` depuis le daemon**
**PASS (with note)**

T032 did not introduce direct workflow state machine modifications. The daemon does write to `state.json` via `_save_state_json` in `create_or_update_pr` and `check_and_close_issue`, but these persist daemon-side operational data (`pr_number`, `pr_synced`, `issue_closed`, `daemon_archived`) — not workflow step transitions. No `state` field (the workflow FSM field) is written directly by the daemon; all FSM transitions go through `run_ticket.py`. This is pre-existing behavior and outside T032 scope.

---

**AC7 — Aucune duplication de logique workflow dans le daemon**
**PASS**

The daemon's `run_once` calls `launch_ticket` → `build_run_ticket_command` → `subprocess.run(run_ticket.py --auto ...)`. All FSM logic remains in `run_ticket.py`. The `parse_args` for `--exec-cmd` (line 662) accepts a single string value and passes it through without parsing or splitting.

---

### Regressions

None observed. The broader test suite for daemon state scanning, locking, retry/cooldown, and PR lifecycle was not broken by T032 changes.

---

### Verdict

**IMPLEMENTATION_APPROVED** — All 7 acceptance criteria pass. The extracted `build_run_ticket_command` pure function is correctly tested, the command contract matches the canonical form exactly, and logging is unambiguous.
