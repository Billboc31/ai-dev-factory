# Plan Fix Request — T008

Status: PLAN_FIX_REQUIRED

## Contexte

Le plan T008 actuel est globalement bon, mais il viole une contrainte obligatoire ajoutée au prompt coder T008.

## Problème bloquant

Le plan propose encore une machine à états pilotée par `workflow-status.md`.

Ce n’est pas acceptable pour T008.

`workflow-status.md` ne doit pas être la source de vérité workflow, car :
- il contient de l’historique
- il peut contenir plusieurs statuts passés
- il est fragile à parser
- il a déjà provoqué un bug où `PLAN_APPROVED` était relu après `IMPLEMENTATION_APPROVED`

## Correction attendue

Réviser le plan pour introduire :

- `runs/TXXX/state.json` comme source de vérité canonique
- `workflow-status.md` uniquement comme vue humaine / journal
- une table explicite des transitions autorisées
- des gates stricts avant transition
- des erreurs explicites si :
  - `state.json` absent
  - `state.json` corrompu
  - état inconnu
  - transition invalide
  - branche git incohérente
  - working tree incohérent

## Contraintes à conserver

- `--auto` exécute une seule étape par invocation
- pas de PR automatique
- pas de merge automatique
- pas de boucle infinie
- commit/push uniquement contrôlés
- exit code non-zéro sur gate bloquant

## Résultat attendu

Mettre à jour `runs/T008/plan.md` avec un plan corrigé compatible avec un vrai workflow engine strict.
