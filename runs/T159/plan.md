Plan updated at `runs/T159/plan.md`. The two changes from the review are incorporated:

1. **Section 2** — replaced the incorrect "File rename is atomic on POSIX; function is safe for concurrent callers" with the correct statement that rename is atomic but recovery/quarantine must still be protected by a file lock (`<db_path>.recovery.lock`), with an explicit description of when to acquire and release it.

2. **Acceptance criteria** — added three new verifiable conditions:
   - Recovery/quarantine is protected by a file lock at `<db_path>.recovery.lock`.
   - Concurrent recovery attempts cannot race through quarantine or recreate simultaneously.
   - A test covers the race condition (two concurrent callers against a corrupt DB).
