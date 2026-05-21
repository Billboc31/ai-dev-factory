All 24 new tests pass and all 28 existing tests remain green. Here's a summary of what was implemented:

---

## Files created

| File | Description |
|------|-------------|
| `tools/agent_runner/scripts_prompt_builder.py` | Builds LLM prompt requesting 7 FILE blocks (6 scripts + deployment.md) |
| `tools/agent_runner/scripts_git_service.py` | Branch `ai-scripts/{id}-YYYYMMDD-HHMMSS`, stages scripts dir + deployment.md, creates/updates PR |
| `tools/agent_runner/run_scripts.py` | Worker CLI — scan → prompt → LLM → extract → write (chmod 0o755 for .sh) → git/PR → state JSON |
| `services/control_api/services/scripts_manager.py` | HTTP proxy to supervisor `/scripts/*` endpoints |
| `tests/test_scripts_generation.py` | 24 tests covering all layers with mocked AI/Git/PR calls |

## Files modified

| File | Change |
|------|--------|
| `services/supervisor/main.py` | Added `_scripts_*` helpers + `POST /scripts/start`, `GET /scripts/{id}/status`, `GET /scripts/{id}/logs`, `POST /scripts/{id}/stop` |
| `services/control_api/routes/deployer.py` | Added `POST /generate-scripts`, `GET /scripts/status`, `GET /scripts/logs` endpoints |
| `services/control_api/models/schemas.py` | Added `ScriptsStatus` model (mirrors `AnalysisStatus`) |
| `apps/dashboard/src/api/deployer.js` | Added `generateScripts`, `getScriptsStatus`, `getScriptsLogs` |
| `apps/dashboard/src/pages/DeployerPage.jsx` | Added `ScriptsStatusPanel`, `ScriptsLogsPanel`, "Generate Scripts" button, polling state |
