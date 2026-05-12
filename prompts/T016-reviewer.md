# Reviewer Prompt — T016

Review the implementation for runtime prompt snapshots.

Read:
- tools/agent_runner/run_step.py
- tools/agent_runner/run_ticket.py
- tickets/TODO/T016-runtime-prompt-snapshots.md
- runs/T016/plan.md
- runs/T016/implementation-output.md

Checks:
- snapshots are written to runs/TXXX/prompts/
- naming is deterministic
- attempts increment correctly
- extra contexts are included
- snapshot content matches runtime prompt
- snapshot is written before execution
- runtime logs are preserved
- no workflow regressions
- scope remains bounded

Use only the workflow decision keyword provided by runtime context.
