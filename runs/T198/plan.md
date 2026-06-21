## Objective

Introduce an advisory Readiness Evaluator that decides whether a ticket can enter the development pipeline. Persist one `ticket_readiness` row per ticket (canonical lowercase snake_case statuses including `ready_candidate` and `blocked`, plus blocking reasons), and expose it via API and dashboard, mirroring the existing Ticket Intelligence pattern. Execution behaviour, scheduler, and worker dispatch are not changed.

## Included

- **Canonical status enum (used in DB, evaluator, API, tests)**
  - `not_started`, `queued`, `running`, `ready_candidate`, `blocked`, `failed`.
  - UI is the only layer that maps these to human-readable labels (`NOT STARTED`, `QUEUED`, `RUNNING`, `READY CANDIDATE`, `BLOCKED`, `FAILED`). Backend logic and tests never use uppercase forms.

- **DB schema (`tools/agent_runner/runtime_db.py`)**
  - Add `CREATE TABLE IF NOT EXISTS ticket_readiness (...)` to `_SCHEMA` with columns:
    - `ticket_id TEXT PRIMARY KEY`
    - `readiness_status TEXT NOT NULL` (canonical enum above)
    - `ready_candidate INTEGER NOT NULL DEFAULT 0`
    - `blocking_reasons_json TEXT` (JSON array of strings)
    - `warnings_json TEXT` (JSON array of strings)
    - `dependency_check_status TEXT` (`passed|failed|unknown`)
    - `approval_check_status TEXT` (`passed|failed|unknown`)
    - `context_freshness_status TEXT` (`fresh|unknown|stale` — `stale` is reserved, never produced yet)
    - `human_approval_required INTEGER`
    - `human_approval_present INTEGER`
    - `main_sha_when_evaluated TEXT`
    - `evaluated_at TEXT`
    - `created_at TEXT NOT NULL`
    - `updated_at TEXT NOT NULL`
  - Add `upsert_ticket_readiness(db_path, ticket_id, **fields)` and `get_ticket_readiness(db_path, ticket_id)` mirroring the `ticket_intelligence` helpers (JSON list fields encoded on write, decoded on read).
  - Rebind both functions in the Postgres backend selection block at the bottom of the file.

- **Postgres backend (`tools/agent_runner/runtime_db_pg.py`)**
  - Add equivalent `ticket_readiness` table creation and `upsert_ticket_readiness` / `get_ticket_readiness` implementations.

- **Merge-state helper (`tools/agent_runner/ticket_merge_state.py`, new)**
  - Public function:
    ```
    is_ticket_merged(project_root, ticket_id) -> MergeCheckResult
    ```
    where `MergeCheckResult` is a small dataclass / TypedDict with fields:
    - `status`: one of `merged`, `not_merged`, `unknown`
    - `source`: one of `runtime_db`, `github_metadata`, `git_fallback`, `unknown`
    - `reason`: short human-readable string
  - Resolution order (return on first definitive answer; only fall through on `unknown`):
    1. **Runtime DB**: query existing ticket / run / PR rows for a recorded merge state (e.g. PR `merged_at` / `state == "merged"` if such columns exist). If a row exists and is decisive, return `merged|not_merged` with `source="runtime_db"`.
    2. **GitHub metadata helper**: if a project helper exposes PR/issue state (search for an existing `gh`/GitHub client wrapper in `tools/agent_runner/`), use it; return `source="github_metadata"`.
    3. **Git fallback**: `git log --grep "T<id>" main` (and `git merge-base --is-ancestor` where applicable). Treat hits as `merged` with `source="git_fallback"` only when at least one match is found; otherwise `not_merged`.
  - If none of the three yields a definitive answer, return `status="unknown"` with `source="unknown"`.
  - This helper is the only call site the evaluator uses for dependency merge state; the evaluator must never call `git log` directly.

