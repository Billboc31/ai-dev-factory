# T021 — Human approval commands

## Contexte

Le workflow supporte maintenant un daemon local qui peut avancer automatiquement sur les états auto-runnable.

Mais les gates humaines restent pilotées avec une commande trop générique :

```bash
python tools/agent_runner/run_ticket.py TXXX --set-state PLAN_APPROVED
```

Cette approche fonctionne, mais elle est trop basse-niveau pour devenir une interface stable pour :

- daemon local
- UI web
- validation mobile
- commentaires GitHub
- review externe

Il faut introduire des commandes métier explicites.

## Objectif

Ajouter des commandes d’approbation humaines sûres et typées.

Commandes cibles :

```bash
python tools/agent_runner/run_ticket.py TXXX --approve-plan
python tools/agent_runner/run_ticket.py TXXX --request-plan-fix
python tools/agent_runner/run_ticket.py TXXX --approve-implementation
python tools/agent_runner/run_ticket.py TXXX --request-implementation-fix
```

Ces commandes doivent appliquer uniquement des transitions valides depuis l’état courant.

## Inclus

- ajouter les options CLI d’approbation
- valider strictement l’état courant avant transition
- refuser les transitions invalides
- logguer les approvals dans `runtime.log`
- conserver `--set-state` pour usage bas niveau/debug
- ajouter des tests ciblés

## Transitions attendues

```text
PLAN_REVIEW_NEEDED → PLAN_APPROVED
PLAN_REVIEW_NEEDED → PLAN_FIX_REQUIRED
IMPLEMENTATION_REVIEW_NEEDED → IMPLEMENTATION_APPROVED
IMPLEMENTATION_REVIEW_NEEDED → IMPLEMENTATION_FIX_REQUIRED
```

Toute autre combinaison doit être refusée.

## Hors scope

- GitHub comments
- PR sync
- UI web
- risk classifier
- daemon changes
- merge automatique

## Critères d’acceptation

- les commandes d’approbation existent
- les transitions valides fonctionnent
- les transitions invalides sont refusées clairement
- les actions sont loggées
- `--set-state` reste disponible
- le workflow existant reste compatible

## Fichiers potentiellement modifiés

```text
tools/agent_runner/run_ticket.py
tests/
README.md
```
