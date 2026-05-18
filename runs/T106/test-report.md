# Test Report — T106 — Project Issue Tree Agent and Dependency Map

**Date:** 2026-05-18  
**Tester:** Claude (Sonnet 4.6)  
**Branch:** ticket/T106-t106-project-issue-tree-agent-and-dependency-map  
**State at test time:** IMPLEMENTATION_APPROVED

---

## Acceptance Criteria

### AC1 — L'agent produit une map projet exploitable

**Status: PASS**

The agent `tools/agent_runner/run_issue_mapper.py` was executed against the real repository:

```
python tools/agent_runner/run_issue_mapper.py --runs-dir runs \
    --repo Billboc31/ai-dev-factory \
    --worktrees-dir /Users/pierrebocquet/ai-dev-factory-worktrees
```

Output:
- `runs/.project-map.json` written successfully with `generated_at`, `tickets[]`, `parallelizable_groups`, `next_recommended`, `cycles`, `summary`
- `runs/.project-map-activity.json` written with rolling history (4 entries after tests)
- Fetched 5 open issues from GitHub successfully
- Atomic write pattern (`.tmp` → rename) verified in code (lines 403–406)

Synthetic test with T106 in issue index confirmed correct status resolution: T106 (`IMPLEMENTATION_APPROVED`) → `runnable`, promoted to `next_recommended`.

---

### AC2 — Le dashboard affiche l'arbre des tickets

**Status: PASS**

- `apps/dashboard/src/pages/ProjectMapPage.jsx` exists (250 lines)
- `apps/dashboard/src/pages/IssueMapperActivityPage.jsx` exists (124 lines)
- Both pages are registered in `apps/dashboard/src/App.jsx`:
  - `/project-map` → `ProjectMapPage`
  - `/mapper-activity` → `IssueMapperActivityPage`
- Navigation links present: "Project Map" and "Mapper Activity"
- `apps/dashboard/src/api/projectMap.js` wires `getProjectMap`, `getProjectMapActivity`, `refreshProjectMap` to the API
- Auto-refresh every 15 seconds implemented in both pages
- Displays: ticket table, status badges, blocked section, parallelizable groups, cycle warnings, next recommended, summary bar

---

### AC3 — Les tickets parallélisables sont détectés

**Status: PASS**

`compute_parallelizable_groups()` (run_issue_mapper.py:293) verified by unit test:

- Two independent runnable tickets (T001, T002) → `[['T001'], ['T002']]` — separate groups, run in parallel ✅
- T002 depends on T001 (same connected component) → `[['T001']]` — T002 excluded until T001 done ✅
- Result stored in `parallelizable_groups` field of the map artifact
- Dashboard renders each group with visual grouping

---

### AC4 — Les tickets bloqués sont identifiés

**Status: PASS**

Two-pass status classification verified:

- `classify_ticket_status()` returns `blocked_dependency` when deps are not done ✅
- Pass-2 logic downgrades `runnable` → `blocked_dependency` when live dep status is not `done` ✅
- `blocked_retry` classification for retry-stopped tickets also present
- Blocked tickets section rendered separately in `ProjectMapPage` with dependency details

Dependency parsing regex tests (10 patterns): all PASS
- `depends on #N`, `blocked by #N`, `requires #N`, `requires TN`, `blocked by TN` → parsed as deps ✅
- `blocks #N`, `blocks TN` → parsed as blocks (inverted into blocker's dep_map) ✅

Cycle detection verified:
- 3-node cycle (A→B→C→A) → detected and reported ✅
- Linear chain (A→B→C) → no cycle ✅

---

### AC5 — Le daemon peut utiliser la map pour l'intake/scheduling

**Status: PASS** *(with noted limitation)*

Daemon flags verified:
```
--poll-project-map    Run issue mapper at each daemon cycle
--use-project-map     Use next_recommended for scheduling (fallback FIFO)
```

Both flags present and documented in `run_daemon.py`. Key functions `poll_project_map`, `_load_project_map` exist and are called from `run_once()`. Scheduling reorders the ticket queue to put `next_recommended` first.

**Known limitation (non-blocking, noted in implementation review):** The daemon reorders by `next_recommended` but does not actively gate/block tickets classified as `blocked_dependency`. A `blocked_dependency` ticket in `PLAN_APPROVED` state could still be processed. This is an ordering hint, not a hard gate. Accepted for V1 per review decision.

---

## Regressions

None observed. The implementation adds new files and optional flags; no existing daemon behavior is modified when `--use-project-map` is not set (FIFO fallback preserved).

---

## Blocking Issues

None.

---

## Non-blocking Observations

The following issues were flagged in the implementation review and remain:

1. `AUTO_RUNNABLE_STATES` / `HUMAN_GATE_STATES` duplicated between `run_issue_mapper.py` and `run_daemon.py` — divergence risk, post-merge cleanup recommended
2. `ProjectMapActivityEntry.ambiguities: list[Any]` — weak Pydantic typing
3. `compute_parallelizable_groups` docstring misleading about "no dependency between members"
4. Daemon `--use-project-map` is an ordering hint, not a blocking gate — should be documented

---

## Validation Result

**PASS — all 5 acceptance criteria satisfied.**

The agent produces a valid, exploitable project map. The dashboard shows both new pages wired to live API data. Parallelizable and blocked ticket detection algorithms are correct. The daemon integrates the map for intelligent scheduling with safe FIFO fallback.

---

TEST_COMPLETE
