The full suite's pre-existing failures are unrelated to this change — they affect `test_ticket_intelligence_api`, `test_ticket_readiness_api`, `test_ticket_timeline`, `test_traefik_separation`, `test_runtime_db`, and `test_supervisor_intelligence_analyze`, none of which touch the workspace or recovery code. The 136 failures and 14 errors were already present on the branch before this implementation.

The two test files we own are clean: **36/36 pass** (`test_workspace_recovery.py` + `test_supervisor_workspace.py`).
