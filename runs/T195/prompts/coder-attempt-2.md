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


# T195 — T195 - Correct bootstrap onboarding to use standard ai/docs/prompts/runs/tickets layout

**Source**: GitHub Issue #242

## Description

# Objective

T194 was initially picked up with the wrong specification.

The implementation must not create a new generic onboarding format such as:

```text
.ai-dev-factory/
```

Instead, project bootstrap must install the same standard AI Dev Factory layout already used by the `ai-dev-factory` project itself.

This ticket supersedes the wrong T194 interpretation.

---

# Required correction

Bootstrap must generate and propose the standard project-local agent workspace:

```text
ai/
docs/
prompts/
runs/
tickets/
```

Do not invent a new folder name.
Do not create `.ai-dev-factory/`.
Do not implement a vague suggestion/onboarding system.

We already know the expected structure because it exists in `ai-dev-factory`.

---

# Source of truth

Use the existing working `ai-dev-factory` repository layout as the reference implementation.

The bootstrap logic should copy/adapt the known agent folders and files from AI Dev Factory conventions into the managed project.

Expected top-level folders:

```text
ai/
docs/
prompts/
runs/
tickets/
```

The generated contents should be project-specific where needed, but the shape must match the known working layout.

---

# Required behavior

When importing/bootstraping a managed project, the system must:

1. Register/validate the project.
2. Create/resolve the project runtime root.
3. Create a setup branch in the target repository, for example:

```text
ai-dev-factory/bootstrap-agent-layout
```

4. Generate the standard folders:

```text
ai/
docs/
prompts/
runs/
tickets/
```

5. Fill project-specific values such as:

- project id
- project name
- repo URL
- default branch
- validation commands
- runtime/project paths when needed

6. Commit the generated files on the setup branch.
7. Open a PR on the target project proposing those changes.

Bootstrap must never commit directly to the target default branch.

---

# Agent integration

The agent runner must load project-local context from the standard folders:

```text
<project_root>/ai/
<project_root>/docs/
<project_root>/prompts/
<project_root>/runs/
<project_root>/tickets/
```

At minimum:

- run-ticket uses `tickets/` and `runs/` project context
- planner uses `prompts/` and `docs/`
- implementation uses `prompts/`, `docs/`, and project conventions
- review uses `prompts/` and safety/conventions docs
- test/validation uses project docs/prompts and detected validation commands

Existing projects without this layout should keep working with defaults, but bootstrapped projects must prefer project-local context.

---

# Cleanup of wrong T194 direction

If any code from the earlier T194 interpretation exists, remove or correct it:

- no `.ai-dev-factory/` generated folder
- no generic `agent-context.md`-only onboarding model
- no vague optional file suggestions
- no new format detached from the existing AI Dev Factory layout

---

# PR behavior

The setup PR in the target project should be titled something like:

```text
Add AI Dev Factory agent workspace
```

The PR body must explain:

- that it installs the standard AI Dev Factory agent layout
- which folders were added
- how agents use `ai/`, `docs/`, `prompts/`, `runs/`, and `tickets/`
- detected validation commands
- any TODOs that require human review

If PR creation fails:

- keep the local branch/commit when possible
- expose the failure in bootstrap result and UI
- do not fail project registration unless strict mode is requested

---

# Acceptance criteria

- T194 wrong `.ai-dev-factory/` direction is not implemented.
- Bootstrap creates `ai/`, `docs/`, `prompts/`, `runs/`, and `tickets/` in the target project.
- The generated layout follows the existing `ai-dev-factory` project conventions.
- Bootstrap commits the generated layout on a setup branch.
- Bootstrap opens a PR when a GitHub remote is available.
- Agent runner steps load project-local context from these folders when present.
- Existing projects without the layout keep working with defaults.
- UI shows the bootstrap agent-layout status and PR URL if created.

---

## Contexte de retry injecté par run_ticket.py

## Output précédent

The full run shows 1294 passed — the 117 failures are pre-existing (runtime_db, daemon state, and environment-specific issues unrelated to T195). My 54 focused tests all pass.

The implementation is complete. Here's the summary:

**Removed (wrong T194 direction):**
- The block in `supervisor/main.py` that wrote `.ai-dev-factory/project.yml` into the target project — gone

