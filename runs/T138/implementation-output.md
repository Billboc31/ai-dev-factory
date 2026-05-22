All 16 tests pass. Here's a summary of what was implemented:

## Files created / modified

**New files:**
- `services/control_api/models/auto_fix.py` — `ProposalStatus`, `PatchProposal`, `AutoFixProposal` Pydantic models
- `services/supervisor/auto_fix_proposer.py` — `collect_failure_context`, `call_ai_runtime` (mirrors `_invoke_llm`), `validate_patches`, `persist_proposal`/`load_proposal`/`list_proposals`
- `services/control_api/services/auto_fix_runner.py` — HTTP proxy to supervisor (mirrors `sandbox_runner.py`)
- `services/control_api/routes/auto_fix.py` — 3 endpoints: `POST /projects/{id}/auto-fix/propose`, `GET /projects/{id}/auto-fix/proposal/{pid}`, `GET /projects/{id}/auto-fix/proposals`
- `apps/dashboard/src/api/autoFix.js` — Axios client
- `apps/dashboard/src/components/AutoFixPanel.jsx` — read-only patch preview UI with polling
- `tests/test_auto_fix_proposer.py` — 8 proposer unit tests
- `tests/test_auto_fix_routes.py` — 3 route integration tests

**Modified files:**
- `services/supervisor/main.py` — added `uuid` import + 3 new auto-fix endpoints (`POST/GET /auto-fix/…`) with background thread execution
- `services/control_api/main.py` — registered `auto_fix.router`
- `apps/dashboard/src/App.jsx` — added `AutoFixPanel` import + `/auto-fix` route + nav link
