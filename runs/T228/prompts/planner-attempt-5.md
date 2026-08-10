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
document…", "Key points covered…", "The document now contains…",
"Plan written to `runs/…/plan.md`…", "`runs/…/plan.md` is written…".

Do not use the Write tool on `plan.md` and then print a status summary —
your stdout IS the artifact. If you do write the file, stdout must still
be the full plan (same four headings), not a report about it.

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



# T228 — Add autonomous “Unblock this ticket” recovery action to AI Workspace

**Source**: GitHub Issue #312

## Description

## Objective

Add an AI Workspace action that lets the user ask Claude to autonomously diagnose and recover a blocked AI Dev Factory ticket.

Example request:

> Unblock this ticket.

Claude should investigate why the active ticket is blocked, perform the authorized recovery work, restart the relevant pipeline step, and verify that the ticket is progressing again. If the blocker exposes an AI Dev Factory product bug, the action must create a documented GitHub issue.

## User story

As a remote AI Dev Factory user, I want to ask the integrated Workspace chat to unblock the current ticket so that Claude can inspect the pipeline, artifacts, logs, branches, and execution state without requiring me to diagnose each failure manually.

## Structured action

The Workspace should translate the request into a constrained Supervisor action similar to:

```json
{
  "action": "recover_ticket",
  "project_id": "ai-dev-factory",
  "ticket_id": "T226",
  "diagnose": true,
  "apply_safe_fixes": true,
  "retry_failed_stage": true,
  "create_bug_issue_when_detected": true
}
```

The active project and ticket must be resolved from the Workspace context when the user says “this ticket”.

## Recovery workflow

1. Collect the current ticket state.
2. Inspect the failed or blocked pipeline stage.
3. Read relevant logs and existing ticket artifacts.
4. Inspect repository and branch state when relevant.
5. Classify the blocker.
6. Produce a concise recovery plan.
7. Request confirmation before applying mutating recovery actions.
8. Apply only allowlisted and ticket-scoped fixes.
9. Retry the appropriate failed/blocked stage.
10. Verify that the ticket reaches the expected next state.
11. Return a recovery report to the chat.
12. When a reproducible AI Dev Factory bug is identified, create or link a GitHub issue containing the evidence.

## Blocker classification

The recovery agent must distinguish at least:

- missing or malformed ticket artifact;
- stale readiness or rule evaluation;
- missing human approval;
- failed planner, implementation, review, fix-loop, or test execution;
- branch divergence or missing remote update;
- repository working-tree conflict;
- transient provider, network, or process failure;
- invalid project configuration;
- unsupported or inconsistent pipeline state;
- reproducible AI Dev Factory product bug;
- blocker requiring an explicit user decision.

## Allowed recovery actions

Subject to Supervisor authorization and confirmation, the action may:

- regenerate a missing derived artifact using the expected repository convention;
- correct a malformed ticket-scoped artifact;
- refresh readiness and rule evaluation;
- fetch or pull the configured ticket branch using the approved strategy;
- restart or retry the failed pipeline stage;
- restart an approved local AI Dev Factory service when required;
- run ticket-scoped diagnostics and tests;
- create a GitHub bug issue with diagnostic evidence;
- add the created issue URL to the ticket recovery report.

## Safety requirements

- Route all actions through the Supervisor.
- Do not give Claude unrestricted shell access.
- Do not accept arbitrary paths, commands, service names, or internal endpoints from the frontend or model.
- Restrict mutations to the active ticket, its configured branch, approved artifacts, and allowlisted services.
- Never fabricate or bypass human approval.
- When the blocker is “human approval missing”, explain what must be approved and stop at the approval gate.
- Never change readiness, rule, review, or test results merely to force the ticket forward.
- Do not modify `plan.md` directly when the expected workflow requires a plan-review or plan-fix artifact.
- Do not overwrite user changes or resolve merge conflicts automatically unless an explicit safe policy permits it.
- Show the proposed recovery actions before execution.
- Record diagnostics, confirmation, mutations, retries, and results in the audit trail.
- Prevent concurrent recovery sessions for the same ticket.
- Enforce a retry and iteration limit so the agent cannot enter an infinite fix loop.
- Stop and request user input when recovery would require a product decision or destructive operation.

