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



# T143 — T143 — Conflict resolver agent for PR branch rebases

**Source**: GitHub Issue #134

## Description

Goal: add a conflict resolver agent that detects PR/branch conflicts, resolves them in the ticket worktree with full ticket context, and updates the PR safely.

Context:
As the system starts coding multiple tickets in parallel, PR branches will regularly conflict with main. Conflict resolution must be handled with context, not by blindly choosing ours/theirs.

Target workflow:
- PR or ticket branch conflict detected
- ticket state moves to CONFLICT_RESOLUTION_NEEDED
- conflict resolver agent runs in the existing ticket worktree
- agent rebases the ticket branch on latest main
- agent resolves conflicts using ticket context
- tests run
- branch is pushed with force-with-lease
- ticket state moves to CONFLICT_RESOLVED_REVIEW_NEEDED
- dashboard shows resolver summary and review gate

Scope:
- add conflict detection for PR branches or failed branch sync/rebase
- add new workflow states:
  - CONFLICT_RESOLUTION_NEEDED
  - CONFLICT_RESOLVING
  - CONFLICT_RESOLVED_REVIEW_NEEDED
  - CONFLICT_RESOLUTION_FAILED
- run resolver inside the ticket worktree, not main
- collect context for the resolver:
  - ticket.md
  - plan.md
  - reviews
  - fixes
  - PR diff
  - merge-base diff
  - conflicted files
  - latest main changes
- compose a dedicated resolver prompt
- resolve conflicts by editing files in the ticket worktree
- run relevant tests after resolution
- commit resolution artifacts and code changes
- push branch with force-with-lease
- dashboard must display:
  - conflicted files
  - resolver status
  - resolver summary
  - tests result
  - review gate after resolution

Safety rules:
- do not resolve conflicts in main
- do not reset the branch
- do not overwrite main behavior blindly
- preserve both ticket intent and latest main behavior when possible
- do not auto-merge after resolution
- require human review after conflict resolution

Out of scope:
- resolving production deployment conflicts
- automatic merge to main
- multi-branch global planning
- semantic dependency graph construction

Acceptance:
- a conflicting ticket branch can enter CONFLICT_RESOLUTION_NEEDED
- resolver runs in the ticket worktree
- resolver receives ticket context and conflicted file list
- resolved branch is pushed safely
- dashboard exposes conflict status and summary
- human review is required before continuing
- failures end in CONFLICT_RESOLUTION_FAILED with logs

---

## Contexte de retry injecté par run_ticket.py

## Output précédent

Here is the plan:

---

## Objective

Add a conflict resolver agent workflow that detects when a PR branch conflicts with main, collects full ticket context, rebases in the existing ticket worktree, resolves conflicts via an AI agent, runs tests, and pushes the resolved branch with `--force-with-lease` — gated by mandatory human review before the ticket workflow resumes.

## Included

### 1. New workflow states — `tools/agent_runner/run_ticket.py`

- Add to `VALID_STATES`: `CONFLICT_RESOLUTION_NEEDED`, `CONFLICT_RESOLVING`, `CONFLICT_RESOLVED_REVIEW_NEEDED`, `CONFLICT_RESOLUTION_FAILED`.
- Add to `TRANSITIONS`:
  - `CONFLICT_RESOLUTION_NEEDED` → `("conflict-resolver", True, ["CONFLICT_RESOLVED_REVIEW_NEEDED", "CONFLICT_RESOLUTION_FAILED"])`
  - `CONFLICT_RESOLVED_REVIEW_NEEDED` → `("review", False, ["PRE_CONFLICT", "CONFLICT_RESOLUTION_FAILED"])`
  - `CONFLICT_RESOLUTION_FAILED` → `None` (terminal)
- Add to `REVIEW_DECISION_KEYWORDS`: `CONFLICT_RESOLVED_REVIEW_NEEDED → {"approve": "PRE_CONFLICT", "fix": "CONFLICT_RESOLUTION_FAILED"}`
- Add sentinel resolution in transition logic: when the computed next state is `"PRE_CONFLICT"`, read `state["pre_conflict_state"]` from `state.json` and use that as the actual target.
- Add `"conflict-resolver": "conflict/resolution.md"` to `DEFAULT_OUTPUTS`.

