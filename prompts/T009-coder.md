# Prompt Coder — T009

Rôle : Coder

Implémenter l’orchestration artifact-aware des fix loops.

## Objectif

Permettre au runner de relancer une étape de fix avec un contexte enrichi automatiquement.

## Contraintes obligatoires

- ne pas ajouter de boucle infinie
- ne pas ouvrir de PR automatiquement
- ne pas merger automatiquement
- ne pas générer automatiquement le contenu des fix requests
- afficher/loguer les artefacts injectés
- échouer avec exit code non-zéro si un artefact requis manque
- garder `state.json` comme source de vérité
- ne jamais utiliser `workflow-status.md` comme source de décision
