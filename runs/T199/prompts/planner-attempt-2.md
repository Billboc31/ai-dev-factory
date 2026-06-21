# GLOBAL CONTEXT

# Global Context — ai-dev-factory

## Vision

ai-dev-factory est un framework générique d’orchestration de développement assisté par IA.

Le système doit permettre :
- création de tickets structurés
- génération de prompts spécialisés
- orchestration planner/coder/reviewer/tester
- reviews IA intermédiaires
- maintenance automatique de la mémoire projet
- workflow GitHub-centric basé sur PR

Détails lifecycle PR, branches et artefacts : [pr-lifecycle.md](./pr-lifecycle.md).

## Principes

- GitHub = source de vérité workflow
- PR = protocole de communication agentique
- mémoire versionnée dans le repository
- architecture explicitement documentée
- aucun merge sans validations IA requises

## Reviews obligatoires

Aucun merge sans :
- PLAN_APPROVED
- IMPLEMENTATION_APPROVED
- MEMORY_APPROVED

## Mémoire

Le système mémoire est composé de :
- global-context.md
- project-life.md
- decisions-log.md

## Workflow cible

1. Ticket
2. Classification risque
3. Planner
4. Review plan
5. Coder
6. Reviewer
7. Tester
8. Review implémentation
9. Memory updater
10. Review mémoire
11. Merge

---

# ROLE

# Role — Planner

## Mission

Lire un ticket et produire un plan d’implémentation court, concret, borné et actionnable.

## Tu dois

- comprendre le ticket
- proposer les étapes minimales
- lister les fichiers à créer ou modifier
- identifier les risques
- expliciter le hors scope
- produire un plan Markdown versionnable
- signaler les hypothèses nécessaires

## Tu ne dois pas

- coder
- réécrire le ticket
- anticiper les tickets suivants
- élargir le scope
- masquer les incertitudes

## Sortie attendue

Un fichier de plan conforme à `ai/templates/plan-template.md`.

## Règles

- le plan doit rester court
- le plan doit être exécutable par un Coder sans ambiguïté
- toute hypothèse doit être explicite
- toute dérive de scope doit être refusée

## Structure obligatoire

Tout plan doit contenir au minimum **les sections suivantes** (titres
Markdown niveau 2 — `##`). Les variantes anglaises sont acceptées à l'identique :

| Français (recommandé)         | English equivalent       |
|-------------------------------|--------------------------|
| `## Contexte`                 | `## Context`             |
| `## Objectif`                 | `## Objective`           |
| `## Inclus`                   | `## Included`            |
| `## Hors scope`               | `## Excluded`            |
| `## Critères d'acceptation`   | `## Acceptance criteria` |

Choisis une langue par plan, ne mélange pas FR et EN dans un même plan.

Ces titres sont obligatoires même si une section est courte : un ticket
trivial peut produire un plan court, mais la structure doit rester stable.

Ne jamais produire uniquement un résumé.
Ne jamais produire un compte rendu d’implémentation.

## Interdictions absolues

Tu ne dois jamais écrire :
- "implémentation terminée"
- "syntaxe valide"
- "changements appliqués"
- "voici ce qui a été fait"

Tu dois produire uniquement un plan futur, pas un compte rendu passé.

---

# SKILL: workflow-discipline

# Skill — Workflow Discipline

## Objectif

Faire respecter le lifecycle officiel des tickets et PR IA.

## Règles

- respecter l’ordre des étapes du workflow
- ne pas bypass les reviews obligatoires
- maintenir les statuts cohérents
- conserver les artefacts versionnés
- séparer plan, implémentation et mémoire

## Refuser si

- une review obligatoire est sautée
- la mémoire est mise à jour avant validation implémentation
- le workflow officiel est contourné

---

# SKILL: architecture-discipline

# Skill — Architecture Discipline

## Objectif

Préserver la cohérence architecture du projet dans le temps.