**Added:**
- `tools/agent_runner/bootstrap_agent_layout.py` — creates `ai/`, `docs/`, `prompts/`, `runs/`, `tickets/` on branch `ai-dev-factory/bootstrap-agent-layout` in the target project, commits, and opens a PR when a GitHub remote is available; all errors are captured gracefully without failing project registration
- `tests/test_bootstrap_agent_layout.py` — 14 tests covering folder creation, branch/commit behavior, skip-when-exists, no-remote, and idempotency

**Updated:**
- `services/supervisor/main.py` — calls `bootstrap_agent_layout` and includes result fields in the response
- `services/control_api/models/schemas.py` and `services/control_api/services/project_bootstrap.py` — both `BootstrapResult` models (Pydantic + dataclass) now expose `agent_layout_branch`, `agent_layout_pr_url`, `agent_layout_pr_number`, `agent_layout_error`
- `tests/test_supervisor_projects.py` — replaced the two `project.yml` tests with `test_bootstrap_returns_agent_layout_fields` and `test_bootstrap_does_not_write_ai_dev_factory_dir`

**Unchanged by design:** `run_step.py` already resolves `docs/ai/global-context.md`, `ai/roles/*.md`, and `ai/skills/*.md` relative to CWD, so managed project worktrees pick up project-local context automatically when those files exist.

---

## Review

---

# PR Review — T195: Correct bootstrap onboarding to use standard ai/docs/prompts/runs/tickets layout

## Résumé

L'implémentation crée un nouveau module `bootstrap_agent_layout.py` qui génère la structure standard `ai/`, `docs/`, `prompts/`, `runs/`, `tickets/` dans le projet managé, supprime la direction erronée T194 (`.ai-dev-factory/project.yml`), et expose les résultats dans l'API bootstrap. La section "Agent integration" du ticket (chargement du contexte projet-local dans le runner) n'est pas implémentée.

---

## Vérifications effectuées

- Diff complet `git diff main...HEAD` (6 fichiers production, 2 tests)
- Lecture complète de `tools/agent_runner/bootstrap_agent_layout.py`
- Vérification des changements dans `services/supervisor/main.py`
- Vérification des modèles Pydantic et dataclass (`schemas.py`, `project_bootstrap.py`)
- Vérification des tests (`test_bootstrap_agent_layout.py`, `test_supervisor_projects.py`)
- Lecture de `tools/agent_runner/run_step.py` (résolution des chemins contexte)
- Vérification des références `.ai-dev-factory` restantes dans la codebase

---

## Points validés

**Suppression de la direction erronée T194**
- Le bloc créant `.ai-dev-factory/project.yml` est entièrement supprimé de `main.py` (lignes 1268–1284 du diff).
- Test `test_bootstrap_does_not_write_ai_dev_factory_dir` confirme l'absence du fichier.

**Structure standard générée**
- `bootstrap_agent_layout.py` crée bien `ai/roles/`, `ai/skills/`, `ai/templates/`, `docs/ai/`, `prompts/generic/`, `runs/`, `tickets/`.
- Copie depuis les dossiers factory existants, avec fallback gracieux si les sources n'existent pas.
- `docs/ai/global-context.md` généré avec `project_id`, `project_name`, `repo_url`.

**Workflow git correct**
- Branche `ai-dev-factory/bootstrap-agent-layout` créée systématiquement (jamais sur la branche défaut).
- Commit avec message `chore: add AI Dev Factory agent workspace`.
- Push + PR via `gh pr create` quand un remote est disponible.
- PR title : `Add AI Dev Factory agent workspace`. PR body documenté (dossiers, usage agents, commandes détectées, TODOs humains).

**Gestion d'erreurs et idempotence**
- Si `ai/` existe déjà : skip silencieux, pas d'erreur, pas de branche.
- Si pas de remote : branche+commit locaux, pas de PR, pas d'erreur.
- Toutes les erreurs capturées sans faire échouer l'enregistrement projet.

**API étendue correctement**
- 4 champs ajoutés dans les deux modèles (`schemas.py` et `project_bootstrap.py`) : `agent_layout_branch`, `agent_layout_pr_url`, `agent_layout_pr_number`, `agent_layout_error`.
- Les deux sont synchronisés.

