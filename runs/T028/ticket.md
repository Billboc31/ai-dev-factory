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
