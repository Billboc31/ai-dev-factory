# Reviewer Prompt — T018

Review runtime capability and failure detection.

Read:
- tools/agent_runner/run_ticket.py
- tools/agent_runner/run_step.py
- tickets/TODO/T018-runtime-capability-and-failure-detection.md
- runs/T018/plan.md
- runs/T018/implementation-output.md

Verify:
- runtime failures are classified clearly
- write permission issues are detected
- quota/provider issues are detected
- state remains unchanged on failure
- runtime logs are explicit
- workflow compatibility is preserved
- changes remain bounded

Use the workflow decision keyword provided by runtime context.
