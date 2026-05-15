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


# T028 — T028 — Control API foundation and dashboard-ready orchestration layer

**Source**: GitHub Issue #25

## Description

# T028 — Control API foundation and dashboard-ready orchestration layer

## Contexte

Le workflow runtime est maintenant capable de :

- intake GitHub issues
- orchestrer planner/coder/reviewer/tester
- gérer approvals humaines
- gérer retry/cooldown
- publier des checkpoints commit/push
- créer et synchroniser des PR
- fermer les issues après merge

Mais le pilotage reste uniquement CLI.

Architecture cible :

```text
Frontend UI / mobile / dashboard
↓
Control API REST
↓
run_ticket.py / run_daemon.py / run_issue_intake.py
↓
Git / GitHub / runtime
```

Le système doit maintenant exposer une couche REST propre, exhaustive et dashboard-ready.

## Objectif

Créer un backend REST dédié permettant de piloter le workflow IA à distance.

Le backend doit être suffisamment exhaustif pour servir :

- une UI locale
- une future UI distante/mobile
- des dashboards multi-projets
- des automatisations externes
- des integrations futures

Même si certains endpoints ne sont pas utilisés immédiatement.

## Architecture obligatoire

Le backend REST DOIT être dans un module/service séparé.

Exemple cible :

```text
services/control-api/
```

ou :

```text
apps/control-api/
```

Le frontend/dashboard sera un autre module.

## Contraintes architecture critiques

### 1. Le backend REST n'est PAS un nouveau moteur workflow

Les moteurs canoniques restent :

```text
run_ticket.py
run_daemon.py
run_issue_intake.py
```

### 2. Le backend agit comme une façade contrôlée

Le backend REST :

- lit les artefacts runtime
- appelle les scripts existants via subprocess contrôlés
- orchestre les actions utilisateur

Le backend REST ne doit PAS :

- réimplémenter la state machine
- réimplémenter Git
- modifier directement `state.json`
- bypass les guardrails existants
- dupliquer la logique workflow

### 3. Le frontend ne doit jamais manipuler Git directement

Toutes les actions passent par l'API REST.

## Inclus

### 1. Nouveau module backend REST

Créer un service dédié.

Exemple :

```text
services/control-api/
```

Avec :

```text
main.py
routes/
models/
services/
```

Framework suggéré : FastAPI.

### 2. Endpoints daemon

```text
GET  /health
GET  /daemon/status
POST /daemon/start
POST /daemon/stop
POST /daemon/restart
```

### 3. Endpoints tickets

```text
GET  /tickets
GET  /tickets/{ticket_id}
GET  /tickets/{ticket_id}/logs
GET  /tickets/{ticket_id}/artifacts
GET  /tickets/{ticket_id}/plan
GET  /tickets/{ticket_id}/review
GET  /tickets/{ticket_id}/tests
```

### 4. Actions workflow

```text
POST /tickets/{ticket_id}/run-next
POST /tickets/{ticket_id}/approve-plan
POST /tickets/{ticket_id}/request-plan-fix
POST /tickets/{ticket_id}/approve-implementation
POST /tickets/{ticket_id}/request-implementation-fix
```

### 5. Actions Git/runtime

```text
POST /tickets/{ticket_id}/commit
POST /tickets/{ticket_id}/push
POST /tickets/{ticket_id}/checkpoint
```

Ces endpoints doivent appeler les scripts existants.

### 6. Intake endpoints

```text
POST /issues/intake
GET  /issues/intake/status
```

### 7. Provider / runtime status

```text
GET /providers/status
GET /projects
```

Même si certaines données sont initialement mockées/minimales.

### 8. Logging

Toutes les actions REST doivent logger :

```text
api: POST /tickets/T028/approve-plan
api: daemon start requested
api: checkpoint requested for T028
```

### 9. Tests

Ajouter des tests pour :

- endpoints principaux
- orchestration subprocess
- validation ticket_id
- erreurs subprocess
- daemon status
- lecture artefacts
- aucune mutation directe de state.json

## Hors scope

- vraie UI frontend
- websocket live logs
- auth complexe
- multi-user RBAC
- distributed workers
- auto merge
- model routing
- mobile app native
- Tailscale/VPN setup

## Critères d’acceptation

- le backend REST est dans un module séparé
- les endpoints principaux existent
- les actions appellent les scripts existants
- aucune logique workflow n'est dupliquée
- aucune logique Git n'est dupliquée
- les tickets et artefacts sont lisibles via API
- daemon start/stop fonctionne
- les logs API sont explicites
- les tests couvrent les endpoints critiques
- le workflow existant reste compatible

## Fichiers potentiellement modifiés

```text
services/control-api/
tests/
README.md
```