## Règles

- respecter les invariants documentés
- éviter les couplages implicites
- éviter les dépendances inutiles
- éviter les refactors transversaux non demandés
- documenter toute nouvelle règle structurante
- privilégier les changements locaux et bornés

## Refuser si

- le scope dérive
- plusieurs couches sont modifiées sans justification
- des conventions existantes sont cassées
- la mémoire projet devient incohérente

---

# SKILL: documentation

# Skill — Documentation

## Objectif

Maintenir une documentation utile, concise et alignée avec le code réel.

## Règles

- documenter les décisions importantes
- éviter les documentations vagues
- garder la mémoire projet cohérente
- expliciter les invariants architecture
- préférer Markdown simple et versionnable

## Refuser si

- la documentation diverge du comportement réel
- la mémoire contient des suppositions non validées
- des décisions importantes ne sont pas tracées

---

# TASK

The ticket follows.
# Generic Planner Task Read the ticket below and produce a detailed implementation plan. 

## Required output structure (strict) Your reply **MUST** be a Markdown document containing **exactly** these four level-2 headings, in this order, spelled exactly as shown:
## Objective
## Included
## Excluded
## Acceptance criteria
These headings are mandatory even for trivial tickets. A short plan is acceptable — an unstructured plan is not. - ## Objective — one or two sentences describing what the change achieves. - ## Included — concrete changes (files, functions, logic, tests). - ## Excluded — what is explicitly out of scope for this ticket. - ## Acceptance criteria — verifiable conditions a reviewer can check. ## Invalid output Your reply is **invalid** if any of the four headings above is missing, renamed, mistyped, or replaced by a synonym (e.g. ## Goal, ## Scope, ## In scope, ## Out of scope, ## Plan, ## Tasks are **not** accepted). An invalid reply will be rejected by the automated validator and the ticket will be retried. You **MUST NOT** write: - "implementation done" - "changes applied" - "here is what was done" - any past-tense report of work already performed You produce a *future* plan, not a status report. ## Minimal valid example (for a trivial ticket)
markdown
## Objective
Rename the helper `foo()` to `bar()` in `utils.py` to align with the new
naming convention. Behaviour is preserved.

## Included
- `utils.py`: rename `foo` → `bar`, update the docstring.
- `tests/test_utils.py`: update the single import and assertion.

## Excluded
- Renaming callers in other modules (tracked in a follow-up ticket).
- Any logic change inside `foo` / `bar`.

## Acceptance criteria
- `utils.py` no longer defines `foo`.
- `pytest tests/test_utils.py` passes.
- No other file references the old name.

The ticket follows.



# T199 — Add Human Approval Workflow and READY_TO_TAKE lifecycle

**Source**: GitHub Issue #255

## Description

# Add Human Approval Workflow and READY_TO_TAKE lifecycle

## Context

AI Dev Factory now provides:

```text
Ticket Intelligence
↓
Ticket Readiness Evaluation
```

A ticket can now become:

```text
ready_candidate
blocked
```

However, the system still lacks an explicit human approval workflow before a ticket is allowed to enter execution.

We want to introduce a dedicated human validation step.

The objective is to allow humans to decide which tickets may actually be executed by AI agents.

## Goal

Introduce a human approval workflow and a new lifecycle state:

```text
ready_to_take
```

Workflow:

```text
Ticket created
↓
Ticket Intelligence
↓
Ticket Readiness Evaluation
↓
READY_CANDIDATE
↓
Human approval
↓
READY_TO_TAKE
```

Only READY_TO_TAKE tickets will eventually be eligible for automatic execution.

Execution behavior itself is not implemented in this ticket.

## Non-goals

Do not:

- modify scheduler behavior
- automatically start execution
- dispatch workers
- enforce execution rules
- automatically approve tickets
- implement parallel execution

This ticket only introduces the approval workflow.

## Database

Create a new table:

```text
ticket_approvals
```