- **Evaluator service (`tools/agent_runner/ticket_readiness_evaluator.py`, new)**
  - Public `run_evaluation(db_path, ticket_id, ticket_content, project_root)`, designed to run in a background thread; transitions `readiness_status` `queued → running → ready_candidate|blocked|failed`; never raises (failures are persisted with `readiness_status="failed"` and a reason in `warnings`).
  - Internal helpers:
    - `_check_intelligence(db_path, ticket_id)` — fails with reason `Missing Ticket Intelligence analysis` when `get_ticket_intelligence(...)` returns `None` or `analysis_status != "completed"`. Returns `passed|failed`.
    - `_check_dependencies(ticket_content, project_root)` — parse `Depends on T\d+`, `After T\d+`, `Blocked by T\d+` (case-insensitive) from the ticket body. For each prerequisite, call `is_ticket_merged(project_root, dep_id)`:
      - `merged` → contributes no blocking reason.
      - `not_merged` → blocking reason `Dependency T<ID> not merged`.
      - `unknown` → blocking reason `Dependency T<ID> merge state unknown` (also blocks readiness by default, as the review requires).
      - Returns `passed` (only if every prerequisite is `merged`), else `failed`. With no declared prerequisites the status is `passed`.
    - `_check_human_approval(intelligence_row, project_root, ticket_id)` — if `requires_human_plan_review == 1`, look for a human-approval marker (file `runs/<ticket>/plan-approved.md` or equivalent if already conventional; otherwise treat absence as missing). Returns `passed|failed` and sets `human_approval_required` / `human_approval_present`. Missing approval → blocking reason `Human plan approval missing`.
    - `_check_context_freshness(project_root)` — capture `main_sha_when_evaluated` via `git rev-parse main`; set `context_freshness_status="fresh"` on success, `unknown` if the git call fails. No comparison logic in this ticket; `stale` is never emitted.
  - Assemble `blocking_reasons` from failed checks; set `ready_candidate=1` and `readiness_status="ready_candidate"` iff every check is `passed`; otherwise `readiness_status="blocked"`. Persist with `evaluated_at=<now ISO8601>`.

- **API schemas (`services/control_api/models/schemas.py`)**
  - `TicketReadiness` mirrors the DB row, with `blocking_reasons` / `warnings` typed as `list[str]` and `readiness_status` typed as the canonical lowercase enum.
  - `TicketReadinessQueued` carries `ticket_id` and `readiness_status="queued"`.
  - API responses use canonical lowercase values; no UI-style labels in payloads.

