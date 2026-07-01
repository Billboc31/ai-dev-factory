## Summary of Changes

### Blocking fix

**`tools/agent_runner/run_daemon.py`** — Wired `GITHUB_POLL_INTERVAL_SECONDS` into the sleep site.
- Added `_resolve_poll_interval(args)` helper (co-located with `_resolve_max_intakes_per_poll`) that returns `args.interval` when the CLI flag is explicitly set, else resolves the setting live per-cycle via `get_setting_int_positive(db, "GITHUB_POLL_INTERVAL_SECONDS", 30)`.
- Changed `--interval` argparse default from `30` to `None` so we can distinguish "explicit override" from "use setting".
- Sleep site (`main()` while-loop) now calls `_resolve_poll_interval(args)` each cycle → live changes to the setting take effect on the next sleep, no restart needed.
- Boot banner shows either `"Ns (CLI override)"` or `"resolved per-cycle from GITHUB_POLL_INTERVAL_SECONDS"` so operators know which mode is active.
- Removed the dead imports `_find_next_pipeline_ticket` and `_process_ticket_pipeline` (unused since the pool-based rewrite).

**`services/control_api/services/daemon_manager.py:146`** — Dropped `--interval 30` from the recommended host command so the launcher no longer overrides the setting. Added an inline comment documenting the new behaviour.

**`tools/agent_runner/runtime_settings.py`** — Marked `MAX_PARALLEL_TICKET_INTELLIGENCE` and `MAX_PARALLEL_READINESS` `requires_restart=True` (pools are lazy singletons, so live edits genuinely need a restart).

### Docs

**`docs/daemon-lifecycle.md`** — Added a paragraph clarifying that `GITHUB_POLL_INTERVAL_SECONDS` resolves live per-cycle while the pool sizes need a restart, and that `--interval N` is an explicit override.

### Tests

- **`tests/test_poll_interval_resolution.py`** (new, 5 tests, all passing) — Locks in the fix:
  - CLI `--interval 17` beats env `GITHUB_POLL_INTERVAL_SECONDS=5` → 17.
  - Env `=5` with no CLI → 5.
  - No env, no CLI → spec default 5.
  - Invalid env (`"abc"`, `"0"`) → safe default 30.
- **`tests/test_daemon_ticket_pipeline.py`** — Updated the mock that referenced the removed `_process_ticket_pipeline` symbol to patch `_init_pipeline_pools` instead (same semantic: nothing runs when the pipeline is disabled).

### Verification

- All 30 T221-relevant tests pass (5 new poll-interval + 25 pre-existing).
- The one failing test in `test_daemon_ticket_pipeline.py::test_main_calls_poll_ticket_pipeline_each_cycle` is the same pre-existing environment failure the reviewer already documented: a real daemon on this host holds the singleton lock. Confirmed identical failure before my changes.
