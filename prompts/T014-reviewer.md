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

Le review doit se terminer avec exactement un keyword de décision sur sa propre ligne.

Les keywords valides pour l'état courant sont injectés par le runtime dans le contexte de cette review. Ne hardcode pas PLAN_APPROVED, PLAN_FIX_REQUIRED, IMPLEMENTATION_APPROVED ou IMPLEMENTATION_FIX_REQUIRED dans ce prompt : utilise uniquement les keywords fournis par le runtime.