## Automatic bug issue creation

When Claude identifies a reproducible bug in AI Dev Factory rather than a ticket-specific failure, it must create a deduplicated GitHub issue containing:

- concise title;
- affected pipeline stage;
- ticket and project identifiers;
- expected behavior;
- actual behavior;
- sanitized error message and relevant logs;
- reproduction steps;
- suspected component;
- recovery workaround, when available;
- links to related existing issues;
- originating recovery session identifier.

Before creating the issue, search open issues for an equivalent bug. If one exists, link it in the recovery report instead of creating a duplicate.

Secrets, credentials, private prompts, unrestricted logs, and sensitive local paths must not be included in the issue.

## UX requirements

- Add a suggested or explicit `Unblock ticket` action in the AI Workspace when the active ticket is blocked.
- Display live recovery stages:
  - `DIAGNOSING`
  - `PLAN_READY`
  - `AWAITING_CONFIRMATION`
  - `APPLYING_FIX`
  - `RETRYING_STAGE`
  - `VERIFYING`
  - `RECOVERED`
  - `NEEDS_USER_INPUT`
  - `BUG_REPORTED`
  - `FAILED`
- Show the detected root cause and the exact recovery operations before confirmation.
- Stream concise progress and relevant sanitized log excerpts.
- On success, show the new ticket state and next pipeline stage.
- On partial recovery, clearly state what remains blocked and what the user must do.
- When an issue is created or linked, show its URL in the conversation.

## Acceptance criteria

- “Unblock this ticket” resolves the active Workspace ticket without requiring its identifier to be repeated.
- Claude diagnoses the actual blocking stage using current pipeline state and artifacts.
- A clear root cause and recovery plan are shown before any mutation.
- The Supervisor executes only allowlisted, ticket-scoped recovery operations.
- Human approval gates are never bypassed or fabricated.
- A recoverable missing/malformed artifact can be repaired using the correct repository convention.
- A transient failed stage can be retried and its new result verified.
- The action verifies that the ticket moved to the expected next state before reporting success.
- Recovery stops after the configured retry/iteration limit.
- A reproducible platform bug results in a deduplicated, sanitized GitHub issue or a link to an existing equivalent issue.
- The final chat response includes diagnostics, actions performed, retry result, final ticket state, and any bug issue URL.
- Existing manual recovery controls continue to work.

## Out of scope

- Bypassing human review or approval.
- Silently changing business requirements or acceptance criteria.
- Unrestricted autonomous shell access.
- Destructive Git operations.
- Automatic resolution of ambiguous merge conflicts.
- Recovery across unrelated projects or tickets.

---

## Contexte de retry injecté par run_ticket.py

## Artifact-only instruction (mandatory)

Your response will be written verbatim to `runs/T228/plan.md`.
Rewrite the artifact itself. Do not describe the modifications.
Do not explain what changed. Do not produce a status report.
Openings such as "The plan has been rewritten…", "This plan now
covers…", "Plan rewritten as…", "Key points covered…", "The
document now…" make the output invalid.

---

## Output précédent

## Objective

Add a `recover_ticket` workspace capability so a user can say "Unblock this ticket" and have Claude autonomously diagnose the blocking stage, present a constrained recovery plan, execute allowlisted fixes after confirmation, verify the ticket progresses, and file a deduplicated GitHub issue when a product bug is identified.

## Included

### New file — `services/supervisor/recovery.py`

