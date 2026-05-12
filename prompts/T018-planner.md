# Prompt Planner — T018

Plan runtime capability and failure detection.

Read:
- tools/agent_runner/run_ticket.py
- tools/agent_runner/run_step.py
- tickets/TODO/T018-runtime-capability-and-failure-detection.md

Goals:
- classify runtime failures
- preserve state on failure
- detect provider/quota issues
- detect write permission problems
- improve runtime observability
- keep changes bounded

Checks:
- where exit codes are handled
- where stdout/stderr are available
- where runtime logs are written
- how to avoid false positives

Produce a bounded implementation plan.