Suggested columns:

```text
id
project_id
ticket_id
approval_type
approval_status
approved_by
approval_comment
approved_at
created_at
updated_at
```

Canonical statuses:

```text
pending
approved
rejected
```

Approval types:

```text
execution
plan
code
```

For this ticket only `execution` approval is required.

## Ticket lifecycle additions

Introduce new ticket lifecycle state:

```text
ready_to_take
```

Rules:

```text
ready_candidate
+ execution approval approved
→ ready_to_take
```

Otherwise:

```text
ready_candidate
+ no approval
→ remains ready_candidate
```

Rejected approval:

```text
approval_status = rejected
```

must return the ticket to:

```text
blocked
```

with a visible reason.

## Approval service

Create:

```text
tools/agent_runner/ticket_approval_service.py
```

Responsibilities:

- create approval requests
- approve tickets
- reject tickets
- retrieve approval history
- compute effective execution eligibility

Suggested API:

```python
request_execution_approval(...)
approve_execution(...)
reject_execution(...)
get_ticket_approvals(...)
```

## API

Add endpoints:

```text
GET /tickets/{ticket_id}/approvals
POST /tickets/{ticket_id}/approve-execution
POST /tickets/{ticket_id}/reject-execution
```

Approval endpoints should:

- verify ticket currently has `ready_candidate`
- persist approval record
- update effective readiness state

## Frontend

Add a new section on the ticket page:

```text
Human Approval
```

Display:

- approval status
- approval history
- approver
- approval date
- comments

Buttons:

```text
Approve for execution
Reject execution
```

Buttons are enabled only when:

```text
readiness_status == ready_candidate
```

## Board UI

Display clear badges:

```text
READY CANDIDATE
READY TO TAKE
BLOCKED
```

Add filtering by approval state.

## Audit requirements

All approvals and rejections must be persisted.

Nothing should be overwritten.

Approval history must remain visible.

Example:

```text
2026-06-21
Pierre
Approved execution
Comment: Safe backend-only ticket
```

## Acceptance criteria

- Tickets may be approved or rejected for execution.
- Approval history is persisted.
- READY_TO_TAKE lifecycle state exists.
- Only READY_CANDIDATE tickets can be approved.
- Rejected approvals move the ticket back to BLOCKED.
- API exposes approval history.
- Dashboard exposes approval actions and history.
- Scheduler and worker behavior remain unchanged.
- Existing tests continue to pass.

---

## Contexte de retry injecté par run_ticket.py

## Output précédent

I have enough context to produce the plan.

## Objective

Introduce a human approval workflow that gates the new `ready_to_take` lifecycle state. After Ticket Readiness Evaluation flags a ticket `ready_candidate`, a human can approve execution (→ `ready_to_take`) or reject it (→ `blocked` with a visible reason). All approvals are persisted in a new `ticket_approvals` table; the API, dashboard, and board surface the approval history and the new state. Scheduler/worker behaviour is **not** changed.

## Included

### 1. Database layer — `ticket_approvals` table

- `tools/agent_runner/runtime_db.py`
  - Extend `_SCHEMA` with a new `CREATE TABLE IF NOT EXISTS ticket_approvals` block. SQLite columns (stdlib types only):
    ```
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id        TEXT NOT NULL,
    approval_type    TEXT NOT NULL,     -- 'execution' | 'plan' | 'code'  (only 'execution' used here)
    approval_status  TEXT NOT NULL,     -- 'pending' | 'approved' | 'rejected'
    approved_by      TEXT,
    approval_comment TEXT,
    approved_at      TEXT,              -- NULL while 'pending'
    created_at       TEXT NOT NULL,
    updated_at       TEXT NOT NULL
    ```
    plus `CREATE INDEX IF NOT EXISTS ix_ticket_approvals_ticket ON ticket_approvals(ticket_id, approval_type, id);`
  - New functions (mirroring the existing `upsert_ticket_*` / `get_ticket_*` style):
    - `insert_ticket_approval(db_path, ticket_id, approval_type, approval_status, approved_by, approval_comment) -> int` (returns row id; sets `approved_at` to `_now_iso()` for `approved` / `rejected`).
    - `list_ticket_approvals(db_path, ticket_id) -> list[dict]` (ORDER BY id ASC — append-only history).
    - `get_latest_ticket_approval(db_path, ticket_id, approval_type) -> dict | None`.
  - Extend the `_RUNTIME_DB_BACKEND == "postgres"` rebind block to expose the same names from `runtime_db_pg`.
