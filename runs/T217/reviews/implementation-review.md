# Review — T217: Fallback to legacy daemon scheduling when Dispatcher is disabled

## Scope verification

The implementation correctly delivers the **primary T217 goal**: when `DISPATCHER_ENABLED` is `off` (the default), the daemon re-uses its legacy `scan_tickets` → `launch_ticket` path with FIFO/project-map ordering and full PR-lifecycle handling. The plan, the diff, and the new tests are aligned.

Scope is bounded:
- Only `tools/agent_runner/run_daemon.py`, `tools/agent_runner/ticket_dispatcher.py`, `tests/test_run_daemon.py`, `tests/test_ticket_dispatcher.py` are modified (`git diff main..HEAD --stat`). No drive-by refactor.
- The lazy-import pattern at `tools/agent_runner/run_daemon.py:109-114` mirrors `_rdb_*` / `_rr_*` exactly — consistent with the existing convention.
- `is_dispatcher_enabled` at `tools/agent_runner/ticket_dispatcher.py:90` is a thin mirror of `get_dispatcher_mode != "off"` and is correctly exported in `__all__`.

## Correctness vs. acceptance criteria

| Criterion | Verdict |
|---|---|
| `DISPATCHER_ENABLED` unset/off → same legacy order, same `launch_ticket` calls | ✓ — covered by `test_run_once_legacy_when_dispatcher_off` |
| `advisory`/`manual` → dispatcher rank order overrides FIFO | ✓ — covered by `test_run_once_uses_dispatcher_when_enabled` |
| Empty dispatcher → fallback to legacy + dedicated log line | ✓ — covered by `test_run_once_falls_back_to_legacy_when_dispatcher_empty` |
| One `scheduling: …` log per cycle | ✓ — parametrized `test_run_once_logs_active_strategy` |
| Boot banner logs resolved `dispatcher_mode` | ✓ — `run_daemon.py:1955-1960` |
| `is_dispatcher_enabled` exported & correct | ✓ — `test_is_dispatcher_enabled_*` |

Tests: `pytest tests/test_run_daemon.py tests/test_ticket_dispatcher.py` → 59 passed. The 3 failures (`test_run_once_calls_launch_for_auto_runnable_state`, `test_main_once_returns_zero`, `test_main_returns_2_when_runs_dir_missing`) are **pre-existing on `main`** — I verified by checking out `main` and running the same selectors; same 3 failures. Not introduced here.

## Issues

### Minor — Plan claim about PR-lifecycle handling is partially false in dispatcher mode
The plan asserts: *"run the same `for ticket_id, state in tickets:` loop so retry/cooldown, worker registry, conflict detection, PR-lifecycle handling, and `launch_ticket` keep working untouched."*

In reality, `_select_tickets_via_dispatcher` (`run_daemon.py:1681`) **filters to `AUTO_RUNNABLE_STATES` only**. The downstream `elif state == "TEST_COMPLETE":` and `elif state in HUMAN_GATE_STATES:` branches become dead code on any cycle where the dispatcher returns recommendations. PR lifecycle for `TEST_COMPLETE` tickets only runs on "quiet" cycles where the dispatcher returns nothing and we fall back to legacy.

The implementation output explicitly flags this as a "Limit" (`implementation-output.md:25`). It's not a hidden regression. Severity is bounded because:
- Default `DISPATCHER_ENABLED` is `off`, so this only affects users who opt in to advisory/manual.
- `auto` mode is `not_implemented`, treated as empty, falls back to legacy.
- A typical workload still has quiet cycles where lifecycle fires.

Not a blocker for T217's primary goal (legacy fallback when disabled), but a real follow-up is needed before dispatcher modes can be considered production-equivalent. Recommended future fix: union the dispatcher's ranked AUTO_RUNNABLE_STATES tickets with the legacy non-AUTO_RUNNABLE_STATES tickets so human-gate / TEST_COMPLETE handling keeps firing.

### Nit — Continuous-loop path drops `project_root`
`run_daemon.py:2018-2026` (the `while True` loop) does not pass `project_root=REPO_ROOT`, while the `--once` branch at line 2000-2009 does. Behavior is identical because `run_once` falls back to `REPO_ROOT` when `project_root is None`, but it's inconsistent. Not blocking.

### Nit — Boot banner bypasses the helper
The boot banner at `run_daemon.py:1955-1960` calls `_get_dispatcher_mode` directly with its own try/except instead of reusing `_dispatcher_enabled`. Minor duplication. Not blocking.

### Nit — Broad `except Exception` in helpers
`_dispatcher_enabled` and `_select_tickets_via_dispatcher` catch `Exception` blanketly. Reasonable for daemon defensive coding (we don't want a dispatcher hiccup to crash the loop), and the failure is logged — acceptable.

## Code quality

- Naming is clear (`_dispatcher_enabled`, `_select_tickets_via_dispatcher`, `legacy_tickets`).
- Functions are small, single-purpose.
- Logging is operator-friendly and matches the spec (single line per cycle, distinct fallback message).
- No new dependencies, no broadened permissions, no secrets surfaced.
- New tests use the established `_write_state` helper and `monkeypatch` pattern.

## Security / safety

- No new external inputs.
- No new subprocess or shell invocations.
- DB resolution is funnelled through the existing `_ensure_db` cache.
- Failure modes default to the safer legacy path.

## Verdict

The implementation delivers the ticket's primary goal correctly, with adequate test coverage and clean integration with existing daemon machinery. The dispatcher-enabled PR-lifecycle gap is a documented known limit that does not affect the default (`off`) configuration and is appropriately scoped as future work.

IMPLEMENTATION_APPROVED
