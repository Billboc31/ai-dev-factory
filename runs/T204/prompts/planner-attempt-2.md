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

## Artifact-only output (strict)

Your response will be written verbatim to `runs/<ticket>/plan.md`.
Rewrite the artifact itself. Do not describe the modifications.
Do not explain what changed. Do not produce a status report.

This rule applies to both initial plans and rewrites after a review.
Examples of forbidden openings: "The plan has been rewritten…",
"This plan now covers…", "Plan rewritten as a real implementation
document…", "Key points covered…", "The document now contains…".

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



# T204 — T204 - Add Ticket Operations panel for guarded manual recovery actions

**Source**: GitHub Issue #264

## Description

# T204 - Add Ticket Operations panel for guarded manual recovery actions

## Context

AI Dev Factory now has diagnostic capabilities for stuck tickets.

T203 explains why a ticket is stuck and recommends safe recovery actions, but it does not execute those actions.

The next step is to add a dedicated Ticket Operations panel where a human operator can trigger selected manual recovery actions with explicit safeguards.

This is an operator console for recovery, not an automation engine.

## Goal

Add a Ticket Operations panel to the ticket detail page that exposes guarded manual actions for recovering or managing a ticket.

The panel should use diagnostics as input when available and display only relevant actions.

Initial supported actions should be conservative and explicit.

## Non-goals

Do not:

- add automatic recovery
- dispatch new tickets
- change scheduler behavior
- change worker reservation behavior
- introduce parallel execution logic
- auto-delete anything without confirmation
- bypass human approval rules
- merge PRs automatically
- silently reset ticket state

## New concept

Create a service:

```text
tools/agent_runner/ticket_operations.py
```

It should expose guarded operations for a ticket.

Each operation must:

1. validate preconditions
2. return a structured result
3. write an audit log entry if an audit mechanism exists
4. avoid destructive changes unless explicitly confirmed
5. never run automatically

## Operation safety levels

Every operation must have a safety level:

```text
low
medium
high
destructive
```

Rules:

- `low` actions can run after a normal click confirmation.
- `medium` actions require a confirmation modal.
- `high` actions require typing the ticket id.
- `destructive` actions require typing the ticket id and a second explicit confirmation.

## Initial operations

### Re-run advisory analyzers

These actions are safe and should call the existing API/service flows:

```text
rerun_intelligence
rerun_readiness
rerun_rules
rerun_diagnostics
```

They should not mutate ticket execution state.

### Approval actions

Expose existing human approval actions:

```text
approve_execution
reject_execution
```

They must use the existing Human Approval Workflow and must not duplicate approval logic.

### Mark ticket blocked

Action:

```text
mark_blocked
```

Purpose:

Allow a human to mark a ticket as blocked with a reason.

Requirements:

- requires reason text
- appends or persists the blocking reason
- does not delete worktree
- does not cancel runs unless a separate action is explicitly triggered

### Reset ticket to planning

Action:

```text
reset_to_planning
```

Purpose:

Recover from a bad/stale/invalid plan.

Requirements:

- high safety level
- requires typed ticket id
- must preserve previous artifacts in an archive/history folder if possible
- must record why the reset happened
- must not delete the worktree by default
- must not run the planner automatically

### Reset ticket to coding

Action:

```text
reset_to_coding
```

Purpose:

Recover when implementation needs to be regenerated but the plan is still valid.

Requirements:

- high safety level
- requires typed ticket id
- must preserve previous code/review/test artifacts where possible
- must not delete plan artifacts
- must not run the coder automatically

### Clear stuck transient state

Action:

```text
clear_stuck_state
```

Purpose:

Clear stale transient runtime markers when no active worker/daemon is actually running.

Requirements:

- medium or high safety level depending on existing state
- must verify no active process/worker heartbeat exists before clearing
- must not touch artifacts or worktree
- must record what was cleared

### Delete ticket worktree

Action:

```text
delete_worktree
```

Purpose:

Remove a broken ticket worktree after a ticket is cancelled, reset, archived, or confirmed stuck.

Requirements:

- destructive safety level
- requires typed ticket id
- requires explicit confirmation
- refuses to run if a worker is active or if the worktree has uncommitted changes unless force is explicitly confirmed
- must never delete outside the configured worktrees root
- must record deleted path