### 2. Conflict detection — `tools/agent_runner/run_daemon.py`

- `detect_pr_conflict(ticket_id, run_dir, repo)`: calls `gh pr view <pr_number> --json mergeable`, returns `True` if `"CONFLICTING"`.
- `detect_rebase_conflict(ticket_id, worktree_path)`: attempts `git rebase --no-commit origin/main` in the ticket worktree, aborts on failure, returns `True` if conflicts found.
- Both checks integrated in the daemon polling loop for active (non-terminal, non-conflict) tickets that have a branch and PR number.
- On conflict: write `pre_conflict_state` to `state.json`, transition to `CONFLICT_RESOLUTION_NEEDED`.

### 3. New step type — `tools/agent_runner/run_step.py`

- Add `"conflict-resolver"` / alias `"conflict"` to `STEP_ALIASES`, `DEFAULT_OUTPUTS`, `STEP_ROLE_FILES`, `STEP_SKILL_FILES`.
- Add `"conflict"` to `RUN_SUBDIRS`.
- New function `collect_conflict_context(ticket_id, run_dir, repo_root, worktrees_dir)`: reads `ticket.md`, `plan.md`, `reviews/`, `fixes/`, and runs `gh pr diff`, `git diff $(git merge-base HEAD origin/main)`, `git diff --name-only --diff-filter=U`, `git log --oneline origin/main ^HEAD`; writes the assembled document to `runs/TXXX/conflict/context.md`.
- `collect_conflict_context` is called before spawning the agent.

### 4. `ai/roles/conflict-resolver.md` (new file)

- Mission, safety rules (no `reset --hard`, no blind `--ours`/`--theirs`, `--force-with-lease` only), and expected output format for `conflict/resolution.md`.

### 5. `prompts/generic/conflict-resolver.md` (new file)

- Assembles: global context, role, `git-discipline` + `workflow-discipline` skills, context document reference, output template, forbidden-phrase list.

### 6. Schema extension — `services/control_api/models/schemas.py`

- `TicketSummary`: add `conflict_status: str | None`, `conflicted_files: list[str] | None`, `conflict_summary: str | None`.

### 7. Artifact reader — `services/control_api/services/artifact_reader.py`

- `get_ticket()`: populate the three new fields from `state.json`, `conflict/context.md`, and `conflict/resolution.md`.
- `get_ticket_artifacts()`: include conflict directory files when present.

### 8. New API endpoints — `services/control_api/routes/tickets.py`

- `POST /{ticket_id}/approve-conflict-resolution`: reads `pre_conflict_state` and calls `checkpoint_transition` to it.
- `GET /{ticket_id}/conflict`: returns `conflict/resolution.md` as plain text.
- Both mirrored in the project-scoped router.

### 9. Dashboard frontend — `apps/dashboard/src/`

- Conflict badge on ticket cards in any conflict state.
- Conflict detail section: conflicted files list, resolver summary, test result, Approve / Mark-Failed buttons.
- Timeline renderer: four new states mapped to `TimelineStep` entries (`waiting_human` for review gate, `failed` for `CONFLICT_RESOLUTION_FAILED`).

### 10. Tests — `tests/test_conflict_resolver.py` (new file)

- New states in `VALID_STATES`, correct `TRANSITIONS`, `CONFLICT_RESOLUTION_FAILED` terminal, `PRE_CONFLICT` sentinel resolution, `collect_conflict_context` output shape, `detect_pr_conflict` mock, `--force-with-lease` push assertion.

## Excluded

- Resolving production deployment conflicts.
- Automatic merge to main after resolution.
- Multi-branch global planning or semantic dependency-graph construction.
- Memory update triggered by conflict resolution (normal memory workflow after `TEST_COMPLETE`).
- UI changes outside conflict-specific display.
- Conflict resolution for tickets before `PLAN_APPROVED`.

## Acceptance criteria

