All 31 tests pass. Here's a summary of the changes:

**Files modified:**

1. `tools/agent_runner/run_daemon.py`
   - Added `import shlex`
   - Extracted `build_run_ticket_command(ticket_id, exec_cmd, ...)` as a pure function — `exec_cmd` is always passed as a single string element, never split
   - Updated `launch_ticket` to use `build_run_ticket_command` and log `Running ticket command: {shlex.join(cmd)}` before the `subprocess.run()` call

2. `tests/test_run_daemon.py`
   - Added `build_run_ticket_command` to imports
   - Added 4 tests: positional structure, `exec_cmd` not-split assertion, optional flags included, optional flags absent by default