### Archive ticket

Action:

```text
archive_ticket
```

Purpose:

Move a ticket out of the active workflow without deleting data.

Requirements:

- medium safety level
- requires reason text
- must preserve all artifacts
- should mark the ticket as archived/cancelled using existing board conventions if available

## API

Add Control API endpoints:

```text
GET /tickets/{ticket_id}/operations
POST /tickets/{ticket_id}/operations/{operation_key}
```

Project-scoped variants:

```text
GET /projects/{project_id}/tickets/{ticket_id}/operations
POST /projects/{project_id}/tickets/{ticket_id}/operations/{operation_key}
```

`GET` returns available operations for the current ticket:

```json
{
  "ticket_id": "T204",
  "operations": [
    {
      "operation_key": "rerun_diagnostics",
      "label": "Re-run diagnostics",
      "safety_level": "low",
      "enabled": true,
      "disabled_reason": null,
      "requires_reason": false,
      "requires_typed_ticket_id": false,
      "requires_double_confirmation": false
    }
  ]
}
```

`POST` executes one operation after validating confirmation payload.

Suggested request:

```json
{
  "reason": "Plan is stale after main changed",
  "typed_ticket_id": "T204",
  "confirm": true,
  "force": false
}
```

Suggested response:

```json
{
  "ticket_id": "T204",
  "operation_key": "reset_to_planning",
  "status": "completed",
  "message": "Ticket reset to planning and previous artifacts archived.",
  "details": {}
}
```

## Database / audit

Prefer using an existing audit log if available.

If no generic audit mechanism exists, add a lightweight table:

```text
ticket_operation_audit
```

Suggested fields:

```text
id
ticket_id
project_id
operation_key
status
reason
requested_by
details_json
created_at
```

Every operation attempt should be recorded, including rejected attempts.

## Frontend

Add a panel:

```text
Ticket Operations
```

Location:

```text
apps/dashboard/src/pages/TicketDetailPage.jsx
```

Suggested component:

```text
apps/dashboard/src/components/TicketOperationsPanel.jsx
```

Display:

- operation groups:
  - Advisory re-runs
  - Approval actions
  - Recovery actions
  - Dangerous actions
- enabled/disabled state
- disabled reason
- safety level badge
- confirmation modal
- reason input when required
- typed ticket id confirmation when required
- operation result message

If T203 diagnostics are available, display a small hint:

```text
Recommended by diagnostics
```

next to actions matching `recommended_actions`.

## Safety requirements

The operations service must be defensive.

It must:

- never delete outside the configured project/worktree roots
- verify paths with resolved absolute paths before deleting
- refuse destructive actions while a worker heartbeat is active
- require explicit confirmation payload for high/destructive actions
- record every attempted operation
- return clear errors instead of partially mutating state

## Tests

Add tests for:

- available operations API
- confirmation validation
- safety-level requirements
- rerun diagnostics operation
- approval operations delegate to existing approval service
- reset to planning preserves previous artifacts or records why it cannot
- clear stuck state refuses when active heartbeat exists
- delete worktree refuses outside worktrees root
- delete worktree refuses dirty worktree unless force confirmed
- archive ticket preserves artifacts
- audit log records successful and rejected operations
- UI renders operations grouped by safety level
- UI requires typed ticket id for high/destructive actions

## Acceptance criteria

- Ticket detail page displays a Ticket Operations panel.
- Available operations are returned by API with safety metadata.
- Low-risk advisory re-run operations can be triggered manually.
- Approval actions reuse the existing approval workflow.
- Recovery actions validate preconditions and confirmation requirements.
- Destructive actions are guarded by typed ticket id and explicit confirmation.
- Every operation attempt is audited.
- No operation runs automatically.
- Scheduler, dispatcher, worker allocation, and parallel execution remain unchanged.
- Existing tests continue to pass.

---

## Contexte de retry injecté par run_ticket.py

## Artifact-only instruction (mandatory)

