T159 review:

The plan is good overall.

Main required correction:
SQLite recovery/quarantine must be protected by a file lock.

Atomic rename alone is not enough because the full sequence is:
- integrity_check
- corruption decision
- DB quarantine
- recovery/recreate
- schema initialization

That whole flow is a critical section.

Recommendation:
Add a recovery lock file such as:
<db_path>.recovery.lock

Acceptance criteria to add:
- concurrent recovery attempts cannot recreate/quarantine simultaneously
- recovery is protected by a file lock
- race conditions are tested