- `tools/agent_runner/runtime_db_pg.py`
  - Add a matching `ticket_approvals` table (with `project_id TEXT NOT NULL`, `id BIGSERIAL`, composite uniqueness scoped by `(project_id, id)`), and Postgres equivalents of `insert_ticket_approval`, `list_ticket_approvals`, `get_latest_ticket_approval`.
- Extend `ticket_readiness.readiness_status` accepted values to include `ready_to_take` (no schema change — `readiness_status` is a free-form TEXT; only the evaluator/service writes it).

### 2. Approval service — `tools/agent_runner/ticket_approval_service.py`

New stdlib-only module (no third-party deps), import-time symmetric with `ticket_readiness_evaluator.py`:

- `request_execution_approval(db_path, ticket_id) -> dict`
  Creates a `pending` row for `approval_type='execution'`. Idempotent: if the latest execution approval is already `pending`, returns it unchanged.
- `approve_execution(db_path, ticket_id, approved_by, comment=None) -> dict`
  Preconditions: `ticket_readiness.readiness_status == 'ready_candidate'`; raises `ValueError` otherwise.
  Inserts an `approved` row, then calls `runtime_db.upsert_ticket_readiness(..., readiness_status='ready_to_take', evaluated_at=_now_iso())`.
- `reject_execution(db_path, ticket_id, approved_by, comment=None) -> dict`
  Preconditions: same as `approve_execution`.
  Inserts a `rejected` row, then sets `readiness_status='blocked'` and appends `"Execution approval rejected by <approved_by>"` to `blocking_reasons_json` (keeps any existing reasons; deduplicated).
- `get_ticket_approvals(db_path, ticket_id) -> list[dict]` — returns full append-only history.
- `compute_execution_eligibility(db_path, ticket_id) -> str` — pure read helper returning one of `not_started | ready_candidate | ready_to_take | blocked | …` by combining the latest execution approval with the current readiness row. Used by both the API and by the readiness evaluator on re-run to preserve `ready_to_take` instead of demoting it back to `ready_candidate`.
- Hook `compute_execution_eligibility` into `ticket_readiness_evaluator.run_evaluation`: after computing base candidacy, if base says `ready_candidate` and the latest execution approval is `approved`, persist `ready_to_take` instead.

### 3. API — `services/control_api/routes/approvals.py`

New router, mirroring `routes/readiness.py` structure (both `/tickets/...` and `/projects/{project_id}/tickets/...` mounts):

- `GET  /tickets/{ticket_id}/approvals` → `TicketApprovalHistory` (list of `TicketApproval` items).
- `POST /tickets/{ticket_id}/approve-execution` (body: `ApprovalDecision { approved_by: str, comment: str | None }`) → `TicketApproval`. Returns 409 if current `readiness_status != 'ready_candidate'`, 404 if ticket unknown.
- `POST /tickets/{ticket_id}/reject-execution` (same body) → `TicketApproval`, same error semantics.

Models added to `services/control_api/models/schemas.py`:
- `TicketApproval`, `TicketApprovalHistory`, `ApprovalDecision`.

Wiring in `services/control_api/main.py`:
- `from .routes import approvals` and `app.include_router(approvals.router); app.include_router(approvals.project_router)`.

### 4. Frontend dashboard