Your response will be written verbatim to `runs/T204/plan.md`.
Rewrite the artifact itself. Do not describe the modifications.
Do not explain what changed. Do not produce a status report.
Openings such as "The plan has been rewritten…", "This plan now
covers…", "Plan rewritten as…", "Key points covered…", "The
document now…" make the output invalid.

---

## Output précédent

## Objective

Add a Ticket Operations panel exposing guarded manual recovery actions (advisory re-runs, approval delegation, recovery, archive, destructive deletion) backed by a new `ticket_operations.py` service, a paired Control API endpoint pair, an audit table, and a React panel on the ticket detail page. Every operation must be explicit, audited, safety-gated, and never auto-triggered.

## Included

### 1. Operations service — `tools/agent_runner/ticket_operations.py`

Create a new module that defines, validates, and executes ticket operations. Public API:

- `OPERATIONS: dict[str, OperationSpec]` — registry of operation specs.
- `OperationSpec` dataclass with fields: `key`, `label`, `group` (`advisory` | `approval` | `recovery` | `dangerous`), `safety_level` (`low` | `medium` | `high` | `destructive`), `requires_reason: bool`, `requires_typed_ticket_id: bool`, `requires_double_confirmation: bool`, `handler: Callable`.
- `list_operations(db_path, project_root, ticket_id, project_id=None) -> list[dict]` — returns each spec plus `enabled` and `disabled_reason`, computed from current ticket state, worker heartbeat, and worktree state.
- `execute_operation(db_path, project_root, ticket_id, operation_key, payload, requested_by, project_id=None) -> dict` — validates confirmation payload, runs the handler, audits the attempt, and returns `{status, message, details}`.
- `OperationError` exception carrying an HTTP-friendly status code and message; rejected attempts are still audited.

Implement these handlers (each preconditions-first, no partial mutation):

- **Advisory re-runs (`low`)**: `rerun_intelligence`, `rerun_readiness`, `rerun_rules`, `rerun_diagnostics` — call the existing `ticket_intelligence_analyzer`, `ticket_readiness_evaluator`, `execution_rules_engine`, and `ticket_diagnostics.diagnose_ticket` functions. Never touch ticket execution state.
- **Approval (`medium`)**: `approve_execution`, `reject_execution` — delegate verbatim to `ticket_approval_service.approve_execution` / `reject_execution`. No duplicated logic.
- **`mark_blocked` (`medium`)**: requires `reason`; persists the reason by calling `ticket_readiness_evaluator` blocked-write helpers (or, if absent, by inserting a blocking-reason row through `runtime_db`). Does not cancel runs or touch worktrees.
- **`reset_to_planning` (`high`)**: requires typed ticket id and `reason`. Archives the current `runs/<ticket>/` artifacts to `runs/<ticket>/archive/<timestamp>/` via `shutil.move` of the known artifact files (`plan.md`, `reviews/`, `tests/`, `conflict/`, `retry-state.json`). Writes `archive/<timestamp>/reset.json` with reason, requester, prior state. Updates `state.json` to PLANNING. Never invokes the planner. Never removes the worktree.
- **`reset_to_coding` (`high`)**: same archive pattern but preserves `plan.md`; archives `reviews/`, `tests/`, `conflict/`, `retry-state.json`. Updates `state.json` to CODING. Never invokes the coder.
- **`clear_stuck_state` (`medium` if no worker row, `high` if a stale row exists)**: checks `workers` table via `runtime_db` for an entry with this `ticket_id` and a fresh `heartbeat_at` (configurable threshold, default 120 s). Refuses if the heartbeat is fresh. Otherwise deletes the row and records the cleared values in the audit `details_json`. Never touches artifacts or the worktree.
- **`delete_worktree` (`destructive`)**: requires typed ticket id and `confirm=true`. Resolves worktrees root via `services.control_api.services.runtime_resolver.resolve_worktrees_dir`. Computes the target path and asserts (`Path.resolve().is_relative_to(worktrees_root_resolved)`) — otherwise raises. Refuses if a worker row exists with a fresh heartbeat. Runs `git -C <worktrees_root> worktree list --porcelain` to detect dirty/locked worktrees; refuses unless `force=true`. On success, runs `git worktree remove --force <path>` followed by directory removal as a fallback, and records `deleted_path` in audit details.
- **`archive_ticket` (`medium`)**: requires `reason`. Marks the ticket as archived/cancelled by writing to the existing readiness or board state (set `state.json` to a recognized terminal like `CANCELLED` if already supported, otherwise add a `archived: true` flag in `state.json`). Preserves all artifacts on disk. Records the reason in the audit.

