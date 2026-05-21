Review written to `runs/T131/reviews/implementation-review.md`. Here's the summary:

---

## Review — T131: Supervisor Daemon Persistence

**Core implementation: correct.** The supervisor monitor loop, crash metadata, voluntary-stop flag, stale PID recovery, restart-on-crash policy, and dashboard CrashBanner all work as designed. Test coverage is solid across the critical paths.

**Two blocking issues require fixes before merge:**

### [BLOCKING 1] `docker-compose.yml` YAML indentation bug (line 24)
An extra space was inserted before `- AI_DEV_FACTORY_SUPERVISOR_URL=...`, breaking YAML parsing. The env var will either cause a Docker Compose parse error or be silently dropped, meaning the supervisor URL is never set in the container and the entire supervisor integration path is bypassed.

**Fix:** Remove the extra leading space on line 24.

### [BLOCKING 2] `restart_policy` not forwarded to supervisor
`daemon_manager.start()` sends only `{"exec_cmd": exec_cmd}` to the supervisor — `restart_policy` is omitted, so the supervisor always defaults to `"no-restart"`. Restart-on-crash can only be configured by calling the supervisor on port 8090 directly, not via the dashboard or control API.

**Fix:** Add `restart_policy: str = "no-restart"` to `daemon_manager.start()` and pass it through `_call_supervisor(...)`.

**Observations (non-blocking):** `supervisor_available` field is never populated; `last_exit_code` is `None` after a supervisor restart + crash (best-effort); no max restart count or backoff (follow-up).

IMPLEMENTATION_FIX_REQUIRED
