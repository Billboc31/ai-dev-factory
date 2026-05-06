# Prompt Planner — T002

Rôle : Planner

Lis attentivement :
- docs/ai/global-context.md
- docs/ai/project-life.md
- docs/ai/workflow.md
- ai/roles/planner.md
- ai/skills/architecture-discipline.md
- ai/skills/workflow-discipline.md
- ai/skills/documentation.md
- ai/skills/refactor-safety.md
- ai/templates/plan-template.md
- tickets/TODO/T002-pr-lifecycle-and-agent-artifacts.md

## Objectif

Produire un plan d’exécution pour définir le lifecycle PR IA et la structure standard des artefacts agent.

## Contraintes

- ne pas coder
- ne pas modifier le ticket
- rester générique
- ne pas dépendre de doc-platform/RAG
- ne pas dépendre d’un outil spécifique comme Cursor, Claude, Codex ou OpenAI API
- conserver GitHub comme source de vérité workflow
- conserver les 3 reviews obligatoires : plan, implémentation, mémoire

## À produire

Un plan structuré conforme à `ai/templates/plan-template.md`.

Le plan doit préciser :
- structure cible de `docs/ai/pr-lifecycle.md`
- conventions de branches
- conventions de PR
- statuts workflow
- structure des artefacts `runs/TXXX/`
- responsabilités ChatGPT / agent local / humain
- conditions de passage entre étapes
- règles d’escalade
- impacts sur le futur agent local minimal

## Ne fais pas

- pas d’implémentation agent local
- pas d’intégration API
- pas de GitHub Actions
- pas de merge automatique