### 2. Audit storage — extend `tools/agent_runner/runtime_db.py`

Add a new SQLite/Postgres table:

```sql
CREATE TABLE IF NOT EXISTS ticket_operation_audit (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id       TEXT NOT NULL,
    project_id      TEXT,
    operation_key   TEXT NOT NULL,
    status          TEXT NOT NULL,
    reason          TEXT,
    requested_by    TEXT,
    details_json    TEXT,
    created_at      TEXT NOT NULL
);
```

Add helpers in `runtime_db.py`:

- `append_ticket_operation_audit(db_path, ticket_id, project_id, operation_key, status, reason, requested_by, details)`.
- `list_ticket_operation_audit(db_path, ticket_id, limit=50)`.

Mirror the schema for the Postgres branch in `runtime_db_pg.py`. Schema creation must be idempotent and run inside the existing init path used by other tables.

Also append a `runtime_events` entry per operation attempt (`event_type=f"operation:{operation_key}"`) to keep existing audit timelines coherent.

### 3. Control API — new route module `services/control_api/routes/operations.py`

Register the module in `services/control_api/main.py` alongside the other route files. Implement both global and project-scoped variants:

- `GET /tickets/{ticket_id}/operations`
- `POST /tickets/{ticket_id}/operations/{operation_key}`
- `GET /projects/{project_id}/tickets/{ticket_id}/operations`
- `POST /projects/{project_id}/tickets/{ticket_id}/operations/{operation_key}`

Pydantic models in `services/control_api/models/schemas.py`:

- `OperationDescriptor` — fields from the ticket description (`operation_key`, `label`, `safety_level`, `group`, `enabled`, `disabled_reason`, `requires_reason`, `requires_typed_ticket_id`, `requires_double_confirmation`).
- `OperationListResponse` — `ticket_id`, `operations: list[OperationDescriptor]`.
- `OperationRequest` — `reason: str | None`, `typed_ticket_id: str | None`, `confirm: bool = False`, `force: bool = False`.
- `OperationResult` — `ticket_id`, `operation_key`, `status` (`completed` | `rejected` | `error`), `message`, `details: dict`.

Behaviour:

- The `GET` handler calls `ticket_operations.list_operations` and returns `OperationListResponse`.
- The `POST` handler validates `operation_key` against `OPERATIONS`, validates the request payload against the spec (typed id matches, reason present, double confirmation, etc.), calls `execute_operation`, and returns `OperationResult`. Validation failures return HTTP 400 and are still audited as `status="rejected"`. Unknown operation keys return HTTP 404. Server errors return HTTP 500 with audit `status="error"`.
- `requested_by` is sourced from existing auth headers if the project already exposes one; otherwise default to `"operator"`.

### 4. Frontend — `apps/dashboard/src/components/TicketOperationsPanel.jsx`

Create a new panel component following the conventions in `HumanApprovalPanel.jsx` and `TicketDiagnosticsPanel.jsx`:

- Polls `GET .../operations` via the existing axios client and `usePolling`.
- Renders four sections: **Advisory re-runs**, **Approval actions**, **Recovery actions**, **Dangerous actions**, sourced from `group`.
- Each operation row: label, safety-level badge (color-coded by level), enabled state, `disabled_reason` tooltip, and a trigger button.
- Confirmation modal:
  - `low` — click confirm only.
  - `medium` — modal with optional reason field (required if `requires_reason`).
  - `high` — modal with reason field plus a typed-ticket-id input that must equal the ticket id.
  - `destructive` — modal with typed ticket id, an explicit second confirmation checkbox, and a `force` toggle when applicable.
- After action submission, surface the `OperationResult.message` inline (success or rejection).
- If T203 diagnostics are present in props or fetched alongside, display a `Recommended by diagnostics` chip next to operations whose `operation_key` matches `recommended_actions`.