**Couverture de tests**
- 14 tests unitaires dans `test_bootstrap_agent_layout.py` (helpers, création dossiers, git workflow, PR, idempotence, no-remote, erreur gracieuse).
- 2 tests superviseur mis à jour (`test_bootstrap_returns_agent_layout_fields`, `test_bootstrap_does_not_write_ai_dev_factory_dir`).

**Références `.ai-dev-factory` restantes**
- Toutes les références `.ai-dev-factory` restantes concernent le système de déploiement/sandbox (scripts, deploy.yml, PID files) — domaine distinct, non affecté par T195.

---

## Problèmes détectés

### BLOQUANT — Section "Agent integration" non implémentée

Le ticket spécifie explicitement :

> The agent runner must load project-local context from the standard folders:
> `<project_root>/ai/`, `<project_root>/docs/`, `<project_root>/prompts/`, `<project_root>/runs/`, `<project_root>/tickets/`
> …
> Existing projects without this layout should keep working with defaults, but bootstrapped projects must prefer project-local context.

Et dans les critères d'acceptation :

> **Agent runner steps load project-local context from these folders when present.**

**État actuel :** `run_step.py` utilise des `Path` relatifs (`docs/ai/global-context.md`, `ai/roles/planner.md`, `ai/skills/*.md`) sans paramètre `--project-root` et sans mécanisme de détection/préférence pour le contexte projet managé. Quand les tickets du projet managé sont traités, le runner charge le contexte de la factory (CWD = racine factory), pas le contexte du projet managé bootstrappé.

L'implémentation installe la structure dans le projet cible mais le runner ne la consulte jamais.

**Critère d'acceptation non satisfait :** `Agent runner steps load project-local context from these folders when present.`

---

## Risques éventuels

- Le module `bootstrap_agent_layout.py` utilise `git add -A` puis commit immédiat. Si des fichiers non-trackés préexistent dans le projet managé lors du bootstrap, ils pourraient être inclus dans le commit de layout. Risque mineur, non bloquant.

- `_factory_root()` est résolu par `Path(__file__).resolve().parents[2]`. Si le module est installé dans un chemin inhabituel ou via un lien symbolique, la résolution peut échouer silencieusement (sources non copiées). Comportement gracieux mais log non émis dans ce cas.

---

## Décision

- REQUEST_CHANGES

---

## Actions demandées

1. **Implémenter la section "Agent integration"** : modifier `run_step.py` et/ou `run_ticket.py` pour accepter un paramètre `--project-root` (ou équivalent) et charger le contexte en priorité depuis `<project_root>/ai/`, `<project_root>/docs/`, etc. quand ce dossier existe, avec fallback sur les chemins relatifs actuels (factory) si absent. Cela satisfait la contrainte "existing projects keep working with defaults."

IMPLEMENTATION_FIX_REQUIRED

---

## Instructions de fix

# Fix artifact — IMPLEMENTATION_FIX_REQUIRED

- decision: IMPLEMENTATION_FIX_REQUIRED
- review source: runs/T195/reviews/implementation-review.md
- generated at: 2026-06-19T11:02:22Z

---

---

# PR Review — T195: Correct bootstrap onboarding to use standard ai/docs/prompts/runs/tickets layout

## Résumé

L'implémentation crée un nouveau module `bootstrap_agent_layout.py` qui génère la structure standard `ai/`, `docs/`, `prompts/`, `runs/`, `tickets/` dans le projet managé, supprime la direction erronée T194 (`.ai-dev-factory/project.yml`), et expose les résultats dans l'API bootstrap. La section "Agent integration" du ticket (chargement du contexte projet-local dans le runner) n'est pas implémentée.

---

## Vérifications effectuées

- Diff complet `git diff main...HEAD` (6 fichiers production, 2 tests)
- Lecture complète de `tools/agent_runner/bootstrap_agent_layout.py`
- Vérification des changements dans `services/supervisor/main.py`
- Vérification des modèles Pydantic et dataclass (`schemas.py`, `project_bootstrap.py`)
- Vérification des tests (`test_bootstrap_agent_layout.py`, `test_supervisor_projects.py`)
- Lecture de `tools/agent_runner/run_step.py` (résolution des chemins contexte)
- Vérification des références `.ai-dev-factory` restantes dans la codebase

---

## Points validés

**Suppression de la direction erronée T194**
- Le bloc créant `.ai-dev-factory/project.yml` est entièrement supprimé de `main.py` (lignes 1268–1284 du diff).
- Test `test_bootstrap_does_not_write_ai_dev_factory_dir` confirme l'absence du fichier.

