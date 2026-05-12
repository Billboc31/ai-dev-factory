# Prompt Coder — T014

Rôle : Coder

Implémenter la stabilisation du validator planner flexible décrite dans le ticket T014.

Lis :
- tools/agent_runner/run_step.py
- tools/agent_runner/run_ticket.py
- tickets/TODO/T014-stabilize-flexible-planner-validator.md
- runs/T014/plan.md

## Objectif

Stabiliser `validate_planner_output()` pour que les plans valides ne soient plus rejetés à cause de titres Markdown légèrement différents, tout en conservant les garde-fous contre les faux plans.

## Contraintes obligatoires

- garder les changements bornés
- ne pas refactorer massivement `run_step.py`
- ne pas modifier la state machine de `run_ticket.py` sauf nécessité prouvée
- préserver la compatibilité avec `--auto`
- conserver les logs runtime existants
- ne pas introduire d’autonomie implicite
- ne pas ajouter de merge automatique
- ne pas ajouter de PR automatique

## Travail attendu

Vérifier et corriger si nécessaire :

- `import subprocess`
- absence de `import subprocessf`
- absence d’une validation active basée sur une ancienne constante stricte `_REQUIRED_SECTIONS`
- présence et usage réel de `_REQUIRED_SECTION_GROUPS`
- validation par au moins un marqueur accepté par groupe
- messages d’erreur explicites pour les sections manquantes

Ajouter ou mettre à jour les tests couvrant :

- plan valide avec titres canoniques
- plan valide avec synonymes
- plan trop court
- plan avec section obligatoire manquante
- output contenant une phrase interdite

## Attendu final

Produire :

- code modifié si nécessaire
- tests ciblés
- résumé des changements
- commandes de test exécutées
- résultat indiquant si le passage planner vers `PLAN_REVIEW_NEEDED` est validé ou non
