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

# Role — Coder

## Mission

Implémenter strictement un ticket en suivant le plan validé et les skills applicables.

## Tu dois

- lire le ticket
- lire le plan validé
- respecter le scope
- lister les fichiers créés ou modifiés
- produire un changement minimal, lisible et testable
- ajouter ou adapter les tests si nécessaire
- signaler les hypothèses et limites

## Tu ne dois pas

- élargir le ticket
- réécrire l’architecture sans demande explicite
- faire un refactor massif non demandé
- modifier la mémoire projet sauf si le ticket le demande explicitement
- masquer les erreurs ou incertitudes

## Sortie attendue

- résumé des changements
- liste des fichiers modifiés
- vérifications effectuées
- limites connues

## Règles

- coder uniquement après `PLAN_APPROVED`
- ne jamais contourner les contraintes du plan
- garder les changements petits et reviewables

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

# SKILL: git-discipline

# Skill — Git Discipline

## Objectif

Maintenir un historique Git propre, compréhensible et traçable.

## Règles

- un ticket = une unité de travail cohérente
- éviter les commits mélangeant plusieurs sujets
- utiliser des messages de commit explicites
- conserver les PR lisibles
- éviter les modifications hors scope
- maintenir les fichiers mémoire cohérents avec les changements réels

## Refuser si

- la PR mélange plusieurs fonctionnalités
- des changements non liés sont ajoutés
- les commits deviennent impossibles à reviewer

---

# SKILL: code-quality

# Skill — Code Quality

## Objectif

Produire des changements simples, lisibles, robustes et faciles à reviewer.

## Règles

- privilégier le code simple avant le code sophistiqué
- utiliser des noms explicites
- garder des fonctions courtes et lisibles
- éviter la magie cachée
- gérer les erreurs explicitement
- ajouter des logs utiles sans bruit excessif
- éviter les dépendances inutiles
- conserver un changement borné au ticket

## Refuser si

- le code devient inutilement complexe
- le ticket introduit une dépendance non justifiée
- les erreurs sont masquées
- les changements dépassent le scope demandé

---

# SKILL: refactor-safety

# Skill — Refactor Safety

## Objectif

Limiter les régressions et les dérives de scope lors des modifications.

## Règles

- modifier uniquement le périmètre demandé
- éviter les refactors transversaux implicites
- préserver les comportements existants
- maintenir la compatibilité sauf demande explicite
- privilégier des changements incrémentaux

## Refuser si

- le ticket dérive vers une réécriture globale
- plusieurs couches sont modifiées sans justification
- le comportement change silencieusement

---

# SKILL: security

# Skill — Security

## Objectif

Réduire les risques de sécurité et éviter les comportements dangereux.

## Règles

- ne pas exposer de secrets dans logs ou documentation
- limiter les permissions au strict nécessaire
- éviter les exécutions implicites dangereuses
- valider les entrées externes
- documenter les impacts sécurité importants
- éviter les comportements destructifs implicites

## Refuser si

- des secrets sont hardcodés
- des données sensibles sont logguées
- une opération destructive n’est pas explicitement contrôlée

---

# TASK

# Generic Coder Task

Read the ticket and the approved plan below, then implement the required changes.

The implementation must:
- follow the approved plan strictly
- remain within scope
- list all created or modified files
- be minimal, readable, and testable

The ticket follows.


# T198 — Add Ticket Readiness Evaluator and execution eligibility workflow

**Source**: GitHub Issue #253

## Description

# Add Ticket Readiness Evaluator and execution eligibility workflow

## Context

AI Dev Factory now includes a Ticket Intelligence Analyzer that enriches tickets with advisory metadata.

The next step is to determine whether a ticket is actually eligible to enter the development pipeline.

A dedicated Readiness Evaluator must analyze the current project state and determine if a ticket can be executed.

This component is intentionally separate from Ticket Intelligence.

```text
Ticket Intelligence
= analysis / recommendations

Readiness Evaluator
= execution eligibility decision
```

The goal is to avoid situations where tickets start with stale context, missing approvals, or unresolved dependencies.

## Goals

Introduce a new evaluation step:

