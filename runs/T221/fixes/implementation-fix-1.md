# Fix artifact — IMPLEMENTATION_FIX_REQUIRED

- decision: IMPLEMENTATION_FIX_REQUIRED
- review source: runs/T221/reviews/implementation-review.md
- generated at: 2026-07-01T10:15:01Z

---

# Implementation Review — T221

## Summary

The implementation covers most of the ticket's scope well: batch GitHub intake, atomic per-stage claim helpers, bounded thread pools for Ticket Intelligence and Readiness, an idempotent intake insert, and a solid regression test ensuring `MAX_WORKERS` is not touched. The 24 new tests pass locally. However, one of the four new settings — `GITHUB_POLL_INTERVAL_SECONDS` — is registered in the registry but is **never consumed** by the daemon. This directly affects an acceptance criterion and the documented demo behaviour, and I consider it blocking.

---

## What works well

### Batch intake (`run_daemon.poll_github_issues`)
- The `break` on first success is gone; the loop iterates every candidate.
- Bounded by `MAX_ISSUES_INTAKED_PER_POLL` (resolved via `_resolve_max_intakes_per_poll`), with a `skipped_limit` counter for the deferred remainder.
- Emits the required summary log line: `github poll: discovered=<N> intaked=<N> skipped_existing=<N> skipped_limit=<N>` on every exit path (including the "no issues" and "all already ingested" branches).
- Reconciled worktrees still count towards the intake budget (`run_daemon.py:1480`).

### Atomic claim helpers (`ticket_pipeline.py:164-208`)
- `claim_intelligence` and `claim_readiness` use a single `INSERT ... ON CONFLICT ... DO UPDATE WHERE` statement — genuinely atomic under WAL SQLite.
- Terminal filter (`NOT IN ('running', 'completed')`) correctly rejects double-claims of an in-flight or finished run while allowing failed/queued/ready_candidate rows to be re-claimed. The concurrent-worker tests (`test_claim_intelligence.py:73`, `test_claim_readiness.py:67`) prove exactly-one-winner semantics with real threads and a barrier.
- The inline chain in `maybe_run_readiness_after_intelligence` (`ticket_pipeline.py:130-137`) also calls `claim_readiness`, so the inline path and the pool path can't double-fire.

### Idempotent intake (`ticket_pipeline.record_intake_once`)
- `INSERT ... ON CONFLICT(issue_number) DO NOTHING` on `issue_intake.issue_number` (PK); a lost/reset file index still can't produce two DB rows. Correct.
- The poller in `run_daemon.py:1539-1547` treats a `rowcount == 0` return as `skipped_existing++`, so the summary counter is honest across a lost-index scenario.

### Bounded parallel pools (`run_daemon.py:1794-1943`)
- Lazy singletons, sized once at first use via `get_setting_int_positive` with a safe fallback of 1. No race on init (`_intel_pool_lock` / `_readiness_pool_lock`).
- Per-ticket in-flight sets (`_intel_inflight`, `_readiness_inflight`) prevent the same ticket from being enqueued twice while an earlier submission is still pending — this catches the pending-in-queue case that the DB claim alone can't (a queued task hasn't run `claim_*` yet).
- `_shutdown_pipeline_pools()` is called in `main()`'s `finally`, so pools are cleaned even on `KeyboardInterrupt` (`run_daemon.py:2558`).
- Peak-concurrency test (`test_parallel_bounds.py`) exercises the real `ThreadPoolExecutor`, submits 10 barrier-blocked tasks against a pool sized 4, and asserts `peak == 4`.

### Scope discipline
- `test_execution_workers_unchanged.py` static-analyses the new pool helpers to prove they don't reference `MAX_WORKERS` and that `run_once` still owns coding-worker scheduling. This is the exact regression the ticket asked for.

---

## Blocking issue

### 1. `GITHUB_POLL_INTERVAL_SECONDS` is dead weight

`runtime_settings.py:190-199` registers the setting with default 5. `docs/daemon-lifecycle.md:138,159` documents it. `test_settings_fallback.py:61` verifies fallback behaviour. **But nothing in `run_daemon.py` reads it.** The daemon's actual sleep is still `time.sleep(args.interval)` at `run_daemon.py:2554`, sourced from the `--interval` CLI flag (default 30, `run_daemon.py:2367`). `services/control_api/services/daemon_manager.py:146` still launches the daemon with a hard-coded `--interval 30`.

