Implementation complete. Summary:

**Files modified:**
- `tools/agent_runner/run_ticket.py` — added `_copy_ticket_source()`, updated `init_auto()` signature, added `--ticket-source` CLI flag
- `tests/test_ticket_source.py` (new) — 6 targeted tests

**What was added:**
- `_copy_ticket_source(ticket_id, source)`: validates path (blocks `..` traversal, rejects missing files and directories), copies content to `runs/TXXX/ticket.md`, logs the source in `runtime.log`
- `--ticket-source <path>` CLI option (use with `--auto-init`): creates the stable task snapshot at init time
- Existing workflow is unchanged when `--ticket-source` is not provided

All 67 tests pass with no regressions.