Wire the panel in `apps/dashboard/src/pages/TicketDetailPage.jsx` next to the existing panels and pass the ticket id / project id.

Add API client functions in `apps/dashboard/src/api/tickets.js`:

- `listTicketOperations(ticketId, projectId)`.
- `executeTicketOperation(ticketId, projectId, operationKey, payload)`.

### 5. Tests

Backend (`tests/`, pytest), one file per service: `tests/test_ticket_operations.py` and `tests/test_control_api_operations.py`.

- `list_operations` returns expected entries with correct `enabled`/`disabled_reason` for representative ticket states.
- Confirmation payload validation:
  - missing `reason` rejects when required.
  - mismatched `typed_ticket_id` rejects.
  - missing `confirm` rejects destructive operations.
- `rerun_diagnostics` calls `ticket_diagnostics.diagnose_ticket` and persists nothing else (verify via patched function).
- `approve_execution` and `reject_execution` delegate to `ticket_approval_service` (verify via patch / inserted approval row).
- `reset_to_planning` moves `plan.md` and related artifacts under `runs/<ticket>/archive/<ts>/`, records a `reset.json`, and sets `state.json` state to `PLANNING`. A separate test asserts a clear error when the run directory cannot be archived.
- `clear_stuck_state` refuses when a fresh heartbeat exists and clears when stale.
- `delete_worktree` refuses paths outside the worktrees root (path traversal guard), refuses dirty worktree without `force`, and succeeds with `force=true` on a constructed fixture worktree.
- `archive_ticket` preserves artifacts on disk.
- Audit log records both successful and rejected attempts (assert one row per call in `ticket_operation_audit`).

Frontend (`apps/dashboard/tests/TicketOperationsPanel.test.jsx`):

- Renders all four operation groups when API returns operations from each group.
- Disabled operations show their `disabled_reason`.
- High/destructive operations gate submission on typed ticket id matching.
- Calling an operation shows the API result message.
- Diagnostics hint appears for operations listed in `recommended_actions`.

## Excluded

- Any automatic, scheduled, or worker-driven triggering of operations.
- New dispatcher, scheduler, parallel-execution, or reservation logic.
- New automatic PR merging, auto-approval, or bypassing the human approval workflow.
- Re-implementing approval, readiness, intelligence, rules, or diagnostics logic (only delegate).
- Adding new artifact types or rearranging existing run-directory layout beyond the `archive/<timestamp>/` subfolder.
- Authentication / authorization changes; `requested_by` is best-effort from existing context.
- Bulk or multi-ticket operations.
- Real-time websocket updates (the panel polls).
- Migration tooling for existing deployments beyond the idempotent `CREATE TABLE IF NOT EXISTS` at startup.

## Acceptance criteria

- `tools/agent_runner/ticket_operations.py` exists with the documented `OperationSpec` registry, `list_operations`, and `execute_operation`, covering all ten operation keys (`rerun_intelligence`, `rerun_readiness`, `rerun_rules`, `rerun_diagnostics`, `approve_execution`, `reject_execution`, `mark_blocked`, `reset_to_planning`, `reset_to_coding`, `clear_stuck_state`, `delete_worktree`, `archive_ticket`).
- `runtime_db.py` (SQLite) and `runtime_db_pg.py` (Postgres) both create `ticket_operation_audit` idempotently and expose `append_ticket_operation_audit` / `list_ticket_operation_audit`.
- `GET /tickets/{ticket_id}/operations` and `GET /projects/{project_id}/tickets/{ticket_id}/operations` return the documented JSON shape with safety metadata for every registered operation.
- `POST /tickets/{ticket_id}/operations/{operation_key}` (and its project-scoped twin) validates the confirmation payload before executing; invalid payloads return HTTP 4xx and are still recorded in `ticket_operation_audit` with `status="rejected"`.
- Approval operations route through `ticket_approval_service.approve_execution` / `reject_execution` and do not duplicate readiness logic.
- `reset_to_planning` and `reset_to_coding` move prior artifacts into `runs/<ticket_id>/archive/<timestamp>/` and write a metadata file describing the reset; neither operation invokes the planner or the coder.
- `clear_stuck_state` refuses to execute when a worker heartbeat is fresh and clears stale rows otherwise.
- `delete_worktree` refuses any target path not strictly under the resolved worktrees root, refuses dirty worktrees unless `force=true`, and refuses when a worker heartbeat is fresh.
- `archive_ticket` does not delete any artifact on disk.
- Every operation attempt — accepted, rejected, or errored — appears as a row in `ticket_operation_audit` and as a `runtime_events` entry with type `operation:<key>`.
- `TicketOperationsPanel.jsx` is mounted on the ticket detail page, displays the four operation groups with safety-level badges, enforces typed-ticket-id input for `high`/`destructive` actions, surfaces the API result message, and shows the diagnostics hint for operations matching `recommended_actions`.
- All new backend tests in `tests/test_ticket_operations.py` and `tests/test_control_api_operations.py` pass; the new frontend test `TicketOperationsPanel.test.jsx` passes; the existing test suite continues to pass.
- No change is made to the scheduler, dispatcher, worker allocation, worker reservation, or any code path that runs without an explicit operator click.

