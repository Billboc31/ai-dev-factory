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


# T026 — T026 — Continuous checkpoint publishing and PR lifecycle

**Source**: GitHub Issue #21

## Description

# T026 — Continuous checkpoint publishing and PR lifecycle

## Contexte

Le daemon peut déjà orchestrer les runs locaux, mais pour un usage à distance il ne suffit pas de publier à `TEST_COMPLETE`.

Après chaque step réussi, il faut publier un checkpoint pour que :

- le workspace reste clean
- le step suivant ne soit pas bloqué par les guards Git
- les artefacts soient visibles depuis GitHub
- un reviewer externe puisse lire le plan, le code, les reviews et les logs

Architecture cible :

```text
step success
→ transition workflow
→ commit checkpoint --include-code
→ push branch
→ daemon continue
```

Puis à la fin :

```text
TEST_COMPLETE
→ final checkpoint
→ push
→ create/update PR
→ human merge
→ close source issue
```

## Objectif

Ajouter une publication continue des checkpoints et un lifecycle PR minimal.

## Inclus

### 1. Continuous checkpoint publishing

Après chaque step réussi et transition workflow, le daemon déclenche un commit/push du checkpoint du ticket.

États typiques publiés :

```text
PLAN_REVIEW_NEEDED
IMPLEMENTATION_REVIEW_NEEDED
IMPLEMENTATION_APPROVED
TEST_COMPLETE
PLAN_FIX_REQUIRED
IMPLEMENTATION_FIX_REQUIRED
```

### 2. Remote visibility

Après chaque checkpoint, GitHub doit contenir les artefacts runtime et les fichiers modifiés :

```text
runs/TXXX/plan.md
runs/TXXX/implementation-output.md
runs/TXXX/reviews/*
runs/TXXX/tests/*
runs/TXXX/runtime.log
runs/TXXX/prompts/*
code/tests/docs modifiés
```

### 3. PR lifecycle à TEST_COMPLETE

Quand le ticket atteint `TEST_COMPLETE`, le daemon doit :

- vérifier que le checkpoint final est publié
- créer une PR si absente
- réutiliser ou mettre à jour la PR si elle existe
- lier la PR à l’issue source
- écrire une description utile

### 4. Issue closing après merge

Après merge manuel de la PR, le daemon doit :

- détecter la PR merged
- fermer l’issue source
- retirer le label `ai-ready`
- logguer l’action

### 5. Guardrails

- aucun merge automatique
- aucune PR avant `TEST_COMPLETE`
- aucune mauvaise branche poussée
- respect de `state.json`
- logs explicites

## Hors scope

- auto merge
- slash commands
- review GitHub automatique
- model routing
- UI web
- distributed workers

## Critères d’acceptation

- checkpoint commit/push après chaque step réussi
- pas de commit/push si step échoue
- workspace clean entre les étapes
- artefacts visibles à distance
- PR créée ou mise à jour à `TEST_COMPLETE`
- issue source liée à la PR
- issue fermée après merge détecté
- label `ai-ready` retiré après completion
- aucun merge automatique
- workflow existant compatible

## Fichiers potentiellement modifiés

```text
tools/agent_runner/run_daemon.py
tools/agent_runner/run_issue_intake.py
tests/
README.md
```

---

## Contexte de retry injecté par run_ticket.py

## Output précédent

All 217 tests pass. Here's a summary of what was implemented:

**Files modified:**

- `tools/agent_runner/run_issue_intake.py` — `write_state_json()` now accepts `issue_number` and writes it to `state.json` so the daemon can link PR → issue.

- `tools/agent_runner/run_ticket.py` — `auto_run()` gains an `include_code` parameter that's forwarded to `commit_ticket()`; new `--auto-include-code` CLI flag wires it up.

