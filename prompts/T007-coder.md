# Prompt Coder — T007

Rôle : Coder

Lis attentivement :
- docs/ai/workflow.md
- docs/ai/pr-lifecycle.md
- ai/roles/coder.md
- ai/skills/git-discipline.md
- ai/skills/code-quality.md
- ai/skills/refactor-safety.md
- tickets/TODO/T007-git-ticket-branch-workflow.md
- Plan T007 si disponible

## Objectif

Implémenter le workflow Git ticket branch dans `tools/agent_runner/run_ticket.py`.

## Travail attendu

Ajouter des commandes explicites pour :
- créer ou switcher vers une branche ticket
- générer un nom de branche standard `ticket/TXXX-*`
- commit les changements du ticket
- push explicitement la branche ticket

## Contraintes

- pas de merge automatique
- pas d’ouverture automatique de PR
- pas de review distante automatique
- pas de décision autonome
- rester compatible avec Python standard library
- ne pas modifier les prompts canoniques

## À produire

- fichiers modifiés
- résumé des commandes ajoutées
- exemples d’utilisation
