# Prompt Coder — T017

Rôle : Coder

Lis :
- tools/agent_runner/run_ticket.py
- tickets/TODO/T017-workflow-aware-commit-and-push.md
- runs/T017/plan.md

## Objectif

Implémenter des checkpoints Git workflow-aware.

## Contraintes importantes

- jamais de `git add .`
- staging limité et explicite
- préserver les guardrails Git existants
- préserver les branches ticket
- préserver les logs runtime
- préserver fix loops et review loops
- aucune autonomie implicite
- aucun merge automatique
- aucune PR automatique

## Travail attendu

Implémenter :

- commit workflow-aware
- push workflow-aware
- staging limité aux chemins autorisés
- validations branche/ticket
- logs runtime Git explicites
- tests ciblés

## Vérifications importantes

Vérifier explicitement :

- refus des fichiers hors scope
- refus mauvaise branche
- push uniquement branche ticket
- compatibilité avec `state.json`
- compatibilité `--auto`
- absence de `git add .`

## Attendu final

Produire :

- code modifié
- tests ciblés
- résultats des tests exécutés
- résumé des changements
