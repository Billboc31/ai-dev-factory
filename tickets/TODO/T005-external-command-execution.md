# T005 — Ajouter l’exécution externe contrôlée des prompts

## Contexte

T003 a créé un runner local minimal.
T004 a ajouté une state machine locale minimale avec `--next`.

Le runner sait maintenant identifier la prochaine étape et résoudre le prompt canonique, mais il n’exécute encore aucun outil externe.

## Objectif

Ajouter une capacité contrôlée d’exécution externe pour lancer un prompt avec une commande locale fournie explicitement.

## Inclus

- ajouter une option `--exec-cmd`
- passer le prompt canonique sur stdin de la commande externe
- capturer stdout comme artefact de sortie
- écrire stdout dans le chemin attendu ou fourni
- conserver stderr dans un fichier log optionnel
- documenter l’usage

## Exclus

- pas d’intégration spécifique Claude/Cursor/OpenAI
- pas d’appel API direct
- pas de watcher permanent
- pas de décision autonome
- pas de merge automatique
- pas d’exécution sans commande explicite

## Contraintes

- aucune commande par défaut
- l’utilisateur doit fournir explicitement la commande
- ne pas exécuter via shell si possible
- conserver les prompts canoniques en lecture seule
- rester compatible Python standard library

## Critères d’acceptation

- le runner peut envoyer un prompt à une commande externe
- stdout peut être écrit dans l’artefact attendu
- stderr peut être loggé
- README mis à jour
- le comportement reste opt-in et non autonome