---

## Review

# Plan review — T204 runner states and operation count

The T204 plan is aligned with the product direction: it adds a manual Ticket Operations panel with explicit confirmation, audit logging, recovery actions, dangerous-action safeguards, and no automatic scheduler or worker-triggered behavior.

However, the plan must be fixed before implementation starts.

## Blocking issue 1 — invalid runner states

The plan currently says:

```text
reset_to_planning -> updates state.json to PLANNING
reset_to_coding -> updates state.json to CODING
archive_ticket -> set state.json to CANCELLED if supported
```

These states are not part of the current runner state machine.

The current valid runner states are:

```text
INIT
PLAN_REVIEW_NEEDED
PLAN_FIX_REQUIRED
PLAN_APPROVED
IMPLEMENTATION_REVIEW_NEEDED
IMPLEMENTATION_FIX_REQUIRED
IMPLEMENTATION_APPROVED
TEST_COMPLETE
CONFLICT_RESOLUTION_NEEDED
CONFLICT_RESOLVING
CONFLICT_RESOLVED_REVIEW_NEEDED
CONFLICT_RESOLUTION_FAILED
```

T204 must not invent new runner states unless the ticket explicitly updates the state machine, transitions, UI, and tests. This ticket should not do that.

Required correction:

- `reset_to_planning` must reset to an existing planning-compatible state.
- `reset_to_coding` must reset to an existing coding-compatible state.
- `archive_ticket` must not introduce `CANCELLED` as a runner state.

Recommended mapping for T204:

```text
reset_to_planning -> PLAN_FIX_REQUIRED
reset_to_coding -> IMPLEMENTATION_FIX_REQUIRED
archive_ticket -> archived flag in state.json, not a new runner state
```

Alternative acceptable mapping:

```text
reset_to_planning -> INIT
reset_to_coding -> PLAN_APPROVED
```

But the plan must choose one explicit mapping and justify it.

## Blocking issue 2 — inconsistent operation count

The plan says:

```text
covering all ten operation keys
```

but the registry actually lists 12 operations:

```text
rerun_intelligence
rerun_readiness
rerun_rules
rerun_diagnostics
approve_execution
reject_execution
mark_blocked
reset_to_planning
reset_to_coding
clear_stuck_state
delete_worktree
archive_ticket
```

The acceptance criteria must say 12 operation keys, not 10.

## Blocking issue 3 — archive_ticket behavior is ambiguous

The plan says:

```text
set state.json to a recognized terminal like CANCELLED if already supported, otherwise add archived: true
```

This is too ambiguous and risks creating inconsistent behavior.

T204 must choose one behavior.

Recommended behavior:

```json
{
  "archived": true,
  "archived_reason": "...",
  "archived_by": "...",
  "archived_at": "..."
}
```

Do not change the runner state to `CANCELLED` in T204.

The ticket should preserve all artifacts and prevent accidental execution only by UI/API operation availability, not by inventing a new runner state.

## Required correction

Update `runs/T204/plan.md` so that:

1. No unsupported runner states are written.
2. `reset_to_planning` and `reset_to_coding` map to explicitly chosen valid states.
3. `archive_ticket` uses explicit archive metadata and does not use `CANCELLED`.
4. The operation count is corrected from 10 to 12.
5. Tests assert that no invalid state value is written.
6. Scheduler, dispatcher, worker allocation, worker reservation, and automatic execution paths remain untouched.

