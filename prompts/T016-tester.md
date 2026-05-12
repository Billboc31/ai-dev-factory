# Tester Prompt — T016

Validate runtime prompt snapshot persistence.

Read:
- tools/agent_runner/run_step.py
- tools/agent_runner/run_ticket.py
- tickets/TODO/T016-runtime-prompt-snapshots.md
- runs/T016/implementation-output.md

Verify:
- prompt snapshots are created
- files exist in runs/TXXX/prompts/
- attempt numbering increments correctly
- extra contexts appear in snapshots
- snapshot content matches runtime prompt
- snapshots exist even if execution fails
- runtime logs are preserved
- no regressions on review loops or fix loops

Run relevant tests and summarize results.