- `apps/dashboard/src/api/tickets.js`
  Add: `getTicketApprovals`, `approveExecution(id, projectId, payload)`, `rejectExecution(id, projectId, payload)`.
- `apps/dashboard/src/components/HumanApprovalPanel.jsx` (new)
  - Subscribes to readiness + approvals (small poll, same hook pattern as `TicketReadinessPanel`).
  - Shows: current effective status badge (`READY CANDIDATE` / `READY TO TAKE` / `BLOCKED`), latest approver/date/comment, append-only history list.
  - Two buttons: **Approve for execution** and **Reject execution**, with a textarea for the comment.
  - Buttons are enabled **only** when `readiness_status === 'ready_candidate'`; otherwise disabled with a tooltip.
- `apps/dashboard/src/pages/TicketDetailPage.jsx`
  - Render `<HumanApprovalPanel ticketId={id} projectId={projectId} />` directly under `<TicketReadinessPanel />`.
- `apps/dashboard/src/pages/BoardPage.jsx`
  - Show `READY CANDIDATE`, `READY TO TAKE`, `BLOCKED` badges on `BoardCard` based on the ticket's `readiness_status` (fetched alongside board items — extend the existing board response or fetch readiness per ticket; see Excluded).
  - Add a top-of-page filter `<select>` (`all | ready_candidate | ready_to_take | blocked`) that filters cards client-side.

### 5. Tests

- `tests/test_ticket_approval_db.py` — schema creation, insert/list/latest helpers, append-only ordering.
- `tests/test_ticket_approval_service.py`
  - `approve_execution` when `ready_candidate` → state becomes `ready_to_take`, row inserted.
  - `reject_execution` when `ready_candidate` → state becomes `blocked`, reason appended.
  - Either action raises `ValueError` when the current state is anything else (including `ready_to_take` already, `blocked`, `not_started`).
  - Re-running `ticket_readiness_evaluator.run_evaluation` after an `approved` execution approval preserves `ready_to_take` (does not demote to `ready_candidate`).
- `tests/test_ticket_approval_api.py` — FastAPI client tests for the three endpoints (404, 409, happy paths, history shape).
- Existing tests under `tests/test_ticket_readiness_*.py`, `tests/test_human_approval.py`, `tests/test_control_api_endpoints.py` continue to pass unchanged.

## Excluded

- No change to `run_daemon.py`, the supervisor, the scheduler, worker dispatch, or any execution gating. `ready_to_take` is purely informational for this ticket.
- No change to the legacy `apply_human_approval` / `runs/<ticket>/state.json` plan/implementation approvals (`tests/test_human_approval.py` semantics are untouched).
- `approval_type='plan'` and `approval_type='code'` are reserved by the schema but not exposed via API or service helpers in this ticket.
- No bulk/auto approval, no email/Slack notification, no role/permission system — `approved_by` is a free-form string taken from the request body.
- No migration of existing `runs/<ticket>/plan-approved.md` markers into the new table.
- No board-server-side filter: filtering is client-side; we won't extend `board_service.py`'s SQL beyond, at most, joining the existing `ticket_readiness` row so `readiness_status` reaches the UI. If joining proves intrusive, the Board falls back to a per-card `GET /tickets/{id}/readiness` call (already public).
- No change to the project-map / parallel-safe logic.

## Acceptance criteria

- `ticket_approvals` table exists on both SQLite and Postgres backends after API startup; `init_runtime_db` is idempotent.
- `POST /tickets/{id}/approve-execution` on a `ready_candidate` ticket:
  - returns 200 with a `TicketApproval` whose `approval_status='approved'`;
  - `GET /tickets/{id}/readiness` then reports `readiness_status='ready_to_take'`;
  - `GET /tickets/{id}/approvals` includes the new row.
