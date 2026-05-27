The simplified V1 plan is written. Here's a summary of what changed from the rejected plan:

**Removed (deferred to follow-up ticket):**
- Bounded auto-fix loop (`run_deploy_with_autofix`)
- Automatic patch application and diff parsing
- Retry orchestration, stagnation guard, progress detection
- Iteration history JSON (`iteration-{N}.json`, `summary.json`)
- `AutoFixCfg` schema and `allowed_fix_paths` enforcement
- New REST endpoints (`/deploy-with-autofix`, `/deploy-iterations`)

**Kept (V1 scope):**
- Optional `smoke.sh` step after healthcheck in both `run_sandbox.py` and `deployer_runner.py`
- Distinct `healthcheck_status` / `smoke_status` fields in state
- `validation.json` artifact written before cleanup
- AI fix **proposal only** (read-only `fix-proposal.md`, no application) when `AI_DEV_FACTORY_EXEC_CMD` is set
- New `ai/roles/deployer-fixer.md` role file
- Schema extension in `schemas.py` for `"skipped"` status