- `BlockerClass` enum with all 11 categories from the ticket (missing artifact, stale readiness, missing approval, failed stage, branch divergence, working-tree conflict, transient failure, invalid config, inconsistent state, product bug, user decision required).
- `RecoverySession` dataclass: `session_id`, `ticket_id`, `project_id`, `stage` (one of `DIAGNOSING / PLAN_READY / AWAITING_CONFIRMATION / APPLYING_FIX / RETRYING_STAGE / VERIFYING / RECOVERED / NEEDS_USER_INPUT / BUG_REPORTED / FAILED`), `iteration_count`, `max_iterations` (constant `MAX_RECOVERY_ITERATIONS = 3`), `operations_log`.
- `ALLOWLISTED_RECOVERY_OPS` mapping: keys are op names (`regenerate_artifact`, `refresh_readiness`, `retry_stage`, `fetch_branch`, `restart_service`, `run_diagnostics`, `create_bug_issue`); values carry risk level and required params.
- `classify_blocker(state_data: dict, artifacts: dict, logs: str) -> BlockerClass` — pure function, reads existing diagnostic output from `ticket_diagnostics.diagnose_ticket()`.
- `build_recovery_plan(blocker: BlockerClass, state_data: dict) -> list[RecoveryOp]` — returns ordered list of allowlisted ops, never includes destructive ops.
- `apply_recovery_op(op: RecoveryOp, project_root: Path, project_id: str, ticket_id: str) -> OpResult` — executes one op, appends to session log; refuses any op not in `ALLOWLISTED_RECOVERY_OPS`.
- `verify_ticket_progress(ticket_id: str, project_root: Path, expected_next_state: str) -> tuple[bool, str]` — reads `state.json`, returns `(progressed, new_state)`.
- `search_existing_bug_issues(repo: str, bug_signature: str) -> str | None` — calls GitHub search API; returns URL of matching issue or `None`.
- `create_bug_issue(repo: str, bug_data: dict) -> str` — builds sanitized issue body (no secrets, no private paths), creates issue, returns URL. Only called when `search_existing_bug_issues` returns `None`.

### Modified — `services/supervisor/main.py`

- Add `recover_ticket` to `_WORKSPACE_CAPABILITIES` (lines ~2876–2889) with `confirmation_required: True`.
- Add module-level `_active_recovery_sessions: dict[str, RecoverySession]` keyed by `ticket_id`; prevents concurrent recovery by returning a structured error when a session already exists.
- Add `_resolve_active_ticket_id(project_id: str) -> str | None` — thin wrapper around the logic already in `daemon_manager._current_ticket()`, exposed for use within the supervisor.
- Add `_execute_recover_ticket(project_id: str, project_root: Path) -> dict` — orchestrates the full recovery flow using `recovery.py`; enforces `MAX_RECOVERY_ITERATIONS`; records diagnostics, confirmation point, mutations, retries, and result in session log; cleans up session on terminal state.
- Extend `_workspace_project_context()` (lines ~2944–2971) to include active ticket id, current `state` field, and blocked stage when the ticket is not progressing.
- Extend `_execute_workspace_capability()` (line ~3042) to dispatch `recover_ticket` to `_execute_recover_ticket()`.
- Extend workspace chat system prompt to recognise "unblock", "stuck", and "blocked ticket" as `recover_ticket` intents.
- Response for `recover_ticket` includes `recovery_report` field: root cause, ops performed, retry result, new ticket state, bug issue URL (if any).

### Modified — `apps/dashboard/src/components/ProjectWorkspacePanel.jsx`

- Add `RecoveryStageIndicator` sub-component: renders a coloured badge for each `recovery_stage` value (`DIAGNOSING` → grey, `PLAN_READY` → blue, `AWAITING_CONFIRMATION` → yellow, `APPLYING_FIX` → orange, `RETRYING_STAGE` → orange, `VERIFYING` → blue, `RECOVERED` → green, `NEEDS_USER_INPUT` → yellow, `BUG_REPORTED` → purple, `FAILED` → red).
- Show the badge inside the assistant message bubble when the message carries a `recovery_stage` field.
- Add an "Unblock ticket" suggested-action button that appears in the chat input area when the last workspace message indicates the ticket is blocked (detected by `recovery_stage === 'NEEDS_USER_INPUT'` or `recovery_stage === 'FAILED'`); clicking it submits the literal message `"Unblock this ticket"`.
- On `recovery_report` in message payload: render a collapsible summary card listing root cause, ops performed, and bug issue link when present.

### New file — `tests/test_workspace_recovery.py`

