# Prompt Coder — T013

Rôle : Coder

Implémenter les primitives Git workflow décrites dans le ticket T013.

Lis :
- docs/ai/workflow.md
- docs/ai/git-workflow.md
- tools/agent_runner/run_ticket.py
- tickets/TODO/T013-git-workflow-automation-primitives.md
- runs/T013/plan.md

## Objectif

Ajouter des commandes Git sûres et contrôlées au runner pour réduire la friction du workflow.

## Contraintes obligatoires

- ne pas introduire de merge automatique
- ne pas créer de PR automatiquement
- ne pas faire d’auto-commit implicite sans flag explicite
- refuser les actions Git si la branche courante est incohérente
- refuser les actions dangereuses si le working tree est sale, sauf pour la commande de commit elle-même
- logger les actions Git importantes dans `runs/TXXX/runtime.log`
- garder les changements bornés à `tools/agent_runner/run_ticket.py` et documentation si possible
- éviter `git add .` aveugle si une alternative plus sûre existe
- conserver la compatibilité avec les options existantes `--branch`, `--commit`, `--push`, `--auto`, `--auto-init`, `--set-state`

## Attendu

Implémenter au minimum :
- ensure branch sûr
- commit checkpoint contrôlé
- push contrôlé
- logs runtime associés
- documentation d’usage

Ne pas modifier la state machine fonctionnelle au-delà de ce qui est nécessaire pour ces primitives Git.
