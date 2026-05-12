# Prompt Reviewer — T015

Rôle : Reviewer

Lis :
- tools/agent_runner/run_ticket.py
- tools/agent_runner/run_step.py
- tickets/TODO/T015-dynamic-review-decision-keywords.md
- runs/T015/plan.md
- runs/T015/implementation-output.md

## Objectif

Review de l’injection dynamique des review decision keywords.

## Vérifications importantes

- les keywords review sont injectés dynamiquement par le runtime
- les prompts reviewer restent génériques
- aucun hardcoding workflow inutile dans les prompts métier
- compatibilité avec `TRANSITIONS`
- compatibilité avec `_determine_next_state()`
- compatibilité avec les fix loops
- compatibilité avec les reviews plan et implémentation
- aucun impact sur les étapes non-review
- logs runtime conservés
- changements bornés

## Important

Le review doit utiliser uniquement les keywords de décision fournis par le runtime.

Ne pas hardcoder :

- PLAN_APPROVED
- PLAN_FIX_REQUIRED
- IMPLEMENTATION_APPROVED
- IMPLEMENTATION_FIX_REQUIRED

si ces valeurs ne correspondent pas au contexte runtime injecté.
