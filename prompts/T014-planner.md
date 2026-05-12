# Prompt Planner — T014

Rôle : Planner

Lis :
- tools/agent_runner/run_step.py
- tools/agent_runner/run_ticket.py
- tickets/TODO/T014-stabilize-flexible-planner-validator.md

## Objectif

Stabiliser définitivement le validator planner flexible et confirmer que le workflow planner fonctionne réellement en runtime.

## Points importants

- validation souple sur les titres
- validation stricte sur le fond
- conserver les garde-fous contre les faux outputs
- ne pas casser le workflow `--auto`
- garder les changements bornés
- préserver les logs runtime explicites
- Git reste la source de vérité
- aucune autonomie implicite

## Vérifications importantes

Vérifier explicitement :

- `import subprocess`
- absence de `import subprocessf`
- utilisation réelle de `_REQUIRED_SECTION_GROUPS`
- comportement réel de `validate_planner_output()`
- intégration correcte avec `run_ticket.py`

## Attendu

Produire un plan permettant de :

- stabiliser la validation flexible
- ajouter des tests ciblés
- confirmer le passage planner vers review
