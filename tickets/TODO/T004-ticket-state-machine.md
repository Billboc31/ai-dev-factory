# T004 — Ajouter une state machine locale minimale au runner

## Contexte

T003 a créé un runner local minimal capable de :
- résoudre les prompts canoniques
- créer `runs/TXXX/`
- écrire des artefacts
- maintenir un `workflow-status.md`

Le runner ne sait pas encore déterminer la prochaine étape logique d’un ticket.

## Objectif

Ajouter une state machine locale minimale permettant de lire l’état d’un ticket et d’indiquer la prochaine étape à exécuter.

## Inclus

- ajouter un script ou une commande `next`
- lire `runs/TXXX/workflow-status.md`
- déterminer la prochaine étape attendue
- afficher le prompt canonique à utiliser
- afficher le chemin d’artefact attendu
- documenter les transitions principales

## Exclus

- pas d’appel LLM automatique
- pas de watcher GitHub
- pas de merge automatique
- pas de décision autonome avancée
- pas de génération de prompts

## Critères d’acceptation

- une commande permet d’afficher la prochaine étape
- les transitions principales sont documentées
- le runner reste simple et sans réseau
- le README est mis à jour
