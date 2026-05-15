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


# T101 — T101 — Runtime hardening: checkpoint, timeline mapping, ticket ids and PR ordering

**Source**: GitHub Issue #41

## Description

# T101 — Runtime hardening: checkpoint, timeline mapping, ticket ids and PR ordering

## Contexte

Les premiers runs réels du daemon ont validé la boucle complète :

```text
GitHub Issue
→ daemon polling
→ issue intake
→ branch
→ planner
→ human plan approval
→ coder
→ reviewer
→ tester
→ TEST_COMPLETE
→ PR auto
```

Mais plusieurs bugs de runtime/hardening sont apparus pendant T032/T033/T100.

Ce ticket vise à corriger les petits bugs bloquants découverts en usage réel.

---

## Bugs observés

### 1. Mauvais mapping timeline pour les étapes auto

Dans l’IHM, `IMPLEMENTATION_REVIEW_NEEDED` est affiché comme une pause humaine.

C’est faux.

Cet état signifie :

```text
coder terminé
→ reviewer doit tourner automatiquement
```

Le dashboard doit afficher le reviewer comme étape auto/pending/running, pas une attente utilisateur.

États attendus :

```text
PLAN_REVIEW_NEEDED = waiting human
IMPLEMENTATION_REVIEW_NEEDED = reviewer auto attendu
IMPLEMENTATION_FIX_REQUIRED = coder fix auto attendu
IMPLEMENTATION_APPROVED = tester auto attendu
TEST_COMPLETE = waiting human / final review
```

---

### 2. Mauvaise allocation automatique des ticket ids

Un ticket issu de l’issue T034 a été créé en `T100` au lieu de `T035`.

Le générateur de ticket id doit utiliser un parsing numérique robuste :

```text
next_id = max(existing numeric ticket ids) + 1
```

Il ne doit pas utiliser de tri lexicographique fragile.

Exemples à tester :

```text
T009 → next T010
T034 → next T035
T099 → next T100
T1, T10, T100 → next T101
```

Le ticket id doit rester cohérent entre :

```text
runs/TXXX/
branch ticket/TXXX-...
commits
push
PR
dashboard
issue intake registry
```

---

### 3. Pré-flight dirty tree trop strict après coder

Pendant T100, le daemon a classé les fichiers modifiés par le coder comme `unknown dirty files` :

```text
apps/dashboard/src/api/tickets.js
apps/dashboard/src/pages/TicketDetailPage.jsx
services/control_api/models/schemas.py
services/control_api/routes/tickets.py
services/control_api/services/artifact_reader.py
...
```

Mais ces fichiers sont dans le scope normal de code.

Quand l’état est `IMPLEMENTATION_REVIEW_NEEDED`, les fichiers modifiés dans `COMMIT_SCOPE` doivent être checkpointables automatiquement, pas bloquants.

Les vrais fichiers unknown doivent continuer à provoquer un abort sécurisé.

---

### 4. PR créée avant checkpoint/push final complet

Sur T100, le daemon a créé la PR après `TEST_COMPLETE`, mais sans garantir avant cela un checkpoint commit/push complet des derniers artefacts et changements de test.

Flux cible :

```text
tester success
→ write test-report.md
→ checkpoint commit --include-code
→ push
→ create/update PR
→ TEST_COMPLETE / waiting human
```

ou a minima :

```text
TEST_COMPLETE
→ checkpoint commit --include-code
→ push
→ create/update PR
```

Mais la PR ne doit pas être créée/considérée stable si le working tree local contient encore des artefacts persistants non commités.

---

### 5. Fichiers runtime à ignorer définitivement

S’assurer que les fichiers suivants sont ignorés et jamais trackés :

```gitignore
runs/daemon.log
runs/daemon.pid
runs/*/daemon.lock
runs/*/workflow-status.md
apps/dashboard/node_modules/
apps/dashboard/node_modules/.vite/
```

Ces fichiers ne doivent jamais bloquer le workflow Git.

---

## Objectif

Stabiliser le runtime daemon après les premiers tests end-to-end.

Le daemon doit pouvoir enchaîner :

```text
intake
→ plan
→ approval
→ code
→ review
→ tests
→ checkpoint
→ push
→ PR
```

sans intervention Git manuelle sauf merge/review humaine.

---

## Travail demandé

### 1. Corriger le mapping timeline

Mettre à jour la projection timeline/API/UI pour distinguer :

- états auto-runnable
- gates humaines
- étapes pending/running

Ne pas introduire de nouvelle state machine : la timeline reste une projection de `state.json`.

---

### 2. Corriger l’allocation de ticket id

Identifier la logique qui génère automatiquement le prochain `TXXX`.

Corriger avec un parsing numérique robuste.

Ajouter tests unitaires pour les cas avec gaps, ids non triés, `T099`, `T100`, etc.

---

### 3. Corriger la classification dirty tree

Mettre à jour la logique de pre-flight daemon :

