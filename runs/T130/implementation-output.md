36/36 pass. All good. Let me now do a final summary of everything created and modified.

---

## Summary

Implementation complete. Here's what was built:

### New files (7)

| File | Purpose |
|------|---------|
| `tools/agent_runner/analysis_prompt_builder.py` | Pure string construction of the LLM prompt (file tree + scan + DeployProfile schema + generation instructions) |
| `tools/agent_runner/analysis_git_service.py` | Creates `ai-analysis/{project_id}-{YYYYMMDD-HHMMSS}` branch, commits `.ai-dev-factory/`, pushes, creates or updates PR via `gh` |
| `tools/agent_runner/run_analysis.py` | Host-side analysis worker: scans project, builds prompt, invokes LLM via `exec_cmd`, parses `--- BEGIN FILE ---` blocks, writes files, calls git service |
| `services/control_api/services/analysis_manager.py` | HTTP proxy from control API to supervisor for start/status/logs |
| `tests/test_analysis_prompt_builder.py` | 4 tests: file tree, schema, all 3 file instructions, determinism |
| `tests/test_analysis_manager.py` | 5 tests: delegation, unreachable supervisor, 409 lock, no supervisor URL, status proxy |
| `tests/test_analysis_git_service.py` | 3 tests: branch name format, PR create on new branch, PR edit on existing branch |

### Modified files (5)

| File | Changes |
|------|---------|
| `services/supervisor/main.py` | Added `_state_dir()`, analysis PID/log/state helpers, per-project lock, 4 endpoints: `POST /analysis/start`, `GET /analysis/{id}/status` (with zombie detection), `GET /analysis/{id}/logs`, `POST /analysis/{id}/stop` |
| `services/control_api/models/schemas.py` | Added `AnalysisStatus` model |
| `services/control_api/routes/deployer.py` | Added 3 routes: `POST /analyze` (202), `GET /analysis/status`, `GET /analysis/logs` |
| `apps/dashboard/src/api/deployer.js` | Added `analyzeProject`, `getAnalysisStatus`, `getAnalysisLogs` |
| `apps/dashboard/src/pages/DeployerPage.jsx` | Added `AnalysisStatusPanel`, `AnalysisLogsPanel`, "Analyze Project" button, analysis polling |

All 36 deployer + analysis tests pass. The 44 pre-existing failures are unrelated to this ticket (daemon/ticket workflow tests) and were failing before these changes.