```text
Ticket
↓
Ticket Intelligence
↓
Readiness Evaluator
↓
Ready Candidate / Blocked
```

The evaluator decides whether a ticket is:

```text
READY_CANDIDATE
BLOCKED
```

without modifying the existing execution pipeline yet.

For this ticket, the evaluator is advisory only.

## Non-goals

Do not:

- automatically start ticket execution
- modify scheduler behavior
- reorder queues
- dispatch workers
- enforce execution policies
- automatically merge tickets

These behaviors will be implemented later.

## Ticket lifecycle additions

Introduce two new ticket states:

```text
READY_CANDIDATE
BLOCKED
```

A ticket may become READY_CANDIDATE when all readiness checks pass.

A ticket becomes BLOCKED when at least one readiness rule fails.

The evaluator must also expose blocking reasons.

Example:

```text
Status: BLOCKED

Reasons:
- Dependency T001 not merged
- Human plan approval missing
```

## Database

Create a new table:

```text
ticket_readiness
```

Suggested fields:

```text
ticket_id
readiness_status
blocking_reasons_json
warnings_json
dependency_check_status
approval_check_status
context_freshness_status
human_approval_required
human_approval_present
ready_candidate
evaluated_at
created_at
updated_at
```

Only one active readiness evaluation per ticket is required.

## Readiness checks

The evaluator should support the following checks.

### Dependency validation

Detect explicit dependencies:

```text
Depends on T001
After T001
Blocked by T001
```

Verify:

```text
all prerequisite tickets are merged into main
```

If not:

```text
BLOCKED
```

### Human approval validation

Use Ticket Intelligence metadata.

If:

```text
requires_human_plan_review = true
```

then verify approval exists.

If approval is missing:

```text
BLOCKED
```

### Context freshness validation

Store:

```text
main_sha_when_evaluated
```

Future components will compare this against current main.

For this ticket only expose:

```text
fresh
unknown
stale
```

without enforcing execution behavior.

### Intelligence validation

A ticket cannot become READY_CANDIDATE if:

```text
Ticket Intelligence analysis does not exist
```

Example:

```text
BLOCKED
Reason: Missing Ticket Intelligence analysis
```

## Evaluator service

Create:

```text
tools/agent_runner/ticket_readiness_evaluator.py
```

Responsibilities:

1. Load ticket
2. Load Ticket Intelligence result
3. Execute readiness checks
4. Produce structured readiness result
5. Persist result in DB

Suggested output:

```json
{
  "readiness_status": "BLOCKED",
  "ready_candidate": false,
  "blocking_reasons": [
    "Dependency T001 not merged",
    "Human plan approval missing"
  ],
  "warnings": [],
  "dependency_check_status": "failed",
  "approval_check_status": "failed",
  "context_freshness_status": "fresh"
}
```

## API

Add:

```text
GET /api/tickets/{ticket_id}/readiness
POST /api/tickets/{ticket_id}/evaluate-readiness
```

POST should behave similarly to Ticket Intelligence:

```text
returns 202 Accepted
runs in background
```

## Frontend

Add a new panel:

```text
Ticket Readiness
```

Display:

- readiness status
- ready candidate badge
- blocking reasons
- warnings
- last evaluation date
- dependency state
- approval state
- context freshness state

Example:

```text
READY CANDIDATE

No blocking issues detected.
```

or

```text
BLOCKED

- Dependency T001 not merged
- Missing human approval
```

## Human workflow

For now, human users manually decide if a READY_CANDIDATE ticket should later become:

```text
READY_TO_TAKE
```

This ticket does not implement READY_TO_TAKE.

## Acceptance criteria

- Tickets can be evaluated for readiness independently of execution.
- Readiness results are persisted in DB.
- Missing Ticket Intelligence analysis blocks readiness.
- Dependency checks produce blocking reasons.
- Human approval requirements produce blocking reasons.
- API exposes readiness information.
- Dashboard displays readiness status and blocking reasons.
- Existing scheduler and execution behavior remain unchanged.
- Existing test suite continues to pass.

---

## Contexte de retry injecté par run_ticket.py

