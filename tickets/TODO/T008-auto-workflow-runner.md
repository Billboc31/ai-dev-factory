# T008 — Auto workflow runner avec gates stricts

## Contexte

Les premiers tests runtime T007 ont validé le workflow semi-auto : Claude Code peut produire un plan, modifier le repo, répondre aux reviews, commit/push, et le runner peut gérer des étapes simples.

Mais le système reste loin du full auto : l’humain pilote encore les transitions, les gates ne sont pas strictement imposées, et les boucles review/fix ne sont pas orchestrées automatiquement.

## Objectif

Ajouter un mode `--auto` contrôlé au runner pour orchestrer un ticket étape par étape avec logs visibles et gates stricts.

## Inclus

- ajouter une commande `--auto` dans `run_ticket.py`
- créer/switch automatiquement la branche ticket avant exécution
- lancer une étape à la fois
- afficher des logs clairs
- interdire les transitions invalides
- gérer au minimum le cycle : planner -> review -> coder -> review -> tester
- ne pas marquer `IMPLEMENTATION_APPROVED` avant review + test
- commit/push après chaque étape importante
- documenter les limites

## Exclus

- pas d’ouverture automatique de PR
- pas de merge automatique
- pas de review distante API
- pas de watcher permanent
- pas de suppression ou rewrite git destructif

## Critères d’acceptation

- `run_ticket.py --auto` existe
- le mode auto reste explicite et contrôlé
- logs visibles pendant l’exécution
- gates respectés
- pas de merge automatique
- README mis à jour