Consequences:
- The ticket requires "Poll interval is configurable independently from pipeline execution." Setting `GITHUB_POLL_INTERVAL_SECONDS=5` in the environment (or via the settings API) has **zero runtime effect** — the only way to change the poll interval is still to pass a different `--interval` at launch. That path predates T221; nothing new is actually usable.
- The demo scenario ("creating 10 issues should result in all 10 appearing in AI Dev Factory within a few seconds") is not met unless the operator also remembers to append `--interval 5`. `daemon_manager.py:146` will keep spawning the daemon at 30s.
- `docs/daemon-lifecycle.md:159` explicitly claims "≈5–10 s at the demo default", which is not true given the launch path.

**Fix**: consume the setting at the sleep site. Concretely, in `main()`, right before `time.sleep(args.interval)`, resolve the effective interval each cycle:

```python
poll_interval = _runtime_settings.get_setting_int_positive(
    _ensure_db(), "GITHUB_POLL_INTERVAL_SECONDS", 30,
)
_log(f"sleeping {poll_interval}s")
time.sleep(poll_interval)
```

and drop or deprecate `--interval` (or have it act as an override when explicitly passed). Update `daemon_manager.py:146` accordingly. Update `test_settings_fallback.py` if needed, and add a small integration test that overriding the env var actually changes the observed sleep duration in `--once`-adjacent code.

---

## Minor observations (non-blocking; fix in this PR if convenient)

### 2. Dead imports left after the pool refactor
`run_daemon.py:133-134` still binds:
```python
_find_next_pipeline_ticket = _tp_mod.find_next_ticket
_process_ticket_pipeline = _tp_mod.process_ticket
```
Neither name is used anywhere in the module after the pool-based rewrite of `poll_ticket_pipeline`. Remove both lines to avoid confusion about which path is live. (`ticket_pipeline.find_next_ticket` / `process_ticket` themselves are still callable elsewhere, so don't delete them from `ticket_pipeline.py`.)

### 3. Pool-size settings are lazy singletons but not flagged `requires_restart`
`_init_pipeline_pools` (`run_daemon.py:1805`) creates each pool once for the daemon's lifetime. Changing `MAX_PARALLEL_TICKET_INTELLIGENCE` or `MAX_PARALLEL_READINESS` in the settings DB has no effect until the daemon restarts. Two options: (a) mark those two `SettingSpec`s `requires_restart=True` for UI accuracy; (b) actually recreate the pool on size change — probably overkill for V1. Option (a) is the low-effort fix and keeps behaviour honest for operators.

### 4. Doc/README sync
`docs/daemon-lifecycle.md:159` claims "≈5–10 s at the demo default". This becomes true only once issue #1 is fixed. Update the wording (or the code) so they agree.

### 5. Test bootstrap duplication (cosmetic)
Every T221 test file that needs a real SQLite DB copies the same 15-line `_load_sqlite_runtime_db` block. Consider a shared `conftest.py` fixture — not blocking, just churn multiplier for the next author.

---

## Coverage of ticket acceptance criteria

| AC | Status |
|---|---|
| Batch discovery + intake in one pass | ✅ |
| No 1-per-cycle throttle unless configured | ✅ |
| Poll interval configurable independently | ❌ (setting exists but unused — see #1) |
| Ticket Intelligence concurrency configurable independently | ✅ |
| Readiness concurrency configurable independently | ✅ |
| 10 issues intaken within 1–2 poll cycles | ✅ for intake; user-visible latency still gated by 30s poll (see #1) |
| Execution concurrency unchanged | ✅ (verified by `test_execution_workers_unchanged.py`) |
| Logs show discovered/intaked per poll | ✅ |
| Tests cover multi-issue single-poll intake | ✅ |

---

Fix issue #1 (wire `GITHUB_POLL_INTERVAL_SECONDS` into the sleep) and this is close to shippable. The rest are polish.

IMPLEMENTATION_FIX_REQUIRED
