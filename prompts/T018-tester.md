# Tester Prompt — T018

Validate runtime capability and failure detection.

Read:
- tools/agent_runner/run_ticket.py
- tools/agent_runner/run_step.py
- tickets/TODO/T018-runtime-capability-and-failure-detection.md
- runs/T018/implementation-output.md

Verify:
- runtime failures are classified
- write permission issues are detected
- quota/provider issues are detected
- state remains unchanged on failure
- runtime logs contain explicit diagnostics
- workflow compatibility is preserved
- no regressions on snapshots, reviews, or fix loops

Run relevant tests and summarize the results.
