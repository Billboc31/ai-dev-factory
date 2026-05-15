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


# T031 — T031 — Daemon terminal-ticket skip and commit/checkpoint hardening

**Source**: GitHub Issue #32

## Description

# T031 — Daemon terminal-ticket skip and commit/checkpoint hardening

## Contexte

Le dashboard, la Control API et le daemon fonctionnent maintenant ensemble, mais les tests réels ont révélé deux problèmes bloquants pour une utilisation autonome.

### Problème 1 — Le daemon rescane les anciens tickets terminés

Le daemon scanne tous les `runs/T*/state.json` à chaque cycle.

Pour les anciens tickets en `TEST_COMPLETE`, il relance le lifecycle PR et tente de créer une PR même quand la branche n’a plus de diff avec `main`.

Exemple observé :

```text
gh pr create failed: No commits between main and ticket/T022-...
```

Puis il recommence au cycle suivant.

Conséquences :

- lenteur importante avant de traiter les nouveaux tickets
- spam GitHub inutile
- logs bruyants
- le daemon semble bloqué sur de vieux tickets
- mauvais comportement pour une exécution permanente

### Problème 2 — Commit/checkpoint incomplet depuis l’UI/API

Le bouton Commit de l’IHM ne commit pas correctement tous les fichiers de code.

Causes probables :

- l’endpoint Control API appelle `run_ticket.py --commit` sans `--include-code`
- le scope de commit ne couvre pas tous les modules récents (`apps/`, `services/`, fichiers racine utiles)

Conséquences :

- les nouveaux dossiers frontend/backend restent untracked
- le workspace reste dirty
- le daemon ou l’intake peut refuser de continuer
- le workflow distant n’est pas fiable

## Objectif

Rendre le daemon et les actions commit/checkpoint robustes pour un usage quotidien via l’IHM.

Le système doit :

- ignorer les tickets terminalement finis
- ne pas retenter indéfiniment un PR lifecycle impossible
- archiver explicitement les anciens tickets terminés
- commit/push correctement les changements de code depuis l’API/UI
- garder le workspace clean entre les étapes

## Inclus

### 1. Skip des tickets archivés

Le daemon doit ignorer un ticket dont `state.json` contient :

```json
{
  "daemon_archived": true
}
```

Log attendu :

```text
[daemon] skipping T022 daemon_archived=true
```

### 2. Marquage terminal sur PR sans diff

Si le daemon tente de créer une PR et reçoit une erreur du type :

```text
No commits between main and ticket/...
```

alors il doit persister dans `state.json` un flag explicite, par exemple :

```json
{
  "pr_skipped_no_diff": true,
  "daemon_archived": true
}
```

Et ne plus retenter au cycle suivant.

### 3. Skip des tickets terminés déjà finalisés

Le daemon doit ignorer les tickets `TEST_COMPLETE` si l’un des flags suivants est vrai :

```text
daemon_archived=true
issue_closed=true
pr_skipped_no_diff=true
```

### 4. Commande d’archivage manuel

Ajouter une commande contrôlée :

```bash
python tools/agent_runner/run_ticket.py T022 --archive-daemon
```

Elle doit :

- vérifier le ticket id
- écrire `daemon_archived: true` dans `state.json`
- logger l’action dans `runtime.log`

### 5. Endpoint API d’archivage

Ajouter un endpoint Control API :

```text
POST /tickets/{ticket_id}/archive
```

Le backend doit appeler `run_ticket.py --archive-daemon` via le subprocess runner.

### 6. Bouton UI archive

Ajouter un bouton minimal dans la vue ticket :

```text
Archive daemon
```

Ce bouton sert à retirer un ticket terminé du cycle daemon.

### 7. Commit/checkpoint API avec include-code

Les actions Control API suivantes doivent appeler les commandes avec le bon scope :

```text
POST /tickets/{ticket_id}/commit
POST /tickets/{ticket_id}/checkpoint
```

Le comportement attendu doit inclure `--include-code` par défaut pour l’usage dashboard.

### 8. Scope commit complet

Vérifier et compléter le scope autorisé de `--include-code`.

Il doit inclure au minimum :

```text
tools/
tests/
prompts/
tickets/
docs/
ai/
services/
apps/
README.md
.gitignore
package.json
package-lock.json
```

Le système ne doit jamais faire `git add .`.

### 9. Tests

Ajouter des tests pour :

- daemon skip `daemon_archived`
- daemon skip `pr_skipped_no_diff`
- daemon marque `pr_skipped_no_diff` sur erreur GitHub no diff
- commande `--archive-daemon`
- endpoint API `/tickets/{id}/archive`
- commit endpoint appelle `--commit --include-code`
- checkpoint endpoint inclut le code
- `COMMIT_SCOPE` couvre `apps/` et `services/`
- aucun `git add .`

## Hors scope

- SQLite registry daemon
- multi-project dashboard
- refactor complet du daemon
- PR auto-merge
- auth UI
- notifications
- websocket

## Critères d’acceptation

- les vieux tickets `TEST_COMPLETE` ne ralentissent plus le daemon
- un ticket marqué `daemon_archived` est ignoré
- une PR impossible car sans diff n’est pas retentée en boucle
- le bouton/API Commit commit les changements code attendus
- le workspace peut rester clean après action UI
- aucune logique Git dangereuse (`git add .`) n’est introduite
- les logs sont explicites
- le workflow existant reste compatible

## Fichiers potentiellement modifiés

```text
tools/agent_runner/run_daemon.py
tools/agent_runner/run_ticket.py
services/control_api/
apps/dashboard/
tests/
README.md
```