1. Four new states present in `VALID_STATES` in `run_ticket.py`.
2. Transitioning to `CONFLICT_RESOLUTION_NEEDED` persists the previous state as `pre_conflict_state` in `state.json`.
3. `run_ticket.py --auto` auto-launches the `conflict-resolver` step from `CONFLICT_RESOLUTION_NEEDED`.
4. `runs/TXXX/conflict/context.md` is created before the agent runs, containing ticket, plan, reviews, PR diff, conflicted files, and latest main delta.
5. Resolver agent produces `runs/TXXX/conflict/resolution.md` with per-file rationale and test outcome.
6. Push uses `git push --force-with-lease` (verified in tests).
7. Successful resolution → `CONFLICT_RESOLVED_REVIEW_NEEDED`; failure → `CONFLICT_RESOLUTION_FAILED`.
8. `POST approve-conflict-resolution` transitions the ticket back to `pre_conflict_state`.
9. `CONFLICT_RESOLUTION_FAILED` is terminal — no automatic retry.
10. Dashboard shows conflict badge, files, summary, and review gate buttons for all conflict-state tickets.
11. `tests/test_conflict_resolver.py` passes; no regressions in existing suite.

---

The plan is saved to `runs/T143/plan.md`. The two key design decisions worth noting: the `"PRE_CONFLICT"` sentinel in `REVIEW_DECISION_KEYWORDS` to dynamically resolve the resume state (avoids duplicating each possible pre-conflict state as a separate transition), and `detect_rebase_conflict` aborts cleanly after detection so the worktree is never left in a mid-rebase state before the resolver agent runs.

---

## Review

# Plan review — T143

Decision: PLAN_FIX_REQUIRED

The current T143 plan is too large and too risky for a first conflict-management implementation.

It combines:

- workflow state machine changes
- automatic conflict detection
- automatic rebases
- AI conflict resolution
- force-with-lease pushes
- dashboard changes
- API changes
- context orchestration
- review lifecycle changes

This should be split into smaller and safer runtime iterations.

The first implementation should focus on:

- conflict detection
- conflict workflow states
- dashboard visibility
- preserving ticket state

before introducing automatic AI-driven rebases and branch rewriting.

See `runs/T143/fixes/plan-fix-1.md`.

---

## Instructions de fix

# Plan fix — T143 V1

## New objective

Implement safe conflict detection and visibility for ticket branches and PRs.

The system should:

- detect conflicting ticket branches
- preserve workflow state before conflict
- expose conflict status in the dashboard
- expose conflicted files and metadata

The system must NOT automatically rewrite branches yet.

This ticket intentionally focuses on:

- workflow safety
- observability
- dashboard visibility
- conflict state transitions

before introducing AI-driven conflict resolution.

---

# Included

## Workflow states

Add:

- CONFLICT_RESOLUTION_NEEDED
- CONFLICT_RESOLUTION_FAILED

Persist:

- pre_conflict_state

in state.json.

## Conflict detection

Detect:

- PR merge conflicts (`gh pr view --json mergeable`)
- failed branch sync/rebase situations

Do NOT attempt automatic conflict resolution.

## Conflict metadata

Collect and persist:

- conflicted files
- PR number
- branch name
- detection timestamp
- previous workflow state

## Dashboard visibility

Expose in dashboard:

- conflict badge
- conflict status
- conflicted files
- previous workflow state
- manual action required

## API additions

Expose conflict state and metadata through ticket endpoints.

## Tests

Add tests for:

- conflict state transitions
- pre_conflict_state persistence
- conflict detection mocks
- dashboard serialization
- conflict metadata persistence

---

# Excluded

Do NOT implement in this ticket:

- AI conflict resolver agent
- automatic rebases
- branch rewriting
- force-with-lease pushes
- automatic conflict fixes
- automatic workflow resume
- approve-conflict-resolution endpoint
- automatic test execution after conflicts

These should be handled in a later dedicated resolver ticket.

---

# Acceptance criteria

- conflicting PRs or branches enter CONFLICT_RESOLUTION_NEEDED
- pre_conflict_state is persisted safely
- conflicted files are visible in the dashboard
- conflict metadata is exposed through the API
- no automatic branch rewriting occurs
- no automatic pushes occur
- manual review/action is required after conflict detection