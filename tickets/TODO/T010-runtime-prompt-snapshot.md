# T010 — Runtime prompt snapshot persistence

## Contexte

T008 a introduit un mode `--auto` avec `state.json` comme source de vérité, gates stricts et transitions contrôlées.

T009 a ajouté une orchestration artifact-aware des fix loops : le runner peut reconstruire un contexte de retry à partir des artefacts du run.

Il reste une limite importante : le prompt exact envoyé à Claude n’est pas toujours persisté comme artefact runtime.

Aujourd’hui, même si le contexte est reconstruit, il n’existe pas toujours de snapshot clair et rejouable du prompt final réellement transmis au LLM.

## Objectif

Persister systématiquement le prompt runtime exact envoyé à l’external command.

Chaque exécution doit produire un artefact dans :

```text
runs/TXXX/prompts/<step>-attempt-N.md
```

Ce fichier doit contenir le prompt complet effectivement envoyé à Claude, incluant :

- prompt canonique
- contexte extra éventuel
- séparateurs
- métadonnées utiles de run

## Inclus

- créer une convention de nommage pour les snapshots de prompts runtime
- calculer un numéro d’attempt par step
- écrire le prompt exact avant appel à l’external command
- loguer le chemin du snapshot dans `runtime.log`
- documenter le fonctionnement dans le README
- conserver la compatibilité avec les exécutions sans contexte extra
- couvrir les steps classiques et les fix loops artifact-aware

## Hors scope

- pas de replay automatique
- pas de resume automatique
- pas de comparaison automatique entre prompts
- pas de merge automatique
- pas de PR automatique
- pas de watcher permanent

## Critères d’acceptation

- chaque exécution via `run_step.py --exec-cmd` écrit un snapshot dans `runs/TXXX/prompts/`
- le snapshot contient exactement le prompt envoyé à l’external command
- le nom du snapshot permet de distinguer les attempts
- le chemin du snapshot est affiché ou logué
- les fix loops T009 produisent aussi un snapshot complet avec contexte injecté
- README documente où trouver et comment relire les prompts runtime
