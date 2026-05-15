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
