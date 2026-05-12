# Prompt Reviewer — T017

Review the workflow-aware commit and push implementation.

Read:
- tools/agent_runner/run_ticket.py
- tickets/TODO/T017-workflow-aware-commit-and-push.md
- runs/T017/plan.md
- runs/T017/implementation-output.md

Checks:
- staging scope is explicit
- no unsafe global staging
- branch validation works
- push targets the correct ticket branch
- runtime Git logs exist
- workflow compatibility preserved
- changes remain bounded

Use the workflow decision keyword provided by runtime context.
