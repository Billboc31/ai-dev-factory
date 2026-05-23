## Review — T141 Implementation

### Résumé

The plan review explicitly narrowed T141's scope to a focused V1: fix `stop()`, add `restart()` and `refresh()`, enrich the dashboard with `runtime_root` and `uptime_seconds`, and wire lifecycle endpoints in both the sandbox and dashboard routers. The implementation faithfully follows the approved plan. All 33 tests pass.

---

### Points validés

- **`stop()`** — calls `_terminate_sandbox_supervisor()` (SIGTERM via PID file), runs `docker compose down`, cleans `*.pid`/`*.lock` from `sandbox_runtime_root` with per-file OSError catch. Port slot deliberately retained for restart reuse (plan-approved).
- **`restart()`** — clean `stop()` → `start()` chain, no extra state drift.
- **`refresh()`** — pure read, no subprocess. Verified by test.
- **Routes** — `POST /{id}/restart` and `/{id}/refresh` return 200/404 correctly. Dashboard stop/restart endpoints delegate to the shared `SandboxManager` instance via the same `app.state._sandbox_manager` key, avoiding duplicate instances.
- **Dashboard enrichment** — `SandboxRunSummary` gains `runtime_root` and `uptime_seconds`; computation is timezone-aware and guarded.
- **Input validation** — dashboard endpoints validate `sandbox_id` with regex, matching existing practice.
- **Test coverage** — 5 new manager tests (supervisor SIGTERM, PID/lock cleanup, port retention, restart transition, refresh no-subprocess) + 4 route-level 200/404 tests. All correct.

---

### Problèmes détectés

**Minor — uptime inaccuracy after restart.** `SandboxState` has no `started_at` field; `_parse_sandbox_state()` falls back to `created_at`. After a restart, uptime counts from sandbox creation, not the last `start()`. This is a plan omission rather than an implementation bug. Recommend adding `started_at: str | None` to `SandboxState` and setting it in `start()` in a follow-up.

**Minor — non-supervisor workers not explicitly SIGTERM'd.** `stop()` SIGTERMs the supervisor and removes stale PID files, but does not signal daemon/worker processes directly. The design relies on supervisor to cascade SIGTERM to children. Acceptable within the plan's scope.

**Observation — port slot not released on stop.** `plan-fix-1.md` (the guidance document) said "release allocated ports" on stop. The final approved `plan.md` overrides this: port slot is retained so `restart()` reuses the same ports. Implementation is correct per the approved plan, but operators should know that `destroy()` (not `stop()`) is the only reclamation path. Stopped sandboxes hold their port slots indefinitely.

---

### Décision

**APPROVED** — The implementation is a faithful and clean delivery of the approved plan. No blocking issues. No security regressions.

---

IMPLEMENTATION_APPROVED
