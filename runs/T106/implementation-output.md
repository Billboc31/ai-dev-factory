Implementation complete. Here's a summary of what was built:

---

## Files created (6)

| File | Role |
|------|------|
| `tools/agent_runner/run_issue_mapper.py` | Standalone mapper: fetches GitHub issues, parses deps, classifies statuses, detects cycles, writes `.project-map.json` and `.project-map-activity.json` |
| `services/control_api/services/project_map_service.py` | Read-only service + `refresh_project_map()` trigger |
| `services/control_api/routes/project_map.py` | `GET /project-map`, `GET /project-map/activity`, `POST /project-map/refresh` |
| `apps/dashboard/src/api/projectMap.js` | Frontend API client |
| `apps/dashboard/src/pages/ProjectMapPage.jsx` | Project Map page — summary stats, parallelizable groups, blocked tickets, full table |
| `apps/dashboard/src/pages/IssueMapperActivityPage.jsx` | Mapper Activity page — rolling scan history |

## Files modified (4)

| File | Change |
|------|--------|
| `tools/agent_runner/run_daemon.py` | `--poll-project-map` (run mapper each cycle) + `--use-project-map` (next_recommended scheduling with FIFO fallback) |
| `services/control_api/models/schemas.py` | 5 new Pydantic models for project map |
| `services/control_api/main.py` | Registered `project_map` router |
| `apps/dashboard/src/App.jsx` | 2 new nav links + routes |
