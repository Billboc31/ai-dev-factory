# Prompt Planner — T013

Rôle : Planner

Lis :
- docs/ai/workflow.md
- docs/ai/pr-lifecycle.md
- tools/agent_runner/run_ticket.py
- tools/agent_runner/run_step.py
- tickets/TODO/T013-git-workflow-automation-primitives.md

## Objectif

Planifier l’ajout de primitives Git sûres et bornées pour réduire la friction du workflow.

## Points importants

- Git reste la source de vérité workflow
- aucune autonomie implicite dangereuse
- pas de merge automatique
- pas de PR automatique
- logs runtime explicites
- garde-fous stricts sur branche et working tree
- changements incrémentaux et reviewables
- éviter les commandes shell dangereuses implicites
