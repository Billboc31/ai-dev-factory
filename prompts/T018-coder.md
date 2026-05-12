# Prompt Coder — T018

Implement runtime capability and failure detection.

Read:
- tools/agent_runner/run_ticket.py
- tools/agent_runner/run_step.py
- tickets/TODO/T018-runtime-capability-and-failure-detection.md
- runs/T018/plan.md

Constraints:
- preserve state unchanged on failure
- preserve workflow compatibility
- preserve snapshots and logs
- avoid unsafe automation
- keep changes bounded

Implement:
- runtime failure classification
- explicit runtime diagnostics
- detection of write permission issues
- detection of quota/provider failures
- targeted tests

Verify:
- workflow remains recoverable after failure
- runtime logs are explicit
- no regressions on fix loops or reviews
