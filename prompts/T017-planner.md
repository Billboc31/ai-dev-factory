# Prompt Planner — T017

Rôle : Planner

Lis :
- tools/agent_runner/run_ticket.py
- tickets/TODO/T017-workflow-aware-commit-and-push.md

## Objectif

Planifier un système de commit/push workflow-aware pour ai-dev-factory.

## Points importants

- Git reste la source de vérité
- éviter tout `git add .` aveugle
- préserver la sécurité du workflow
- préserver les branches ticket
- préserver les fix loops et review loops
- garder les changements bornés
- conserver les logs runtime Git
- aucun merge automatique
- aucune PR automatique

## Vérifications importantes

Vérifier explicitement :

- fonctionnement actuel de `--commit`
- fonctionnement actuel de `--push`
- validation branche ↔ ticket
- working tree guards
- comment limiter le scope du staging
- comment éviter les fichiers hors scope

## Attendu

Produire un plan permettant :

- commit workflow-aware
- push workflow-aware
- staging sûr
- checkpoints Git cohérents et reviewables