- fichiers dans `COMMIT_SCOPE` → checkpointables
- artefacts `runs/TXXX/` persistants → checkpointables
- fichiers ignorés → ignorés
- fichiers inconnus hors scope → abort sécurisé

Ne jamais utiliser `git add .`.

---

### 4. Garantir checkpoint/push avant PR

Avant création ou update de PR :

1. checkpoint commit avec le scope canonique
2. push
3. vérifier working tree clean
4. seulement ensuite create/update PR

Réutiliser les scripts canoniques existants autant que possible.

---

### 5. Nettoyer `.gitignore`

Vérifier que les fichiers runtime identifiés sont bien ignorés.

S’ils sont déjà trackés, les retirer du tracking avec `git rm --cached`, sans supprimer les fichiers locaux utiles.

---

## Contraintes

- `run_ticket.py` reste le moteur workflow canonique
- pas de duplication de state machine dans l’API/UI
- pas de `git add .`
- pas d’auto-merge
- PR créée/updated uniquement après push stable
- conserver les gates humaines
- logs explicites pour chaque checkpoint/push/PR

---

## Critères d’acceptation

- `IMPLEMENTATION_REVIEW_NEEDED` n’est plus affiché comme pause humaine dans la timeline
- le prochain ticket après T034 est généré en T035, pas T100
- les fichiers code dans `COMMIT_SCOPE` sont auto-checkpointés au bon moment
- les vrais fichiers inconnus continuent à bloquer le daemon
- `TEST_COMPLETE` déclenche un checkpoint/push avant PR
- la PR est créée/updated uniquement après push stable
- les fichiers runtime ne polluent plus Git
- aucun `git add .`

---

## Contexte de retry injecté par run_ticket.py

## Output précédent

101/101 tests pass. All five bugs are implemented. Here's a summary:

---

## Summary

**7 files modified:**

### Bug 1 — Timeline mapping (`artifact_reader.py`, `test_ticket_timeline.py`)
- `IMPLEMENTATION_REVIEW_NEEDED`: `human_gate=True→False`, status `"waiting_human"→"running"`, `_STEP_AGENTS[4]=None→"reviewer"`
- `TEST_COMPLETE`: `human_gate=False→True` (merge is human)
- Updated 2 test assertions accordingly

### Bug 2 — Ticket ID edge cases (`test_daemon_issue_polling.py`)
- Added 7 new tests: T034→T035, T099→T100, lexicographic trap (T1/T10/T100→T101), gaps, reserved set

### Bug 3 — Dirty tree 3-tuple (`run_daemon.py`, `test_daemon_checkpoint.py`)
- Added `_CODE_SCOPE_PREFIXES` constant (mirrors `COMMIT_SCOPE` from `run_ticket.py`)
- `_classify_dirty_files()` now returns `(workflow_artifacts, code_scope_files, unknown_files)`
- `_ensure_clean_working_tree()` treats code-scope files as auto-checkpointable, not blocking
- Updated all 8 affected tests + added 2 new tests

### Bug 4 — Checkpoint before PR (`run_daemon.py`, `test_daemon_pr_lifecycle.py`)
- Added `_checkpoint_and_push_before_pr()` — commits with `--include-code`, pushes if something committed, non-blocking
- `handle_test_complete()` calls it before `create_or_update_pr()`
- Added 4 new tests (including call-order verification)

### Bug 5 — `.gitignore`
- Added: `runs/*/state.json.tmp`, `runs/*/retry-state.json`, `runs/*/retry-state.json.tmp`, `runs/.issue-intake.json.tmp`
- Removed: duplicate `apps/dashboard/node_modules/` and redundant `.vite/` entry

---

## Review

---

# PR Review — T101 Runtime Hardening

## Résumé

Implémentation solide sur 4 des 5 bugs. Un problème bloquant sur le Bug 4.

---

## Points validés

**Bug 1 — Timeline mapping** : `artifact_reader.py:151-156` corrige correctement tous les états. `IMPLEMENTATION_REVIEW_NEEDED` → `human_gate=False`, reviewer en "running". Tous les autres états correspondent au spec.

**Bug 2 — Ticket IDs** : `run_daemon.py:687-698` parse numériquement avec `re.match(r"T(\d+)$")`. Format zero-padé 3 digits. Tous les cas du ticket couverts par les tests : T034→T035, T099→T100, T001/T010/T100→T101 (piège lexicographique évité), gaps.

**Bug 3 — Dirty tree** : `run_daemon.py:235-331` classifie en 3 buckets corrects. Les fichiers coder (services/, apps/) tombent dans `code_scope_files` (auto-checkpointés). Les vrais inconnus bloquent toujours. Aucun `git add .`.

**Bug 5 — .gitignore** : tmp files ajoutés. Suppression de `apps/dashboard/node_modules/.vite/` acceptable — couvert par le dossier parent.

---

## Problème bloquant

**`_checkpoint_and_push_before_pr` est non-bloquante** (`run_daemon.py:539-574`).

La fonction retourne `None` dans tous les cas. `handle_test_complete` appelle `create_or_update_pr` **inconditionnellement**, même si push a échoué :

