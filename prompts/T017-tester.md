# Tester Prompt — T017

Validate workflow-aware commit and push checkpoints.

Read:
- tools/agent_runner/run_ticket.py
- tickets/TODO/T017-workflow-aware-commit-and-push.md
- runs/T017/implementation-output.md

Verify:
- commit includes expected ticket files
- staging remains scoped
- branch validation works
- push targets the correct ticket branch
- runtime Git logs exist
- workflow compatibility is preserved
- no regressions on fix loops or review loops

Run relevant tests and summarize results.