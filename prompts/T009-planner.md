# Prompt Planner — T009

Rôle : Planner

Lis :
- docs/ai/workflow.md
- docs/ai/pr-lifecycle.md
- docs/ai/git-workflow.md
- tools/agent_runner/run_ticket.py
- tools/agent_runner/run_step.py
- tickets/TODO/T009-artifact-aware-fix-loop.md

## Objectif

Planifier l’ajout d’une orchestration de retry consciente des artefacts.

## Points importants

- ne pas réintroduire d’autonomie dangereuse
- garder une invocation humaine explicite
- reconstruire automatiquement le contexte de retry
- ne pas masquer les artefacts injectés
- logs clairs
- erreurs explicites si artefacts manquants
