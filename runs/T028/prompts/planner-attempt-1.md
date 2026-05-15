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

# Generic Planner Task

Read the ticket below and produce a detailed implementation plan.

The plan must include:
- changes to implement (files, functions, logic)
- out-of-scope items
- risks and dependencies
- acceptance criteria

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