- `test_recover_ticket_in_allowlist` — verifies `recover_ticket` is in `_WORKSPACE_CAPABILITIES`.
- `test_concurrent_recovery_rejected` — starting a second session for the same ticket while one is active returns a structured error (not 500).
- `test_iteration_limit_enforced` — after `MAX_RECOVERY_ITERATIONS` retries, session reaches `FAILED` and stops.
- `test_blocker_classification` — parametrised over each `BlockerClass` variant with fixture state/artifact combinations.
- `test_only_allowlisted_ops_execute` — passing an op name not in `ALLOWLISTED_RECOVERY_OPS` to `apply_recovery_op` raises `ValueError`.
- `test_active_ticket_resolution` — `_resolve_active_ticket_id` returns the ticket whose `state.json` contains `"RUNNING"`.
- `test_bug_issue_deduplication` — when `search_existing_bug_issues` returns a URL, `create_bug_issue` is not called.
- `test_recovery_verification_step` — `verify_ticket_progress` returns `(False, original_state)` when state is unchanged, `(True, new_state)` when it advances.
- `test_workspace_chat_unblock_intent` — chat message "Unblock this ticket" produces `proposed_action.capability == "recover_ticket"`.

## Excluded

- Streaming/SSE protocol changes — uses existing request-response flow; recovery stage is a field in the JSON response.
- Automatic resolution of ambiguous merge conflicts.
- Unrestricted shell or filesystem access beyond current supervisor subprocess model.
- Recovery spanning multiple projects or multiple tickets in a single session.
- Bypassing human approval gates; `missing_approval` blocker class terminates with `NEEDS_USER_INPUT` and explains what must be approved.
- Destructive git operations (`reset --hard`, force-push).
- Changes to `plan.md` outside the normal plan/plan-review artifact convention.
- Changes to existing capabilities (`restart_daemon`, `resume_execution`, `rerun_dependency_analysis`).

## Acceptance criteria

- Sending "Unblock this ticket" in the Workspace chat resolves the active ticket id without requiring the user to specify it; confirmed via `test_workspace_chat_unblock_intent`.
- Diagnostics phase reads only existing artifacts and logs; no state mutation occurs before confirmation; confirmed by `test_blocker_classification`.
- Root cause classification covers all 11 categories defined in the ticket; confirmed by parametrised `test_blocker_classification`.
- The action confirmation card shows the exact ops to be executed before the user clicks confirm; recovery_report field present in response.
- Only op names present in `ALLOWLISTED_RECOVERY_OPS` can be executed; confirmed by `test_only_allowlisted_ops_execute`.
- A second "Unblock" request while a session is active for the same ticket returns a non-500 structured error; confirmed by `test_concurrent_recovery_rejected`.
- Recovery halts and returns `FAILED` after `MAX_RECOVERY_ITERATIONS` attempts; confirmed by `test_iteration_limit_enforced`.
- `search_existing_bug_issues` is always called before `create_bug_issue`; duplicate bugs link to the existing issue; confirmed by `test_bug_issue_deduplication`.
- Recovery report in the final chat message includes root cause, list of ops performed, new ticket state, and bug issue URL when applicable; field schema enforced in `test_workspace_chat_unblock_intent`.
- `RecoveryStageIndicator` renders the correct badge colour for each `recovery_stage` value; existing workspace capability tests (`test_supervisor_workspace.py`) remain green.

---

## Review

# PLAN_FIX_REQUIRED

## Summary

The revised plan still does not explicitly separate the read-only preparation phase from the post-confirmation execution phase. This is required so the user confirms the exact recovery operations before any mutation occurs.

## Required fixes

1. Add an explicit read-only preparation step, for example `_prepare_recovery_action(...)`, that:
   - resolves the active ticket;
   - runs diagnostics without mutation;
   - classifies the blocker;
   - builds the exact allowlisted recovery operations;
   - stores a structured recovery proposal;
   - returns the exact operations in `proposed_action` for the confirmation card.

2. Add a separate post-confirmation execution step, for example `_execute_recovery_action(...)`, that:
   - loads the stored proposal by action/session id;
   - ignores operation definitions supplied by the frontend;
   - revalidates the ticket state before execution;
   - executes only the operations that were prepared and confirmed.

3. Add a `RecoveryProposal` or equivalent structure containing at least:
   - `project_id`;
   - `ticket_id`;
   - `blocker_class`;
   - exact ordered operations and validated parameters;
   - current ticket state and blocked stage;
   - a state/artifact fingerprint or version;
   - creation timestamp.

4. Revalidate the proposal fingerprint at confirmation time. If the ticket state or relevant artifacts changed after preparation, reject execution with a structured conflict response and require a new diagnosis.

