## Implementation summary

Implemented the dispatcher-aware scheduling branch per the approved plan.

**Files modified:**

- `tools/agent_runner/ticket_dispatcher.py`
  - Added `is_dispatcher_enabled(db_path=None) -> bool` (mirrors `get_dispatcher_mode != "off"`); exported in `__all__`.

- `tools/agent_runner/run_daemon.py`
  - Lazy-imported `ticket_dispatcher` via the existing `importlib.util.spec_from_file_location` pattern, binding `_get_dispatcher_mode` and `_get_recommended_tickets`.
  - Added `_dispatcher_enabled(db_path) -> (enabled, mode)` — tolerates missing DB and resolution failures by returning `(False, "off")`.
  - Added `_select_tickets_via_dispatcher(...)` — calls the dispatcher, walks ranked recommendations, resolves each `run_dir`, keeps only `AUTO_RUNNABLE_STATES`, returns `[]` on failure / `not_implemented`.
  - In `run_once`: resolves DB and dispatcher mode up front; computes the legacy ticket list (preserving FIFO + `--use-project-map` ordering); branches on `dispatcher_enabled`. Logs exactly one `scheduling: …` line per cycle (`scheduling: legacy (dispatcher=off)` or `scheduling: dispatcher (mode=…)`), and logs `dispatcher returned no recommendations — falling back to legacy scan` when the dispatcher returns an empty list. Added a `project_root` keyword to wire `REPO_ROOT` through.
  - Boot banner now logs `dispatcher_mode = <resolved>` once at startup.

- `tests/test_ticket_dispatcher.py`
  - Added 3 tests for `is_dispatcher_enabled` (off / unknown → False; advisory/manual/auto → True).

- `tests/test_run_daemon.py`
  - Added 7 tests covering: legacy path used when off, dispatcher rank order honored when enabled, fallback to legacy when dispatcher empty, dispatcher recommendations filtered to `AUTO_RUNNABLE_STATES`, per-cycle `scheduling:` log line (parametrized off/advisory), and the missing-DB helper short-circuit.

**Test results:** `tests/test_ticket_dispatcher.py` — 17/17 pass. `tests/test_run_daemon.py` — 42/45 pass; the 3 failures (`test_run_once_calls_launch_for_auto_runnable_state`, `test_main_once_returns_zero`, `test_main_returns_2_when_runs_dir_missing`) pre-existed on the bootstrap commit (verified by checkout) — the first asserts a `launch_ticket` signature that has lacked `state_dir=` for a while; the other two collide with the live daemon singleton on the developer machine.

**Limits:** In dispatcher mode, `TEST_COMPLETE` / human-gate handling only runs when the dispatcher returns no recommendations (and we fall back to the legacy scan). This matches the plan's explicit instruction to replace the ticket list with the dispatcher's output, but if the dispatcher consistently emits work, PR-lifecycle handling for `TEST_COMPLETE` tickets would only fire on the next quiet cycle.
