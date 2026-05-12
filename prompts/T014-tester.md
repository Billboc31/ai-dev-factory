# Prompt Tester — T014

Rôle : Tester

Tester la stabilisation du validator planner flexible.

Lis :
- tools/agent_runner/run_step.py
- tools/agent_runner/run_ticket.py
- tickets/TODO/T014-stabilize-flexible-planner-validator.md
- runs/T014/plan.md
- runs/T014/implementation-output.md

## Objectif

Confirmer que le workflow planner fonctionne correctement avec la validation flexible.

## Tests attendus

Tester au minimum :

- plan valide avec titres canoniques
- plan valide avec synonymes
- plan trop court
- plan sans section obligatoire
- plan contenant une phrase interdite

## Workflow runtime

Vérifier le passage planner vers review sans rejet abusif.

## Régression

Confirmer que :

- les logs runtime existent toujours
- le workflow `--auto` reste compatible
- aucune autonomie implicite n’a été introduite

## Sortie attendue

Produire :

- liste des tests exécutés
- résultats observés
- problèmes détectés
- verdict final sur la stabilité du validator planner