```python
def handle_test_complete(...):
    _checkpoint_and_push_before_pr(ticket_id)   # None toujours
    create_or_update_pr(...)                     # appelé même si push échoué
```

**Impact** : si `git push` échoue, la PR est créée sur un remote branch incomplet (test-report.md, state.json final absents). C'est exactement le bug T100 que ce ticket vise à corriger.

**Critère violé** : "la PR est créée/updated uniquement après push stable"

**Correction minimale demandée** (`run_daemon.py:539-574`) :

```python
def _checkpoint_and_push_before_pr(ticket_id: str) -> bool:
    # ... mêmes logs
    if commit_result.returncode not in (0, 1):
        return False
    if commit_result.returncode == 0:
        push_result = ...
        if push_result.returncode != 0:
            return False
    return True

def handle_test_complete(...):
    if not _checkpoint_and_push_before_pr(ticket_id):
        _log(f"{ticket_id}: pre-PR push failed — PR skipped")
        return
    create_or_update_pr(...)
    check_and_close_issue(...)
```

Ajouter un test couvrant le cas push échoué → PR non créée dans `test_daemon_pr_lifecycle.py`.

---

## Risques mineurs

- `_CODE_SCOPE_PREFIXES` (`run_daemon.py:236`) duplique `COMMIT_SCOPE` de `run_ticket.py` — drift possible si l'un évolue sans l'autre.
- `IMPLEMENTATION_APPROVED` affiche fix_loop comme "skipped" même si un fix loop a tourné — cosmétique, état transitoire.

---

IMPLEMENTATION_FIX_REQUIRED

---

## Instructions de fix

# Fix artifact — IMPLEMENTATION_FIX_REQUIRED

- decision: IMPLEMENTATION_FIX_REQUIRED
- review source: runs/T101/reviews/implementation-review.md
- generated at: 2026-05-15T17:21:19Z

---

---

# PR Review — T101 Runtime Hardening

## Résumé

Implémentation solide sur 4 des 5 bugs. Un problème bloquant sur le Bug 4.

---

## Points validés

**Bug 1 — Timeline mapping** : `artifact_reader.py:151-156` corrige correctement tous les états. `IMPLEMENTATION_REVIEW_NEEDED` → `human_gate=False`, reviewer en "running". Tous les autres états correspondent au spec.

**Bug 2 — Ticket IDs** : `run_daemon.py:687-698` parse numériquement avec `re.match(r"T(\d+)$")`. Format zero-padé 3 digits. Tous les cas du ticket couverts par les tests : T034→T035, T099→T100, T001/T010/T100→T101 (piège lexicographique évité), gaps.

**Bug 3 — Dirty tree** : `run_daemon.py:235-331` classifie en 3 buckets corrects. Les fichiers coder (services/, apps/) tombent dans `code_scope_files` (auto-checkpointés). Les vrais inconnus bloquent toujours. Aucun `git add .`.

**Bug 5 — .gitignore** : tmp files ajoutés. Suppression de `apps/dashboard/node_modules/.vite/` acceptable — couvert par le dossier parent.

---

## Problème bloquant

**`_checkpoint_and_push_before_pr` est non-bloquante** (`run_daemon.py:539-574`).

La fonction retourne `None` dans tous les cas. `handle_test_complete` appelle `create_or_update_pr` **inconditionnellement**, même si push a échoué :

```python
def handle_test_complete(...):
    _checkpoint_and_push_before_pr(ticket_id)   # None toujours
    create_or_update_pr(...)                     # appelé même si push échoué
```

**Impact** : si `git push` échoue, la PR est créée sur un remote branch incomplet (test-report.md, state.json final absents). C'est exactement le bug T100 que ce ticket vise à corriger.

**Critère violé** : "la PR est créée/updated uniquement après push stable"

**Correction minimale demandée** (`run_daemon.py:539-574`) :

```python
def _checkpoint_and_push_before_pr(ticket_id: str) -> bool:
    # ... mêmes logs
    if commit_result.returncode not in (0, 1):
        return False
    if commit_result.returncode == 0:
        push_result = ...
        if push_result.returncode != 0:
            return False
    return True

def handle_test_complete(...):
    if not _checkpoint_and_push_before_pr(ticket_id):
        _log(f"{ticket_id}: pre-PR push failed — PR skipped")
        return
    create_or_update_pr(...)
    check_and_close_issue(...)
```

Ajouter un test couvrant le cas push échoué → PR non créée dans `test_daemon_pr_lifecycle.py`.

---

## Risques mineurs

- `_CODE_SCOPE_PREFIXES` (`run_daemon.py:236`) duplique `COMMIT_SCOPE` de `run_ticket.py` — drift possible si l'un évolue sans l'autre.
- `IMPLEMENTATION_APPROVED` affiche fix_loop comme "skipped" même si un fix loop a tourné — cosmétique, état transitoire.

---

IMPLEMENTATION_FIX_REQUIRED