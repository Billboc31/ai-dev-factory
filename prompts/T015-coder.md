# Prompt Coder — T015

Rôle : Coder

Lis :
- tools/agent_runner/run_ticket.py
- tools/agent_runner/run_step.py
- tickets/TODO/T015-dynamic-review-decision-keywords.md
- runs/T015/plan.md

## Objectif

Implémenter l’injection dynamique des keywords de décision review par le workflow engine.

## Contraintes importantes

- garder les changements bornés
- ne pas refactorer massivement la state machine
- préserver `TRANSITIONS`
- préserver le parsing déterministe des reviews
- préserver la compatibilité fix loops
- conserver les logs runtime
- aucune autonomie implicite
- aucun merge automatique
- aucune PR automatique

## Travail attendu

Implémenter :

- une structure explicite des review decision keywords
- l’injection runtime des keywords reviewer
- un contexte review visible et reviewable
- des prompts reviewer génériques
- les tests nécessaires

## Vérifications importantes

Vérifier explicitement :

- compatibilité avec `_determine_next_state()`
- compatibilité avec `possible_next`
- compatibilité avec les fix contexts existants
- absence d’injection review sur les étapes non-review

## Attendu final

Produire :

- code modifié
- tests ciblés
- résumé des changements
- résultats des tests exécutés
