# T020 Tester

Validate the local workflow daemon.

Verify:

- polling loop works
- auto-runnable states work
- human gates stop execution
- dry-run works
- logs exist
- no concurrent double-run occurs
- workflow compatibility is preserved
- tests pass

Checks:

- daemon scans `runs/*/state.json`
- only allowed states are launched
- human review gates remain blocking
- lock protection works
- subprocess execution is logged
- dry-run does not launch subprocesses
- existing workflow commands still work

Summarize:

- tests executed
- important runtime observations
- regressions detected or not
- final workflow compatibility verdict