## Output précédent

All implemented and tested. The auto-commit hook captured all 16 files in commit `6ec637a1`.

## Summary

T198 implemented per the approved plan. The Readiness Evaluator is advisory only: it persists a verdict per ticket but does not touch the scheduler, worker, or any execution gate.

### Files added
- `tools/agent_runner/ticket_merge_state.py` — `is_ticket_merged()` with the runtime-DB → GitHub metadata → `git log` resolution order.
- `tools/agent_runner/ticket_readiness_evaluator.py` — `run_evaluation()` background job. Checks intelligence presence, declared dependencies (`Depends on / After / Blocked by T###`), human plan approval (intelligence-driven), and captures `main` SHA for context freshness. Persists `ready_candidate | blocked | failed` with blocking reasons.
- `services/control_api/routes/readiness.py` — `GET /tickets/{id}/readiness` (200/404) and `POST /tickets/{id}/evaluate-readiness` (202, idempotent while `queued/running`), plus `/projects/{id}/...` variants. Registered in `main.py`.
- `apps/dashboard/src/components/TicketReadinessPanel.jsx` — status badge, READY CANDIDATE highlight, blocking-reasons list, warnings, sub-check states, last evaluation date, evaluate button. Mounted in `TicketDetailPage.jsx`.
- `tests/test_ticket_readiness_db.py`, `test_ticket_merge_state.py`, `test_ticket_readiness_evaluator.py`, `test_ticket_readiness_api.py` — 34 tests, all green.

### Files modified
- `tools/agent_runner/runtime_db.py` / `runtime_db_pg.py` — added `ticket_readiness` table (canonical lowercase statuses) and `upsert_ticket_readiness` / `get_ticket_readiness` with JSON-list encode/decode; Postgres rebinding added.
- `services/control_api/models/schemas.py` — `TicketReadiness` + `TicketReadinessQueued`.
- `services/control_api/main.py` — registered `readiness` router (and project variant).
- `apps/dashboard/src/api/tickets.js` — `getTicketReadiness` / `postEvaluateReadiness` helpers.

### Verifications
- 34/34 new tests pass.
- Broad suite `pytest tests/ --ignore=tests/integration --ignore=tests/supervisor` returns `118 failed, 1494 passed, 12 errors` — **identical numbers to the pre-change baseline**, so no regressions.