- `POST /tickets/{id}/reject-execution` on a `ready_candidate` ticket:
  - returns 200 with `approval_status='rejected'`;
  - `GET /tickets/{id}/readiness` then reports `readiness_status='blocked'` with `"Execution approval rejected by <approver>"` in `blocking_reasons`.
- Both endpoints return **409 Conflict** when the current `readiness_status` is not `ready_candidate`; return **404** for an unknown ticket id.
- Approval history is append-only: no row is ever updated in place; repeated approve/reject calls add new rows visible via `GET /tickets/{id}/approvals`.
- Re-running `POST /tickets/{id}/evaluate-readiness` on an already-approved ticket leaves `readiness_status='ready_to_take'` (does not demote).
- The Ticket Detail page renders the Human Approval section, with buttons enabled only when `readiness_status === 'ready_candidate'`, and lists prior approvals (approver, date, comment).
- The Board page renders `READY CANDIDATE`, `READY TO TAKE`, and `BLOCKED` badges and supports client-side filtering on these states.
- `pytest` for the existing suite (in particular `tests/test_ticket_readiness_*.py`, `tests/test_human_approval.py`, `tests/test_control_api_endpoints.py`) still passes; the new `tests/test_ticket_approval_*.py` files pass.
- Scheduler/daemon/worker behaviour is unchanged: no new code path in `run_daemon.py`, `services/supervisor/`, or `tools/agent_runner/run_ticket.py` consults `ready_to_take` to start, queue, or block execution.

---

## Review

# Plan review — T199 approval idempotency

The T199 plan is broadly aligned with the issue goal: it introduces human execution approval, the `ready_to_take` lifecycle state, an approval API, an approval UI, and an append-only approval history while leaving scheduler and worker behavior unchanged.

However, one blocking issue must be fixed before implementation starts.

## Blocking issue — approve/reject endpoints are not idempotent

The issue explicitly requires:

```text
- approving twice is idempotent
- revoking twice is idempotent
```

The current plan says:

```text
approve_execution(...)
Preconditions: ticket_readiness.readiness_status == 'ready_candidate'
```

and also plans tests where approving when the state is already `ready_to_take` raises `ValueError`.

That means this sequence would fail:

```text
POST /tickets/T199/approve-execution
→ readiness_status = ready_to_take

POST /tickets/T199/approve-execution again
→ 409 / ValueError
```

This is not idempotent.

The same issue exists for rejection:

```text
POST /tickets/T199/reject-execution
→ readiness_status = blocked

POST /tickets/T199/reject-execution again
→ 409 / ValueError
```

This is risky because users can double-click buttons, retry requests, refresh pages, or clients can retry network calls.

## Required behavior

`approve_execution(...)` must be idempotent:

- If the latest execution approval is already `approved`, return the existing latest approval and do not insert a duplicate row.
- If readiness is already `ready_to_take`, return success with the existing approval state.
- Do not raise an error for repeated approval.

`reject_execution(...)` must be idempotent:

- If the latest execution approval is already `rejected`, return the existing latest rejection and do not insert a duplicate row.
- If readiness is already `blocked` because of the same execution rejection, return success with the existing rejection state.
- Do not raise an error for repeated rejection.

## Conflict behavior

Conflicts should only occur when the requested action contradicts the current latest decision.

Examples:

```text
latest approval = approved
POST reject-execution
→ 409 Conflict, unless a future explicit revoke/reopen workflow exists
```

```text
latest approval = rejected
POST approve-execution
→ 409 Conflict, unless a future explicit reapproval workflow exists
```

For this ticket, do not implement reapproval or revocation unless explicitly planned. Keep the workflow simple and safe.

## History behavior

The plan currently says approval history is append-only, which is good. But idempotent duplicate requests should not create duplicate rows.

Append-only means each real state transition creates a row; retries of the same already-applied decision should not.

## Required correction

Update `runs/T199/plan.md` so that:

