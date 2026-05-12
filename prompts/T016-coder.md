# Prompt Coder — T016

Rôle : Coder

Lis :
- tools/agent_runner/run_step.py
- tools/agent_runner/run_ticket.py
- tickets/TODO/T016-runtime-prompt-snapshots.md
- runs/T016/plan.md

## Objectif

Implémenter la persistance réelle des runtime prompt snapshots.

## Contraintes importantes

- snapshot avant exécution LLM
- inclure les extra contexts injectés
- préserver fix loops
- préserver review loops
- préserver logs runtime
- éviter les collisions de noms
- garder les changements bornés
- aucune autonomie implicite

## Travail attendu

Implémenter :

- écriture des snapshots runtime
- naming déterministe
- incrément des tentatives
- logs runtime explicites
- tests ciblés

## Vérifications importantes

Vérifier explicitement :

- le contenu snapshoté correspond exactement au prompt envoyé
- les extra contexts apparaissent dans le snapshot
- les snapshots existent même en cas d’échec du process LLM
- aucune régression workflow

## Attendu final

Produire :

- code modifié
- tests ciblés
- résultats des tests exécutés
- résumé des changements