- **API routes (`services/control_api/routes/readiness.py`, new)**
  - `GET /tickets/{ticket_id}/readiness` → 200 with `TicketReadiness`; 404 when no row exists.
  - `POST /tickets/{ticket_id}/evaluate-readiness` → 202 with `TicketReadinessQueued`; idempotent when current `readiness_status` is `queued` or `running` (returns the existing row's status, does not spawn a second thread); otherwise sets the row to `queued` and launches `ticket_readiness_evaluator.run_evaluation` in a daemon thread.
  - Add `/projects/{project_id}/...` variants following the pattern of `intelligence.py`.
  - Register the new router in `services/control_api/main.py` next to the existing `intelligence` router include.

- **Frontend API helper (`apps/dashboard/src/api/tickets.js`)**
  - Add `getTicketReadiness(ticketId, projectId)` and `postEvaluateReadiness(ticketId, projectId)`.

- **Frontend panel (`apps/dashboard/src/components/TicketReadinessPanel.jsx`, new)**
  - Maps canonical statuses to user-facing labels via a small `STATUS_LABELS` constant (`ready_candidate → "READY CANDIDATE"`, `blocked → "BLOCKED"`, etc.).
  - Displays: status badge, `READY CANDIDATE` highlight when applicable, blocking reasons list, warnings list, last evaluation date, dependency / approval / context-freshness sub-states, and an `Evaluate readiness` button that triggers the POST and polls (reuse `usePolling`).
  - Mounted on `apps/dashboard/src/pages/TicketDetailPage.jsx` next to `TicketIntelligencePanel`.

- **Tests (`tests/`)**
  - `test_ticket_readiness_db.py` — schema creation in SQLite, `upsert` then `get` round-trip including JSON-list fields and default values.
  - `test_ticket_merge_state.py` — covers the helper: runtime-DB hit returns `source="runtime_db"`; runtime-DB miss with git hit returns `source="git_fallback"`; nothing found returns `status="unknown"`, `source="unknown"`.
  - `test_ticket_readiness_evaluator.py` — each check in isolation:
    - missing intelligence → `readiness_status="blocked"`, reason `Missing Ticket Intelligence analysis`;
    - dependency `not_merged` → blocked with reason `Dependency T<ID> not merged`;
    - dependency `unknown` → blocked with reason `Dependency T<ID> merge state unknown`;
    - missing human approval → blocked with reason `Human plan approval missing`;
    - all checks pass → `readiness_status="ready_candidate"`, `ready_candidate=1`, empty `blocking_reasons`, non-null `evaluated_at` and `main_sha_when_evaluated`.
  - `test_ticket_readiness_api.py` — GET returns 404 when no row; POST returns 202 with `readiness_status="queued"`; second POST while `queued`/`running` is idempotent; project-scoped route mirror.

## Excluded

- Any change to scheduler, worker dispatch, daemon state machine, execution queue ordering, or merge logic.
- Implementing `READY_TO_TAKE` or any transition out of `ready_candidate`.
- Comparing `main_sha_when_evaluated` against current `main` to detect staleness — only the field and the `fresh|unknown|stale` enum surface are introduced; `stale` is never produced in this ticket.
- Automatic triggering of readiness evaluation (no daemon hook, no auto-run after Ticket Intelligence completes). Evaluation runs only on explicit POST.
- Enforcing readiness as a gate before any existing pipeline step.
- Refactors to `ticket_intelligence_analyzer.py` or shared extraction of helpers between analyzer and evaluator beyond the new `ticket_merge_state.py` helper.
- New CLI entry point for the evaluator; it is reachable only via the API in this ticket.
- Uppercase / human-readable status strings in DB, evaluator, API payloads, or tests — those exist only as UI labels.

## Acceptance criteria

- `ticket_readiness` table exists in both SQLite and Postgres backends; `upsert_ticket_readiness` / `get_ticket_readiness` round-trip cleanly, including JSON list fields.
- All readiness status values stored in the DB and returned by the API are canonical lowercase snake_case (`not_started`, `queued`, `running`, `ready_candidate`, `blocked`, `failed`). No uppercase form appears in backend logic or tests.
- The dashboard renders human-readable labels (e.g. `READY CANDIDATE`, `BLOCKED`) derived from the canonical values via a UI-only mapping.
- `POST /tickets/{ticket_id}/evaluate-readiness` returns HTTP 202 with `readiness_status="queued"`, persists a row, and triggers a background evaluation; a second POST while the row is `queued` or `running` is idempotent.
- `GET /tickets/{ticket_id}/readiness` returns the persisted result with `blocking_reasons` and `warnings` as JSON arrays and a canonical `readiness_status` value; 404 when no row exists.
- Dependency merge checks in the evaluator go through `is_ticket_merged(project_root, ticket_id)`; the evaluator code contains no direct `git log --grep` call.
- `is_ticket_merged` prefers structured metadata: it returns `source="runtime_db"` or `source="github_metadata"` whenever those sources can decide, and only returns `source="git_fallback"` after the structured sources have produced no answer.
- When `is_ticket_merged` returns `status="unknown"` for any declared prerequisite, the evaluator marks the ticket `blocked` with a reason of the form `Dependency T<ID> merge state unknown`.
- Evaluator marks a ticket `blocked` with reason `Missing Ticket Intelligence analysis` when no completed intelligence row exists.
- Evaluator marks a ticket `blocked` with reason `Dependency T<ID> not merged` when a prerequisite is recorded as not merged.
- Evaluator marks a ticket `blocked` with reason `Human plan approval missing` when intelligence has `requires_human_plan_review=1` and no approval marker is present.
- When every check passes, the row has `readiness_status="ready_candidate"`, `ready_candidate=1`, an empty `blocking_reasons` array, and non-null `evaluated_at` and `main_sha_when_evaluated`.
- The `TicketReadinessPanel` renders the status, badge, reasons, warnings, sub-check states, and last evaluation date, and can trigger evaluation.
- No existing daemon / scheduler / worker code paths are modified; `pytest tests/` continues to pass.