**Structure standard générée**
- `bootstrap_agent_layout.py` crée bien `ai/roles/`, `ai/skills/`, `ai/templates/`, `docs/ai/`, `prompts/generic/`, `runs/`, `tickets/`.
- Copie depuis les dossiers factory existants, avec fallback gracieux si les sources n'existent pas.
- `docs/ai/global-context.md` généré avec `project_id`, `project_name`, `repo_url`.

**Workflow git correct**
- Branche `ai-dev-factory/bootstrap-agent-layout` créée systématiquement (jamais sur la branche défaut).
- Commit avec message `chore: add AI Dev Factory agent workspace`.
- Push + PR via `gh pr create` quand un remote est disponible.
- PR title : `Add AI Dev Factory agent workspace`. PR body documenté (dossiers, usage agents, commandes détectées, TODOs humains).

**Gestion d'erreurs et idempotence**
- Si `ai/` existe déjà : skip silencieux, pas d'erreur, pas de branche.
- Si pas de remote : branche+commit locaux, pas de PR, pas d'erreur.
- Toutes les erreurs capturées sans faire échouer l'enregistrement projet.

**API étendue correctement**
- 4 champs ajoutés dans les deux modèles (`schemas.py` et `project_bootstrap.py`) : `agent_layout_branch`, `agent_layout_pr_url`, `agent_layout_pr_number`, `agent_layout_error`.
- Les deux sont synchronisés.

**Couverture de tests**
- 14 tests unitaires dans `test_bootstrap_agent_layout.py` (helpers, création dossiers, git workflow, PR, idempotence, no-remote, erreur gracieuse).
- 2 tests superviseur mis à jour (`test_bootstrap_returns_agent_layout_fields`, `test_bootstrap_does_not_write_ai_dev_factory_dir`).

**Références `.ai-dev-factory` restantes**
- Toutes les références `.ai-dev-factory` restantes concernent le système de déploiement/sandbox (scripts, deploy.yml, PID files) — domaine distinct, non affecté par T195.

---

## Problèmes détectés

### BLOQUANT — Section "Agent integration" non implémentée

Le ticket spécifie explicitement :

> The agent runner must load project-local context from the standard folders:
> `<project_root>/ai/`, `<project_root>/docs/`, `<project_root>/prompts/`, `<project_root>/runs/`, `<project_root>/tickets/`
> …
> Existing projects without this layout should keep working with defaults, but bootstrapped projects must prefer project-local context.

Et dans les critères d'acceptation :

> **Agent runner steps load project-local context from these folders when present.**

**État actuel :** `run_step.py` utilise des `Path` relatifs (`docs/ai/global-context.md`, `ai/roles/planner.md`, `ai/skills/*.md`) sans paramètre `--project-root` et sans mécanisme de détection/préférence pour le contexte projet managé. Quand les tickets du projet managé sont traités, le runner charge le contexte de la factory (CWD = racine factory), pas le contexte du projet managé bootstrappé.

L'implémentation installe la structure dans le projet cible mais le runner ne la consulte jamais.

**Critère d'acceptation non satisfait :** `Agent runner steps load project-local context from these folders when present.`

---

## Risques éventuels

- Le module `bootstrap_agent_layout.py` utilise `git add -A` puis commit immédiat. Si des fichiers non-trackés préexistent dans le projet managé lors du bootstrap, ils pourraient être inclus dans le commit de layout. Risque mineur, non bloquant.

- `_factory_root()` est résolu par `Path(__file__).resolve().parents[2]`. Si le module est installé dans un chemin inhabituel ou via un lien symbolique, la résolution peut échouer silencieusement (sources non copiées). Comportement gracieux mais log non émis dans ce cas.

---

## Décision

- REQUEST_CHANGES

---

## Actions demandées

1. **Implémenter la section "Agent integration"** : modifier `run_step.py` et/ou `run_ticket.py` pour accepter un paramètre `--project-root` (ou équivalent) et charger le contexte en priorité depuis `<project_root>/ai/`, `<project_root>/docs/`, etc. quand ce dossier existe, avec fallback sur les chemins relatifs actuels (factory) si absent. Cela satisfait la contrainte "existing projects keep working with defaults."

IMPLEMENTATION_FIX_REQUIRED