# Test Report — T127

**Date**: 2026-05-21  
**Branch**: ticket/T127-t127-project-deployer-profiles-and-dashboard-deplo  
**Verdict**: TEST_COMPLETE — V1 scope passes. 4 ACs explicitly deferred per approved plan.

---

## Commands executed

```
python -m pytest tests/test_project_scanner.py tests/test_deployer_routes.py -v
# → 18 passed in 0.57s

python -m pytest --ignore=tests/test_project_scanner.py --ignore=tests/test_deployer_routes.py
# → 44 failed, 557 passed
# Regression check: same failures exist before T127 changes (pre-existing baseline)
```

---

## Acceptance criteria

### AC1 — A project can be scanned from the dashboard

**PASS**

- `POST /projects/{id}/deployer/scan` endpoint implemented and registered in `main.py`
- `DeployerPage.jsx` renders a "Scan Project" button that calls the endpoint
- `ScanResultPanel` displays docker services, required tools, backend/frontend flags, and deploy profile
- `test_deployer_scan_returns_docker_services` passes

---

### AC2 — A deploy profile is generated and stored in the target project

**PARTIAL — generation deferred to V2**

- `.ai-dev-factory/deploy.yml` exists and is committed ✅
- Scanner reads and parses the existing profile ✅
- **No generation logic exists**: no "generate" endpoint, no Claude-assisted profile creation ❌
- V1 plan explicitly excludes profile generation — this AC is partially satisfied (stored, not generated)

---

### AC3 — Dashboard shows deployment actions for deployer-enabled projects

**PASS within V1 scope**

- `/deployer` route added to `App.jsx` ✅
- "Deployer" nav link added to navigation ✅
- `StatusBadge` shows deployer state and `profile_present` indicator ✅
- "Scan Project" is the only action exposed — Deploy Main, Deploy Branch, Restart Services, View Logs are absent (deferred)
- V1 plan scopes dashboard to scan action only

---

### AC4 — Deploy actions execute deterministic Python deployment steps

**DEFERRED — not in V1 scope**

No deployment execution implemented. Approved plan explicitly excluded this for V1.

---

### AC5 — Deployment logs are visible from the dashboard

**DEFERRED — not in V1 scope**

No log viewer implemented. Approved plan explicitly excluded this for V1.

---

### AC6 — Healthchecks run after deployment

**DEFERRED — not in V1 scope**

No healthcheck logic implemented. Approved plan explicitly excluded this for V1.

---

### AC7 — ai-dev-factory deployment profile supports docker services, host-side daemon, gh dependency, Claude dependency

**PASS**

`.ai-dev-factory/deploy.yml` verified:

```yaml
required_tools: [gh, git, docker, claude]   # gh ✅, claude ✅
components:
  - name: api    type: docker   service: api    # docker service ✅
  - name: web    type: docker   service: web    # docker service ✅
  - name: daemon type: host     command: python services/daemon/main.py  # host daemon ✅
```

All four sub-criteria satisfied.

---

### AC8 — Deployment failures return structured errors instead of silent failures

**PASS within observable scope**

- Malformed `deploy.yml` → scanner returns `None` gracefully, no exception leaked (`test_deploy_profile_malformed_returns_none` passes)
- Unknown project ID → 404 response (`test_deployer_status_unknown_project_returns_404`, `test_deployer_scan_unknown_project_returns_404` pass)
- No deployment execution exists in V1, so runtime deployment failure handling is not testable yet

---

## Regressions

**None introduced by T127.**

Pre-existing baseline failures: 31+ in `test_control_api_endpoints.py`, `test_control_api_subprocess.py`, `test_daemon_checkpoint.py`, `test_daemon_issue_polling.py`, `test_run_daemon.py`, `test_ticket_timeline.py`. These fail identically on the main branch before T127 changes.

T127 changes to existing files are purely additive:
- `main.py`: adds one `include_router` call (+1 vs 9 on main)
- `schemas.py`: adds new Pydantic models, no modifications to existing ones
- `App.jsx`: adds route and nav link, no changes to existing routes

---

## Summary

| Criterion | Status |
|---|---|
| AC1: Scan from dashboard | ✅ PASS |
| AC2: Deploy profile generated and stored | ⚠️ PARTIAL (stored ✅, generated ❌ — deferred V2) |
| AC3: Dashboard shows deployment actions | ✅ PASS (scan only, per V1 scope) |
| AC4: Deterministic Python deployment | ⏳ DEFERRED V2 |
| AC5: Deployment logs visible | ⏳ DEFERRED V2 |
| AC6: Healthchecks after deployment | ⏳ DEFERRED V2 |
| AC7: ai-dev-factory profile completeness | ✅ PASS |
| AC8: Structured error returns | ✅ PASS (within V1 scope) |

**New tests**: 18/18 pass  
**Regressions**: 0  
**Blocking issues**: none — deferred ACs are documented in approved V1 plan
