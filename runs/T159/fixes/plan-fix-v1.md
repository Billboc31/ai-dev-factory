T159 plan fix v1:

Required correction:
Protect SQLite recovery/quarantine with a file lock.

The current plan should not imply that atomic rename alone makes concurrent recovery safe.

Required updates to runs/T159/plan.md:

1. Replace the concurrent safety statement with:

File rename is atomic on POSIX, but recovery/quarantine must still be protected by a file lock.

2. Add:

- Add a file-lock guard around check_and_recover_db(db_path)
- lock path: <db_path>.recovery.lock
- acquire before integrity_check/quarantine/recreate
- release after recovery or empty DB initialization

3. Add acceptance criteria:

- concurrent recovery attempts cannot recreate/quarantine simultaneously
- recovery/quarantine is protected by a file lock
- recovery race conditions are tested
