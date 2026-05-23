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



# T141 — T141 — Full sandbox environments and lifecycle management

**Source**: GitHub Issue #131

## Description

Goal: make each sandbox a complete isolated runtime environment with full lifecycle management.

Context:
T140 introduces isolated runtime roots and isolated supervisors.

The next step is making a sandbox behave like a full independent environment containing all required runtime components for a project.

A sandbox should not only expose isolated API/web ports. It should represent a complete runnable project environment.

Scope:
- sandbox environments must support full runtime component topology
- sandbox deploy profiles must declare runtime components generically
- sandbox startup must start all declared components
- support components such as:
  - api
  - web
  - supervisor
  - daemon
  - workers
  - databases
  - redis
  - custom services
- sandbox dashboard must display runtime components and component states
- add sandbox lifecycle actions:
  - start
  - stop
  - restart
  - cleanup/delete
  - refresh state
- stopping a sandbox must:
  - stop compose services
  - stop supervisor
  - stop daemon/workers
  - release ports
  - clean locks and pid files safely
- cleanup must preserve optional logs/state artifacts when configured
- sandbox dashboard must display:
  - sandbox URLs
  - runtime root
  - allocated ports
  - component health
  - running/stopped state
  - uptime
- support multiple concurrent sandbox environments safely
- runtime topology must remain generic and not ai-dev-factory specific

Out of scope:
- distributed orchestration
- Kubernetes support
- cloud deployment
- production deployment
- automatic AI self-healing loops

Acceptance:
- a sandbox represents a full isolated runtime environment
- sandbox lifecycle actions work safely
- all runtime components stop correctly on sandbox shutdown
- ports and locks are released correctly
- dashboard displays sandbox runtime topology and state
- multiple sandbox environments can coexist safely
- the implementation remains generic and reusable across projects

---

## Contexte de retry injecté par run_ticket.py

## Output précédent

The plan is written to `runs/T141/plan.md`. Here's what it covers:

**Core problem identified:** `stop()` at line 176 only runs `docker compose down` — it never calls `_terminate_sandbox_supervisor()`, never calls `_release_slot()`, and never cleans pid/lock files.

**Three changes to `sandbox_manager.py`:**
1. Fix `stop()` — add supervisor termination, pid/lock cleanup, and port release
2. Add `restart()` — stop + start
3. Add `refresh()` — stateless re-read of state.json

**Two new endpoints in `routes/sandbox.py`:**
- `POST /sandboxes/{id}/restart`
- `POST /sandboxes/{id}/refresh`

**Dashboard enrichment in `routes/runtime_dashboard.py`:**
- `SandboxRunSummary` gains `runtime_root` and `uptime_seconds`
- Three new proxied lifecycle endpoints (stop/restart/refresh)

**Tests** cover the supervisor SIGTERM mock, port release, pid/lock cleanup, restart transitions, refresh no-side-effects, and concurrent safety.

---

## Review

# Plan review — T141

Decision: PLAN_FIX_REQUIRED

The current T141 plan is too ambitious for one implementation ticket.

It combines:

- generic runtime topology model
- sandbox-profile.yml format
- component startup abstraction
- component health polling
- daemon/worker/database/redis/custom component handling
- lifecycle endpoints
- restart/destroy/preserve logs
- runtime dashboard enrichment
- multiple new test suites

These are valuable, but the immediate runtime need is simpler and more urgent: the user can start sandbox environments but cannot safely stop, restart, or clean them up from the UI.

## Requested change

Rewrite T141 as a focused V1:

> Sandbox lifecycle controls: stop, restart, cleanup/delete, refresh.

The ticket should focus on safe lifecycle operations for existing sandbox runs.

Do not introduce the generic topology model or sandbox-profile.yml in this ticket.

See `runs/T141/fixes/plan-fix-1.md` for the requested reduced scope.

---

## Instructions de fix

# Plan fix — T141 V1

## New objective

Implement safe sandbox lifecycle management for existing sandbox environments.

The primary user need is:

- start sandbox
- stop sandbox
- restart sandbox
- cleanup/delete sandbox
- refresh sandbox state

The implementation should focus on stable runtime lifecycle behavior before introducing generic topology abstractions.

---

# Included

## Sandbox lifecycle operations

Implement:

- stop sandbox
- restart sandbox
- cleanup/delete sandbox
- refresh sandbox state

## Safe shutdown behavior

Stopping a sandbox must:

- stop docker compose services for the sandbox
- stop sandbox supervisor if running
- stop sandbox daemon/workers if running
- release allocated ports
- remove stale locks and pid files
- preserve sandbox state consistency

The main runtime must never be impacted.

## Cleanup behavior

Deleting a sandbox must:

- stop the sandbox first if still running
- remove sandbox runtime artifacts safely
- remove sandbox worktree safely
- remove compose resources associated with the sandbox

Optional:

- preserve logs/state artifacts before deletion

## Lifecycle API endpoints

Add minimal lifecycle endpoints:

- POST /sandboxes/{id}/stop
- POST /sandboxes/{id}/restart
- POST /sandboxes/{id}/refresh
- DELETE /sandboxes/{id}

## Dashboard integration

Expose:

- running/stopped state
- ports
- runtime root
- uptime if available

Add lifecycle actions in the dashboard:

- stop
- restart
- refresh
- delete

## Tests

Add tests for:

- stop lifecycle
- restart lifecycle
- cleanup/delete
- port release
- stale lock cleanup
- concurrent sandbox safety

---

# Excluded

Do NOT implement in this ticket:

- generic runtime topology model
- sandbox-profile.yml
- component DAG/orchestration
- component health polling
- generic component abstractions
- distributed orchestration
- Kubernetes/cloud support
- AI auto-healing loops

These should be handled in later dedicated tickets.

---

# Acceptance criteria

- sandbox can be stopped safely
- sandbox can be restarted safely
- sandbox can be deleted safely
- ports are released correctly after stop/delete
- stale locks and pid files are cleaned safely
- dashboard lifecycle actions work
- main runtime is never affected
- concurrent sandboxes remain isolated