5. Document the exact `proposed_action` schema rendered by the confirmation card, including operation name, description, risk level, and safe validated parameters.

6. Add tests proving that:
   - preparation performs no mutation;
   - the confirmation card receives the exact stored operations;
   - frontend-supplied operation changes are ignored;
   - stale proposals are rejected after ticket state changes;
   - only the confirmed stored proposal can be executed.

## Decision

PLAN_FIX_REQUIRED

---

## Instructions de fix

# PLAN_FIX_REQUIRED — iteration 3

The current `runs/T228/plan.md` is still the original plan and has not incorporated the previous plan-fix artifacts. Regenerate and replace `runs/T228/plan.md`; do not merely acknowledge this artifact.

## Mandatory architecture correction

The recovery workflow must be explicitly split into four distinct phases:

1. **Prepare (read-only)**
   - Resolve the active ticket.
   - Run diagnostics without mutating ticket state.
   - Classify the blocker.
   - Build an exact allowlisted recovery plan.
   - Create and persist a `RecoveryProposal` snapshot.
   - Return a `proposed_action` containing the exact operations that will require confirmation.

2. **Confirm**
   - The confirmation card must display the exact ticket id, blocker class, operations, operation parameters, descriptions, and risk levels.
   - The frontend confirms only by `action_id`; it must not resend or alter operations or parameters.

3. **Revalidate**
   - Before execution, reload the ticket state and compare it to the stored proposal fingerprint.
   - The fingerprint must include at least ticket id, current state, blocked stage, relevant artifact metadata, and a state/artifact version or deterministic hash.
   - If the ticket changed after preparation, return HTTP 409 and require a new diagnostic. Do not execute a stale plan.

4. **Execute**
   - Execute only the immutable operations stored in the confirmed `RecoveryProposal`.
   - Revalidate every operation name and parameter against the Supervisor allowlist.
   - Never accept operation names, paths, services, repositories, commands, or parameters supplied by the frontend at confirmation time.

## Required data structures

Define a structured `RecoveryProposal` containing at least:

- `proposal_id`
- `project_id`
- `ticket_id`
- `blocker_class`
- `operations`
- `state_fingerprint`
- `created_at`
- `status` (`AWAITING_CONFIRMATION`, `EXECUTING`, `COMPLETED`, `INVALIDATED`)

Each proposed operation must contain only closed, validated fields such as:

- `name`
- `description`
- `risk_level`
- `params`

## Operation contracts

For every allowlisted operation, document:

- accepted parameter schema;
- internal service/function invoked;
- preconditions;
- mutation performed;
- success condition;
- retry policy;
- prohibited arbitrary values.

Examples:

- `regenerate_artifact` must accept a closed artifact type enum, never a free filesystem path.
- `restart_service` must resolve a configured service identifier, never a free service name or shell command.
- `create_bug_issue` must resolve the configured project repository server-side.

## Concurrency and lifecycle

- Protect proposal/session creation with a dedicated lock so check-and-create is atomic.
- Guarantee cleanup in `finally` after execution errors.
- Preserve terminal recovery results in a separate result registry long enough for frontend polling.
- Long-running recovery must use a background job with `recovery_id` and a polling endpoint, unless the regenerated plan rigorously proves all operations are short and non-blocking.

## Deterministic bug deduplication

Build the bug signature from structured fields such as:

- `project_id`
- `blocker_class`
- `failed_stage`
- normalized error code
- affected component

Do not use free-form LLM text as the deduplication key.

## Required tests

Add tests proving that:

- preparation performs no mutation;
- the confirmation card receives the exact stored operations;
- the frontend cannot alter operations or params;
- a changed ticket state invalidates the proposal with HTTP 409;
- only the stored immutable proposal is executed;
- concurrent preparation/execution for the same ticket is rejected atomically;
- locks are released after exceptions;
- arbitrary paths, services, repositories, commands, and operation names are rejected;
- missing approval never triggers automatic approval;
- duplicate product bugs never create a second GitHub issue;
- intermediate asynchronous stages are available through polling.

## Expected output

Replace `runs/T228/plan.md` with a new plan that explicitly implements the architecture above. The new `plan.md` must have different content and a different Git blob SHA from the original plan.