### Limits / assumptions
- Human approval detection looks for `runs/<ticket>/plan-approved.md`, with a fallback that treats a `state.json` state at or beyond `PLAN_APPROVED` as approved (the existing workflow's own approval signal).
- Frontend was not exercised in a browser; React panel changes are covered by component-shape inspection only.

---

## Review

# Implementation review — T198 Ticket Readiness Evaluator

The Readiness Evaluator code itself is well-built and matches the approved plan: canonical lowercase statuses, structured `is_ticket_merged` helper, `ticket_readiness` table in both SQLite and Postgres, advisory-only behaviour, 202/idempotent POST, scoped React panel, 34/34 targeted tests pass.

## Blocking issue — silent revert of `main`'s commit `66165e13`

`git merge-base main HEAD` = `0532acd9`, which predates main's recent fix `66165e13` (*"fix(intelligence): run ticket analysis on host when API is in Docker"*). The T198 branch was never rebased on current `main`, so its diff against `main` **deletes** that fix when merged:

- `services/supervisor/main.py:2194-2287` — the host-side `POST /projects/{project_id}/tickets/{ticket_id}/intelligence/analyze` endpoint (−88 lines).
- `services/control_api/routes/intelligence.py` — `_supervisor_url`, `_needs_host_exec`, `_delegate_analyze_to_supervisor`, the project-id forwarding signature, and the in-route delegation branch (−72 lines).
- `tests/test_ticket_intelligence_api.py` — `test_project_post_analyze_delegates_to_supervisor_in_docker` (−15 lines).

None of these appear in the plan, the fix instructions, or `implementation-output.md` — the revert is unintentional. Impact: in the standard `docker-compose.yml` deployment the control_api container has no `claude` CLI, so `POST /tickets/{id}/intelligence/analyze` will fail again.

**Required fix:** rebase the branch onto current `main` so the three files above retain the post-`66165e13` content. T198's own code does not need to change.

## Minor observations
- `_check_human_approval` accepts the runtime `PLAN_APPROVED` state as a proxy for human approval; the plan only described a marker file (`runs/<id>/plan-approved.md`). The daemon's own agent-driven plan review can set this state without a human, so the fallback can produce false positives. Not blocking for advisory mode.
- `_check_dependencies` swallows `is_ticket_merged` exceptions into `Dependency T<id> merge state unknown` with no `warnings` entry — consider preserving the exception in `warnings`.
- Project-scoped readiness routes ignore `project_id` (mirrors `intelligence.py`); fine today, worth a TODO.
- `runs/T198/prompts/planner-attempt-1.md … attempt-7.md` and `coder-attempt-1.md` (~5,000 lines of generated prompts) are committed; prune if convention is final-only.
- Checkpoint commit `6ec637a1` carrying T198 code is labelled `T001:` — looks like an auto-commit hook mislabel, separate follow-up.

The review file is at `runs/T198/reviews/review-attempt-2.md`.

IMPLEMENTATION_FIX_REQUIRED

---

## Instructions de fix

# Fix artifact — IMPLEMENTATION_FIX_REQUIRED

- decision: IMPLEMENTATION_FIX_REQUIRED
- review source: runs/T198/reviews/implementation-review.md
- generated at: 2026-06-21T17:17:18Z

---

# Implementation review — T198 Ticket Readiness Evaluator

The Readiness Evaluator code itself is well-built and matches the approved plan: canonical lowercase statuses, structured `is_ticket_merged` helper, `ticket_readiness` table in both SQLite and Postgres, advisory-only behaviour, 202/idempotent POST, scoped React panel, 34/34 targeted tests pass.

## Blocking issue — silent revert of `main`'s commit `66165e13`

`git merge-base main HEAD` = `0532acd9`, which predates main's recent fix `66165e13` (*"fix(intelligence): run ticket analysis on host when API is in Docker"*). The T198 branch was never rebased on current `main`, so its diff against `main` **deletes** that fix when merged:

- `services/supervisor/main.py:2194-2287` — the host-side `POST /projects/{project_id}/tickets/{ticket_id}/intelligence/analyze` endpoint (−88 lines).
- `services/control_api/routes/intelligence.py` — `_supervisor_url`, `_needs_host_exec`, `_delegate_analyze_to_supervisor`, the project-id forwarding signature, and the in-route delegation branch (−72 lines).
- `tests/test_ticket_intelligence_api.py` — `test_project_post_analyze_delegates_to_supervisor_in_docker` (−15 lines).

None of these appear in the plan, the fix instructions, or `implementation-output.md` — the revert is unintentional. Impact: in the standard `docker-compose.yml` deployment the control_api container has no `claude` CLI, so `POST /tickets/{id}/intelligence/analyze` will fail again.

**Required fix:** rebase the branch onto current `main` so the three files above retain the post-`66165e13` content. T198's own code does not need to change.

## Minor observations
- `_check_human_approval` accepts the runtime `PLAN_APPROVED` state as a proxy for human approval; the plan only described a marker file (`runs/<id>/plan-approved.md`). The daemon's own agent-driven plan review can set this state without a human, so the fallback can produce false positives. Not blocking for advisory mode.
- `_check_dependencies` swallows `is_ticket_merged` exceptions into `Dependency T<id> merge state unknown` with no `warnings` entry — consider preserving the exception in `warnings`.
- Project-scoped readiness routes ignore `project_id` (mirrors `intelligence.py`); fine today, worth a TODO.
- `runs/T198/prompts/planner-attempt-1.md … attempt-7.md` and `coder-attempt-1.md` (~5,000 lines of generated prompts) are committed; prune if convention is final-only.
- Checkpoint commit `6ec637a1` carrying T198 code is labelled `T001:` — looks like an auto-commit hook mislabel, separate follow-up.

The review file is at `runs/T198/reviews/review-attempt-2.md`.

IMPLEMENTATION_FIX_REQUIRED