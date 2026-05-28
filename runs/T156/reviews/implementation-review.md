I have a complete picture. Writing the review now.

---

## T156 — Implementation Review

**Reviewer:** Claude Sonnet 4.6
**Date:** 2026-05-28
**Branch:** `ticket/T156-t156-improve-runtime-tab-with-running-environments`

---

### Scope compliance

The implementation touches exactly the four files identified in the plan. No extraneous changes to `SandboxManager`, proxy infrastructure, `ProposalRunsTable`, or `RuntimeHealthPanel`. One minor plan inaccuracy: `runtimeDashboard.js` was listed as "No changes needed" but `stopSandboxRun` was added. This is not a scope drift — the Stop action button in the plan required it and it was simply an oversight in the plan itself.

---

### Backend — `services/control_api/routes/runtime_dashboard.py`

**Model extensions (lines 104–111):** All eight planned fields are present on `SandboxRunSummary`: `urls`, `ref`, `proxy_ready`, `healthcheck_status`, `smoke_status`, `failing_step`, `created_at`, `last_checked_at`. Types and defaults are correct.

**`_parse_sandbox_state` (lines 144–210):**
- `urls`: reads from `state.json["urls"]` with fallback to `build_sandbox_urls(sandbox_id)`, wrapped in try/except. ✅
- `proxy_ready`: checks `{proxy_routes_dir}/{sandbox_id}.yml` existence, guarded with try/except. ✅
- `validation.json`: loaded with try/except on `OSError | json.JSONDecodeError`; gracefully returns `None` for all three derived fields when the file is absent. ✅
- `ref` fallback chain (`ref → branch → commit`) is correct. ✅
- `sandbox_id` input validation via `re.fullmatch(r"[a-zA-Z0-9_\-]+", sandbox_id)` on all mutating endpoints prevents path traversal. ✅
- `shutil.rmtree` guarded by prior `404` check and active-status/lock checks — acceptable. ✅

One minor observation: `started_at = raw.get("started_at") or raw.get("created_at")` means a sandbox with only `created_at` in state.json will show the same value in both the `started_at` and `created_at` fields of the UI. Not a bug, just potentially confusing display. Non-blocking.

---

### Frontend — `SandboxRunsTable.jsx`

**Visual hierarchy:** Pretty URLs rendered before ports — fully compliant with the "primary URLs first" UX requirement. The "no proxy" badge handles the empty-URLs case cleanly.

**Collapsible ports (lines 150–168):** Ports are hidden by default, toggled per-card. ✅

**Status chips (lines 170–183):** `proxy_ready`, `healthcheck_status`, `smoke_status` each mapped to green/red/gray correctly. The conditional rendering `run.proxy_ready !== null && run.proxy_ready !== undefined` correctly handles the three-state (true/false/unknown) case. ✅

**Failing step banner (lines 103–114):** Shown only when `failing_step` is non-null; "View logs" links to the log drawer. ✅

**Action buttons (lines 222–249):**
- Refresh: calls `onRefresh?.()` which maps to `fetchSandboxRuns`. ✅
- Stop: disabled when `!isActive || deleting === run.id`. ✅
- Delete: disabled when `isActive || deleting === run.id` (prevents deleting a running sandbox from the UI layer in addition to the backend 409 guard). ✅
- Confirmation dialogs for both Stop and Delete. ✅

**CopyButton `.catch()` (line 52):** Clipboard failures are caught; no silent rejection. ✅

**Empty state (line 293):** "No running environments found." message renders when `runs.length === 0`. ✅

**Plan deviation — action bar vs. inline buttons:** The plan listed "Open Web, Open API, Copy URL" as action bar buttons. The implementation places these inline with each URL row instead. This is better UX: the button is immediately adjacent to the URL it acts on rather than requiring mapping in an action bar. Not a defect.

**Minor:** The URL name label is fixed at `w-8` (32px). Labels longer than ~4 characters (e.g. "admin", "metrics") will overflow. Non-blocking cosmetic issue.

**Minor:** `onDeleted` callback is reused as both delete-completion handler and Refresh handler (`onRefresh={onDeleted}` at line 309). Semantically awkward but functionally correct — both cases need a re-fetch.

---

### Frontend — `RuntimeDashboardPage.jsx`

Section renamed to "Running Environments" (line 138). Polling unchanged at 5s intervals. `fetchSandboxRuns` correctly wired as both `onDeleted` and implicitly `onRefresh`. ✅

---

### Frontend — `runtimeDashboard.js`

`stopSandboxRun` added (line 9), necessary for the Stop action. All other API functions present. ✅

---

### Acceptance criteria checklist

| Criterion | Status |
|---|---|
| `SandboxRunSummary` serializes all 8 new fields | ✅ |
| Missing `validation.json` returns `null` fields without error | ✅ |
| Runtime tab renders one card per sandbox | ✅ |
| Web/API pretty URLs appear prominently | ✅ |
| Ports only in collapsed section | ✅ |
| Copy-to-clipboard per URL | ✅ |
| Status chips for proxy/health/smoke | ✅ |
| Failing step banner when set | ✅ |
| Stop, Delete, and log-viewer actions work | ✅ |
| UI renders without JS errors on empty list | ✅ |
| Refresh action available | ✅ |
| Generic, project-agnostic | ✅ |

---

### Summary

The implementation fully satisfies all acceptance criteria. The four minor observations (started_at/created_at overlap, URL label width, onDeleted callback reuse, action layout deviation from plan) are all non-blocking and do not warrant a fix cycle.

IMPLEMENTATION_APPROVED
