# T009 — Artifact-aware fix loop orchestration

## Contexte

T008 a introduit un mode `--auto` avec `state.json` comme source de vérité, gates stricts et transitions contrôlées.

Mais une limite importante reste visible : lorsqu’une review produit `PLAN_FIX_REQUIRED` ou `IMPLEMENTATION_FIX_REQUIRED`, le runner sait changer d’état, mais ne sait pas reconstruire automatiquement le contexte du retry.

Aujourd’hui l’humain doit concaténer manuellement :

- prompt canonique
- output précédent
- review précédente
- artefact de fix
- plan courant

## Objectif

Ajouter une orchestration de retry consciente des artefacts.

Le runner doit pouvoir relancer une étape de fix avec le bon contexte workflow.

## Inclus

- détecter les états de fix :
  - `PLAN_FIX_REQUIRED`
  - `IMPLEMENTATION_FIX_REQUIRED`
- définir les artefacts attendus :
  - `runs/TXXX/fixes/plan-fix-*.md`
  - `runs/TXXX/fixes/implementation-fix-*.md`
  - reviews associées
  - output précédent
- construire automatiquement un prompt enrichi pour le retry
- journaliser les artefacts injectés dans `runtime.log`
- échouer clairement si un artefact requis manque
- conserver une invocation explicite contrôlée par l’humain
- documenter le workflow retry dans README

## Hors scope

- pas de boucle infinie automatique
- pas de génération automatique de fix request par LLM
- pas de PR automatique
- pas de merge automatique
- pas de watcher permanent

## Critères d’acceptation

- le runner peut relancer un planner fix avec contexte enrichi
- le runner peut relancer un coder fix avec contexte enrichi
- les artefacts utilisés sont listés dans les logs
- absence d’artefact requis = erreur explicite
- README documente le fonctionnement
