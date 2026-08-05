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

The recovery concept is strong, but the plan must be revised before implementation to guarantee that the user confirms the exact recovery operations that will run, that stale recovery plans cannot be executed, and that long-running recovery remains observable and concurrency-safe.

## Required fixes

### 1. Separate preparation from execution

Introduce two explicit phases:

- `_prepare_recovery_action(...)`: read-only diagnostics, blocker classification, recovery-plan construction, and pending-action creation.
- `_execute_recovery_action(...)`: revalidate the ticket snapshot and execute only the operations stored in the confirmed pending action.

The `proposed_action` returned to the frontend must include the exact ticket id, blocker class, and ordered operations before confirmation.

### 2. Add stale-plan protection

Store a minimal ticket snapshot/fingerprint in the pending action, including at least:

- ticket id;
- current state;
- blocked stage;
- state artifact timestamp or hash;
- observed relevant artifacts;
- exact recovery operations.

At confirmation time, re-read the ticket state. If the snapshot changed, return a conflict and require a new diagnosis instead of executing the stale plan.

### 3. Define every allowlisted operation precisely

For each recovery operation, document:

- allowed parameters;
- internal API or service invoked;
- preconditions;
- expected effects;
- success criteria;
- retry behavior;
- definition of ticket progress.

Do not accept arbitrary paths, service names, commands, or artifact names from the LLM or frontend. Use closed enums and configured identifiers only.

### 4. Use an asynchronous recovery job

Recovery can span diagnostics, fixes, retries, verification, and up to three iterations. Confirm should return a `recovery_id` and `RUNNING` status immediately. Add a polling endpoint exposing intermediate stages and terminal results:

- `DIAGNOSING`
- `PLAN_READY`
- `APPLYING_FIX`
- `RETRYING_STAGE`
- `VERIFYING`
- `RECOVERED`
- `NEEDS_USER_INPUT`
- `BUG_REPORTED`
- `FAILED`

### 5. Make concurrency handling atomic

Add a dedicated lock around `_active_recovery_sessions`. The check-and-create operation must be atomic. Cleanup must happen in `finally`, while terminal reports remain available in a separate result registry for frontend polling.

### 6. Make bug deduplication deterministic

Define `bug_signature` from structured normalized fields such as:

- project id;
- blocker class;
- failed stage;
- normalized error code;
- affected component.

Search only the configured repository for the active project. Never use free-form LLM text as the deduplication key.

## Required tests

Add tests proving that:

- preparation performs no mutation;
- the confirmed operation list exactly matches the presented plan;
- changed ticket state between proposal and confirmation returns a conflict;
- frontend-supplied or modified operations are ignored;
- two concurrent recoveries cannot start for the same ticket;
- locks and active-session state are released after exceptions;
- arbitrary operation parameters are rejected;
- intermediate recovery stages can be polled;
- `missing_approval` never causes automatic approval;
- an existing matching bug issue prevents duplicate creation.

## Decision

PLAN_FIX_REQUIRED

---

## Instructions de fix

# PLAN_FIX_REQUIRED

## Summary

The recovery concept is strong, but the plan must be revised so that the user confirms an exact, immutable recovery plan before any mutating operation is executed.

## Required fixes

### 1. Separate preparation from execution

Add a read-only preparation phase such as `_prepare_recovery_action(...)` that:

- resolves the active ticket;
- runs diagnostics without mutation;
- classifies the blocker;
- builds the exact ordered recovery plan;
- stores the validated plan in the pending action;
- returns the blocker class and exact operations in `proposed_action`.

Add a separate execution phase such as `_execute_recovery_action(...)` that runs only after confirmation and executes only the stored allowlisted operations.

The confirmation card must display the exact operations, descriptions, parameters and risk levels before the user confirms.

### 2. Reject stale recovery plans

Store a compact ticket-state fingerprint with the pending action, including at least:

- project id;
- ticket id;
- current state;
- blocked stage;
- state artifact timestamp, hash or equivalent version;
- observed artifact set;
- exact recovery operations.

At confirmation time, re-read the current ticket state. If it no longer matches the prepared snapshot, return a conflict response and require a new diagnosis. Do not execute the stale plan.

### 3. Define every allowlisted operation precisely

For each operation, document:

- accepted parameters and closed enums;
- internal service or API invoked;
- preconditions;
- expected effects;
- success criteria;
- retry policy;
- verification rule.

No operation may accept arbitrary paths, service names, commands or other free-form execution values from the LLM or frontend.

Examples:

- `regenerate_artifact` must accept only supported artifact types and use the normal workflow.
- `restart_service` must resolve a configured service identifier through an allowlist.
- `retry_stage` must target only the diagnosed stage stored in the confirmed plan.

### 4. Use an asynchronous recovery job

The confirmed action should return a `recovery_id` and run in the background so the Supervisor remains responsive.

Provide a polling endpoint exposing stages such as:

- `APPLYING_FIX`;
- `RETRYING_STAGE`;
- `VERIFYING`;
- `RECOVERED`;
- `NEEDS_USER_INPUT`;
- `BUG_REPORTED`;
- `FAILED`.

Persist the final recovery report long enough for the frontend to retrieve it after the active-session lock is released.

### 5. Make concurrency protection atomic

Add a dedicated lock around `_active_recovery_sessions`.

The check and insertion for a ticket must occur in one critical section. Session cleanup and lock release must be guaranteed in `finally`, including unexpected exceptions.

Concurrent recovery for the same ticket must return a structured conflict response, not HTTP 500.

### 6. Make bug deduplication deterministic

Define a stable bug signature from structured fields such as:

- configured project repository;
- blocker class;
- failed stage;
- normalized error code;
- affected component.

Do not use unrestricted LLM-generated text as the deduplication key. The GitHub repository must be resolved from trusted project configuration.

### 7. Add missing tests

Add tests proving that:

- preparation performs no mutation;
- the confirmation payload contains the exact stored recovery plan;
- ticket-state changes before confirmation cause a conflict;
- frontend-supplied operation or parameter changes are ignored or rejected;
- concurrent preparation/execution creates only one active session per ticket;
- locks and sessions are cleaned after exceptions;
- arbitrary operation parameters are refused;
- intermediate asynchronous stages can be polled;
- `missing_approval` never approves automatically;
- an existing matching bug issue prevents duplicate creation.

## Decision

PLAN_FIX_REQUIRED