## Review verdict

PLAN_FIX_REQUIRED until runner state mappings, archive behavior, and operation count are corrected.

---

## Instructions de fix

# Plan fix — use valid runner states and explicit archive metadata

## Required plan update

Update `runs/T204/plan.md` before starting implementation.

The plan is directionally correct, but it must be corrected in three areas:

1. Do not write unsupported runner states.
2. Correct the operation count from 10 to 12.
3. Make `archive_ticket` behavior explicit and non-ambiguous.

## 1. Valid runner states only

T204 must not introduce new runner states.

Do not write these values to `state.json`:

```text
PLANNING
CODING
CANCELLED
```

They are not currently valid runner states.

Use only existing runner states.

Recommended mappings for this ticket:

```text
reset_to_planning -> PLAN_FIX_REQUIRED
reset_to_coding -> IMPLEMENTATION_FIX_REQUIRED
```

Rationale:

- `PLAN_FIX_REQUIRED` safely sends the ticket back to the planner path without pretending no prior plan existed.
- `IMPLEMENTATION_FIX_REQUIRED` safely sends the ticket back to the coder path while preserving the approved/current plan context.
- Both are existing states already understood by the runner.

If the implementer chooses the alternative mapping below, it must be explicitly justified in the final implementation notes:

```text
reset_to_planning -> INIT
reset_to_coding -> PLAN_APPROVED
```

In all cases, the implementation must use one explicit mapping and tests must assert the exact state written.

## 2. Archive current artifacts before reset

Before changing state, reset operations must archive affected artifacts into:

```text
runs/<ticket_id>/archive/<timestamp>/
```

`reset_to_planning` should archive plan/review/test/conflict/retry artifacts according to the corrected plan.

`reset_to_coding` should preserve `plan.md` and archive implementation/review/test/conflict/retry artifacts according to the corrected plan.

Each reset archive must include metadata:

```json
{
  "operation": "reset_to_planning",
  "ticket_id": "T204",
  "requested_by": "operator",
  "reason": "...",
  "previous_state": "...",
  "new_state": "PLAN_FIX_REQUIRED",
  "created_at": "..."
}
```

or:

```json
{
  "operation": "reset_to_coding",
  "ticket_id": "T204",
  "requested_by": "operator",
  "reason": "...",
  "previous_state": "...",
  "new_state": "IMPLEMENTATION_FIX_REQUIRED",
  "created_at": "..."
}
```

## 3. Explicit archive_ticket behavior

`archive_ticket` must not use or create a `CANCELLED` runner state.

Use archive metadata instead.

Required `state.json` fields:

```json
{
  "archived": true,
  "archived_reason": "...",
  "archived_by": "...",
  "archived_at": "..."
}
```

Do not delete artifacts.

Do not remove the worktree.

Do not invoke planner/coder/reviewer/tester.

Do not change scheduler or worker behavior.

## 4. Correct operation count

The plan currently says `ten operation keys`, but the registry contains 12 operations.

Correct the acceptance criteria to say:

```text
all 12 operation keys
```

The 12 keys are:

```text
rerun_intelligence
rerun_readiness
rerun_rules
rerun_diagnostics
approve_execution
reject_execution
mark_blocked
reset_to_planning
reset_to_coding
clear_stuck_state
delete_worktree
archive_ticket
```

## 5. Tests to add/update

Add or update tests so that:

- `reset_to_planning` writes only the chosen valid state.
- `reset_to_coding` writes only the chosen valid state.
- no test expects `PLANNING`, `CODING`, or `CANCELLED`.
- `archive_ticket` writes archive metadata, not a new runner state.
- the operation registry contains exactly the 12 expected keys.
- every operation attempt is audited, including rejected attempts.

## 6. Non-goals reminder

This fix must not introduce:

- new runner states
- scheduler changes
- dispatcher changes
- worker allocation changes
- worker reservation changes
- auto-triggered operations
- automatic PR merging
- bulk ticket operations

T204 remains a guarded manual operations panel only.