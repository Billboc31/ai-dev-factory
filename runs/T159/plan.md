The plan is written to `runs/T159/plan.md`. Key changes from the previous attempt:

- **Section 2** now describes the full file-lock protocol: acquire `<db_path>.recovery.lock` via `fcntl.flock` before any check or mutation, release after schema init. The old misleading "atomic rename makes this safe" statement is replaced with the correct statement that the entire recovery sequence is a critical section.
- **Section 8** adds explicit tests for both the single-caller and concurrent-caller scenarios.
- **Acceptance criteria** adds three new verifiable conditions: lock acquired/released correctly, concurrent calls cannot race, and a test covers the race condition.
