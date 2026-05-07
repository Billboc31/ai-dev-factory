# T006 — Runner séquentiel de ticket

## Objectif

Créer `tools/agent_runner/run_ticket.py` pour piloter un ticket étape par étape à partir du workflow existant.

## À faire

- lire un ticket id `TXXX`
- afficher la prochaine étape
- afficher le prompt attendu
- afficher l’artefact attendu
- ajouter un mode dry-run par défaut
- ajouter une option pour lancer une seule étape avec une commande externe explicite
- mettre à jour le README

## Hors scope

- pas de watcher
- pas de merge automatique
- pas de génération de prompts
- pas de décision autonome

## Critères d’acceptation

- `run_ticket.py` existe
- dry-run par défaut
- une seule étape peut être lancée explicitement
- README documente l’usage
