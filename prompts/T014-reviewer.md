# Prompt Reviewer — T014

Rôle : Reviewer

Review de la stabilisation du validator planner flexible.

Lis :
- tools/agent_runner/run_step.py
- tools/agent_runner/run_ticket.py
- tickets/TODO/T014-stabilize-flexible-planner-validator.md
- runs/T014/plan.md
- runs/T014/implementation-output.md

## Objectif

Vérifier que le validator planner est robuste et qu’il n’introduit pas de régression dans le workflow engine.

## Vérifications importantes

- validation flexible des titres
- rejet des plans trop courts
- rejet des phrases interdites
- rejet des outputs déguisés
- compatibilité avec `run_ticket.py`
- compatibilité avec `--auto`
- logs runtime conservés
- changements bornés

## Cas à vérifier

Exemples de titres acceptés :

- `## contexte technique`
- `## objectifs`
- `## scope`
- `## non inclus`
- `## acceptance criteria`

Le passage planner vers review doit fonctionner sans dépendre de titres exacts.

## Sortie attendue

Le review doit contenir explicitement :

`PLAN_APPROVED`

ou

`PLAN_FIX_REQUIRED`
