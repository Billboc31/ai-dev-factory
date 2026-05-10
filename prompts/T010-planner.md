# Prompt Planner — T010

Rôle : Planner

Lis :
- docs/ai/workflow.md
- docs/ai/pr-lifecycle.md
- tools/agent_runner/run_ticket.py
- tools/agent_runner/run_step.py
- tickets/TODO/T010-runtime-prompt-snapshot.md

## Objectif

Planifier la persistance systématique des prompts runtime réellement envoyés au LLM.

## Points importants

- le snapshot doit être exact et rejouable
- les fix loops T009 doivent être couverts
- le snapshot doit être créé avant l’appel à l’external command
- conserver une séparation claire entre prompts canoniques et prompts runtime
- logs explicites
- pas d’autonomie supplémentaire
