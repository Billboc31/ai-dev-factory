# Prompt Planner — T016

Rôle : Planner

Lis :
- tools/agent_runner/run_step.py
- tools/agent_runner/run_ticket.py
- tickets/TODO/T016-runtime-prompt-snapshots.md

## Objectif

Planifier la persistance réelle des runtime prompt snapshots.

## Points importants

- les snapshots doivent représenter exactement le prompt envoyé au LLM
- inclure les extra contexts injectés
- snapshot avant exécution
- naming déterministe et incrémental
- conserver les logs runtime
- préserver les fix loops et review loops
- garder les changements bornés
- Git reste la source de vérité

## Vérifications importantes

Vérifier explicitement :

- où le prompt runtime final est construit
- où injecter la persistance snapshot
- comment calculer les numéros de tentative
- comment éviter les collisions de noms
- comment garantir l’écriture avant exécution

## Attendu

Produire un plan permettant :

- la persistance réelle des runtime prompts
- la rejouabilité complète des exécutions
- l’observabilité runtime
