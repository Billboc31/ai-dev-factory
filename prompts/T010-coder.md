# Prompt Coder — T010

Rôle : Coder

Implémenter la persistance des prompts runtime.

## Objectif

Sauvegarder le prompt exact réellement envoyé à l’external command dans `runs/TXXX/prompts/`.

## Contraintes obligatoires

- le snapshot doit être écrit avant l’exécution du LLM
- le snapshot doit correspondre exactement au prompt envoyé
- inclure le contexte injecté T009 si présent
- numéroter les attempts par step
- loguer le chemin du snapshot
- ne pas modifier les prompts canoniques
- ne pas introduire de replay automatique
- ne pas introduire de boucle automatique
- garder `state.json` comme source de vérité workflow
