All 48 tests green (34 T198 + 14 intelligence API).

Summary of the fix:

- **Rebased** `ticket/T198-...` onto `main` so commit `66165e13` (host-side delegation of intelligence analyze when API runs in Docker) is preserved. T198's own commits replayed cleanly — the three files flagged in the review were never touched on the branch, so the rebase was conflict-free.
- **Verified** zero diff vs `main` on `services/control_api/routes/intelligence.py`, `services/supervisor/main.py`, and `tests/test_ticket_intelligence_api.py`. The functions called out in the review (`_supervisor_url`, `_needs_host_exec`, `_delegate_analyze_to_supervisor`, the project-id forwarding, and `test_project_post_analyze_delegates_to_supervisor_in_docker`) are present.
- **Tests** — the 34 T198 tests plus the 14 intelligence API tests all pass (48/48).
- **Branch state** — local is now `ahead 19, behind 18` of origin; pushing the rebased branch requires a force-push, which I have not done (destructive on a shared ref). Let me know if you want me to push `--force-with-lease`.

The minor observations from the review (PLAN_APPROVED proxy, swallowed merge-state exceptions, project-id ignored in routes, prompt artifacts committed, T001-mislabeled checkpoint) were called out as non-blocking — I did not address them in this fix since the instructions specified only the rebase.
