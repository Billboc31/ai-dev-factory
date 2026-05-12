# Prompt Planner — T015

Rôle : Planner

Lis :
- tools/agent_runner/run_ticket.py
- tools/agent_runner/run_step.py
- tickets/TODO/T015-dynamic-review-decision-keywords.md

## Objectif

Planifier l’injection dynamique des keywords de décision review par le workflow engine.

## Points importants

- le workflow engine devient la source de vérité des review decisions
- les prompts reviewer doivent rester génériques
- éviter tout hardcoding des keywords workflow dans les prompts métier
- préserver la compatibilité avec `TRANSITIONS`
- préserver le parsing déterministe des reviews
- conserver les logs runtime explicites
- garder les changements bornés
- Git reste la source de vérité
- aucune autonomie implicite

## Vérifications importantes

Vérifier explicitement :

- où `_determine_next_state()` parse les keywords
- comment `possible_next` est construit
- comment injecter un extra context review sans casser les fix contexts existants
- comment rendre les prompts reviewer génériques

## Attendu

Produire un plan permettant :

- d’injecter dynamiquement les review decision keywords
- de rendre les prompts reviewer génériques
- de préserver le workflow déterministe actuel
