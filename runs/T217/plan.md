I have enough context to produce the plan. The daemon's `run_once()` loop in `tools/agent_runner/run_daemon.py` already uses legacy FIFO/project-map scheduling and never consults `ticket_dispatcher.get_recommended_tickets`. The dispatcher mode is exposed via `ticket_dispatcher.get_dispatcher_mode(db_path)` reading the `DISPATCHER_ENABLED` registry key. The plan must wire an explicit branch in the daemon: dispatcher-driven scheduling when enabled, legacy scan-and-launch when disabled, with clear logs and tests for both modes.

## Objective

Make the daemon explicitly branch its ticket-acquisition strategy on the `DISPATCHER_ENABLED` runtime setting: when the dispatcher mode is `off`, the daemon must keep using its legacy scheduling path (`scan_tickets` → `launch_ticket` for `AUTO_RUNNABLE_STATES`); when the dispatcher mode is anything else (`advisory` / `manual` / `auto`), the daemon must drive scheduling from `ticket_dispatcher.get_recommended_tickets`. The active strategy must be logged each cycle, and both modes must remain covered by tests.

## Included

- `tools/agent_runner/run_daemon.py`
  - Import `ticket_dispatcher` lazily (same `importlib.util.spec_from_file_location` pattern as `_wm_mod` / `_rdb_mod` / `_rr_mod`) and bind a local `_get_dispatcher_mode` symbol.
  - Add a small helper `_dispatcher_enabled(db_path) -> tuple[bool, str]` that returns `(enabled, mode)` where `enabled = mode != "off"`. The helper must tolerate a missing DB (`db_path is None`) by returning `(False, "off")`.
  - In `run_once(...)`, before the existing ticket scan/loop:
    - Resolve `mode` via `_dispatcher_enabled(_db_path)`.
    - Log exactly one line per cycle indicating the active strategy, e.g. `scheduling: legacy (dispatcher=off)` or `scheduling: dispatcher (mode=advisory)`.
  - Add a new internal function `_select_tickets_via_dispatcher(db_path, project_root, runs_dir, worktrees_dir, mode) -> list[tuple[str, str]]` that:
    - Calls `ticket_dispatcher.get_recommended_tickets(db_path, project_root, mode=mode)`.
    - Iterates the returned `recommendations` in rank order, resolves each `ticket_id` to its run_dir via the existing `_get_run_dir`, reads `state.json`, and keeps only entries whose state is in `AUTO_RUNNABLE_STATES`.
    - Returns the resulting `[(ticket_id, state), ...]` list.
    - On any failure (dispatcher exception, missing DB, `not_implemented=True`) it returns `[]` and the caller logs a degradation warning.
  - In `run_once(...)`, branch on the resolved mode:
    - `enabled=False` (mode `off`): keep the existing legacy path unchanged (`scan_tickets` + optional `--use-project-map` ordering + the existing `AUTO_RUNNABLE_STATES` / `TEST_COMPLETE` / `HUMAN_GATE_STATES` handling).
    - `enabled=True`: build the ticket list from `_select_tickets_via_dispatcher`, fall back to the legacy list if the helper returned `[]` (log the fallback), then run the same `for ticket_id, state in tickets:` loop so retry/cooldown, worker registry, conflict detection, PR-lifecycle handling, and `launch_ticket` keep working untouched.
  - Boot banner (`main`): after the existing block, add one line `dispatcher_mode = <resolved>` so operators can see at startup which mode is in effect.
- `tools/agent_runner/ticket_dispatcher.py`
  - Add `is_dispatcher_enabled(db_path=None) -> bool` returning `get_dispatcher_mode(db_path) != "off"`, and export it in `__all__`. Reused by the daemon helper above to avoid duplicating the mode resolution.
- `tests/test_run_daemon.py`
  - New test `test_run_once_legacy_when_dispatcher_off`: with `DISPATCHER_ENABLED` unset (or `off`), set up two tickets in `AUTO_RUNNABLE_STATES`, patch `launch_ticket`, run `run_once`, and assert `launch_ticket` is called for each ticket and that `_select_tickets_via_dispatcher` is not consulted.
  - New test `test_run_once_uses_dispatcher_when_enabled`: monkeypatch `_get_dispatcher_mode` (or set `AI_DEV_FACTORY_DISPATCHER_MODE=advisory`) and patch `ticket_dispatcher.get_recommended_tickets` to return two ranked recommendations. Assert `launch_ticket` is called in dispatcher rank order and that legacy `scan_tickets` ordering is overridden.
  - New test `test_run_once_logs_active_strategy` (parametrized over `off` and `advisory`): capture stdout and assert the `scheduling:` log line matches the active mode.
  - New test `test_run_once_falls_back_to_legacy_when_dispatcher_empty`: with mode `advisory` and `get_recommended_tickets` returning an empty `recommendations` list while `AUTO_RUNNABLE_STATES` tickets exist in `runs/`, assert the daemon launches them and logs the fallback line.
- `tests/test_ticket_dispatcher.py`
  - Add a focused test for `is_dispatcher_enabled` covering `off → False` and `advisory/manual/auto → True`.

## Excluded

- Implementing the dispatcher `"auto"` execution mode (the existing dispatcher already returns `not_implemented=True` for `auto`; the daemon will treat that as an empty recommendation set and fall back to legacy).
- Changes to the dispatcher ranking algorithm (`_score`, `_sort_key`, eligibility), to `ticket_execution_eligibility`, or to the readiness evaluator.
- Changes to the Control API dispatcher routes or to the UI.
- Changes to `--use-project-map` / `next_recommended` behavior (it remains a sub-strategy of the legacy path).
- Changes to PR lifecycle handling (`handle_test_complete`), conflict detection, retry/cooldown logic, workers registry, or `launch_ticket` itself.
- Changes to `runtime_settings.py`’s `DISPATCHER_ENABLED` spec (key, default, env var stay as-is).
- Documentation rewrites in `docs/` or memory files.

## Acceptance criteria

- With `DISPATCHER_ENABLED` unset, set to `off`, or DB unavailable, `run_once` produces the same ticket order and the same `launch_ticket` calls as on `main`, verified by the legacy test added in `tests/test_run_daemon.py`.
- With `DISPATCHER_ENABLED=advisory` (or `manual`), `run_once` calls `launch_ticket` in the order returned by `ticket_dispatcher.get_recommended_tickets`, verified by the dispatcher-driven test.
- When the dispatcher returns no recommendations while autorunnable tickets exist, `run_once` falls back to the legacy list and emits a `dispatcher returned no recommendations — falling back to legacy scan` log line.
- Every daemon cycle emits exactly one `scheduling: …` log line naming the active strategy and mode.
- The daemon boot banner logs the resolved `dispatcher_mode` once at startup.
- `is_dispatcher_enabled` is importable from `ticket_dispatcher` and returns `False` only for mode `off`.
- `pytest tests/test_run_daemon.py tests/test_ticket_dispatcher.py` passes.
- No changes outside the files listed in **Included**; existing tests in `tests/` continue to pass unchanged.