1. Repeated approve is idempotent and returns the existing approved decision.
2. Repeated reject is idempotent and returns the existing rejected decision.
3. Duplicate requests do not append duplicate history rows.
4. Tests cover repeated approve and repeated reject.
5. 409 is reserved for contradictory state transitions, not same-action retries.

## Review verdict

PLAN_FIX_REQUIRED until approval and rejection idempotency are correctly specified.

---

## Instructions de fix

# Plan fix — make execution approval and rejection idempotent

## Required plan update

Update `runs/T199/plan.md` before starting implementation.

The current plan is directionally correct, but it conflicts with the issue acceptance criteria because approval and rejection are not idempotent.

## 1. Approve execution must be idempotent

Change `approve_execution(db_path, ticket_id, approved_by, comment=None)` behavior to:

```text
1. Load current readiness row.
2. Load latest execution approval.
3. If latest execution approval is already approved:
   - return the existing approval row
   - do not insert a new row
   - do not change readiness
   - do not raise
4. Else if readiness_status == ready_candidate:
   - insert approved row
   - set readiness_status = ready_to_take
   - return the new approval row
5. Else:
   - raise ValueError / return 409
```

Repeated approval must therefore succeed.

Example:

```text
POST /tickets/T199/approve-execution
→ 200 approved

POST /tickets/T199/approve-execution again
→ 200 approved, same latest approval, no duplicate history row
```

## 2. Reject execution must be idempotent

Change `reject_execution(db_path, ticket_id, approved_by, comment=None)` behavior to:

```text
1. Load current readiness row.
2. Load latest execution approval.
3. If latest execution approval is already rejected:
   - return the existing rejection row
   - do not insert a new row
   - do not append duplicate blocking reasons
   - do not raise
4. Else if readiness_status == ready_candidate:
   - insert rejected row
   - set readiness_status = blocked
   - append reason "Execution approval rejected by <approved_by>"
   - return the new rejection row
5. Else:
   - raise ValueError / return 409
```

Repeated rejection must therefore succeed.

Example:

```text
POST /tickets/T199/reject-execution
→ 200 rejected

POST /tickets/T199/reject-execution again
→ 200 rejected, same latest rejection, no duplicate history row
```

## 3. Contradictory transitions return conflict

The API should return `409 Conflict` only when the requested action contradicts the latest decision.

Examples:

```text
latest execution approval = approved
POST /tickets/T199/reject-execution
→ 409 Conflict
```

```text
latest execution approval = rejected
POST /tickets/T199/approve-execution
→ 409 Conflict
```

Do not implement reapproval, revoke, or reopen in this ticket unless the plan explicitly adds a separate workflow.

## 4. History semantics

Approval history remains append-only for real state transitions.

However, idempotent retries do not represent a new state transition and must not create extra rows.

Correct behavior:

```text
approve once
approve retry
GET approvals
→ one approved row
```

```text
reject once
reject retry
GET approvals
→ one rejected row
```

## 5. Test updates

Update the planned tests:

- Remove the expectation that approving when already `ready_to_take` raises `ValueError` if latest execution approval is already `approved`.
- Remove the expectation that rejecting when already `blocked` raises `ValueError` if latest execution approval is already `rejected`.
- Add tests:

```text
approve_execution is idempotent
reject_execution is idempotent
repeated approve does not duplicate history
repeated reject does not duplicate history
approve after rejected returns conflict
reject after approved returns conflict
```

## 6. API acceptance criteria additions

Add or update acceptance criteria:

- Repeated `POST /tickets/{id}/approve-execution` returns 200 and does not duplicate history when the latest execution approval is already approved.
- Repeated `POST /tickets/{id}/reject-execution` returns 200 and does not duplicate history when the latest execution approval is already rejected.
- Contradictory transitions return 409 Conflict.
- Approval history is append-only for real state transitions, not for duplicate retries.

## Non-goals reminder

This fix must still not change:

- scheduler behavior
- worker dispatch
- daemon state machine
- execution queue ordering
- automatic execution start