- `tools/agent_runner/run_daemon.py` — the main additions:
  - `_load_state_json()` / `_save_state_json()` — atomic read/write of state.json
  - `create_or_update_pr()` — finds or creates a PR via `gh pr list/create/edit`, stores `pr_number` in state
  - `check_and_close_issue()` — detects merged PR via `gh pr view`, closes issue and removes `ai-ready` label
  - `handle_test_complete()` — orchestrator called from `run_once()` for `TEST_COMPLETE` state
  - `launch_ticket()` — now accepts `auto_commit`, `auto_push`, `auto_include_code` and passes them to `run_ticket.py`
  - `run_once()` — handles `TEST_COMPLETE` separately (PR lifecycle) before the human-gate fallthrough; new flags forwarded to `launch_ticket()`
  - CLI: three new daemon flags `--auto-commit`, `--auto-push`, `--auto-include-code`

- `tests/test_run_daemon.py` — fixed `test_run_once_calls_launch_for_auto_runnable_state` to match the new `launch_ticket` kwargs.

**New test files:**
- `tests/test_daemon_checkpoint.py` — 5 tests covering the auto-commit/push/include-code flags
- `tests/test_daemon_pr_lifecycle.py` — 10 tests covering `_load/save_state_json`, `create_or_update_pr`, `check_and_close_issue`, `handle_test_complete`

---

## Review

La review est écrite dans `runs/T026/reviews/implementation-review.md`.

---

**Verdict : IMPLEMENTATION_FIX_REQUIRED**

Deux problèmes détectés :

**P1 — Bloquant : polling infini post-merge**

`handle_test_complete()` est appelé à chaque cycle du daemon pour tout ticket en `TEST_COMPLETE`, sans aucune condition de sortie anticipée. Après merge de la PR :
- `gh pr view` + `gh issue close` + `gh issue edit --remove-label` sont appelés à chaque cycle (toutes les 30s par défaut)
- Les logs affichent "issue #N closed" en boucle et des erreurs de label inexistant
- À 30s d'intervalle sur 24h : ~8640 appels inutiles par ticket

Fix minimal : persister `issue_closed: true` dans `state.json` après fermeture, et vérifier ce flag en entrée de `check_and_close_issue()`. Même logique avec `pr_synced` pour éviter les `gh pr edit` répétés avec un body identique.

**P2 — Mineur : gates PR incorrectes**

`_pr_body()` affiche `- [ ] PLAN_APPROVED` et `- [ ] IMPLEMENTATION_APPROVED` alors que les deux sont déjà validés à `TEST_COMPLETE`. Ces deux cases devraient être pré-cochées.

Tout le reste de l'implémentation est correct : wiring des flags, préservation des champs dans `state.json`, guardrails, atomicité des écritures, et coverage des tests.

---

## Instructions de fix

# Implementation fix 1 — T026

## Décision

IMPLEMENTATION_FIX_REQUIRED

## Problèmes à corriger

### P1 — Bloquant : polling infini post-merge

`handle_test_complete()` est appelé à chaque cycle du daemon pour tout ticket en `TEST_COMPLETE`, sans condition de sortie anticipée.

Après merge de la PR :
- `gh pr view`
- `gh issue close`
- `gh issue edit --remove-label`

peuvent être appelés à chaque cycle.

Fix attendu :
- persister `issue_closed: true` dans `state.json` après fermeture de l’issue
- vérifier ce flag au début de `check_and_close_issue()`
- ne pas rappeler GitHub si l’issue est déjà fermée
- ajouter tests dédiés

Amélioration recommandée :
- persister un flag ou un marqueur `pr_synced` / `pr_body_hash` pour éviter les `gh pr edit` répétés avec un body identique

### P2 — Mineur : gates PR incorrectes

`_pr_body()` affiche `PLAN_APPROVED` et `IMPLEMENTATION_APPROVED` non cochés alors qu’à `TEST_COMPLETE`, ces gates sont validées.

Fix attendu :
- cocher ces gates dans le body PR à `TEST_COMPLETE`
- ajouter ou adapter le test correspondant

## Contraintes

- pas de merge automatique
- pas de changement de scope
- conserver `run_ticket.py` comme moteur workflow
- conserver les tests existants verts