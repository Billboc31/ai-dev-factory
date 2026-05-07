# T007 — Git ticket branch workflow

## Objectif

Ajouter au runner local la gestion standardisée des branches Git par ticket.

## Contexte

Le workflow IA repose maintenant sur :
- prompts canoniques
- artefacts `runs/TXXX/`
- orchestration locale
- exécution externe contrôlée

La prochaine étape est de permettre les reviews distantes automatiques via GitHub.

Pour cela, chaque ticket doit vivre sur une branche dédiée et versionnée.

## Inclus

- créer une convention officielle de branche : `ticket/TXXX-*`
- ajouter une commande pour créer/switch une branche ticket
- ajouter une commande de commit standardisé
- ajouter une commande de push contrôlé
- documenter le workflow Git ticket
- rester compatible avec `pr-lifecycle.md`

## Exclus

- pas d’ouverture automatique de PR
- pas de merge automatique
- pas de review distante automatique
- pas de GitHub Actions

## Critères d’acceptation

- le runner peut créer une branche ticket
- le runner peut commit les artefacts du ticket
- le runner peut push explicitement la branche
- le workflow Git est documenté
- la convention `ticket/TXXX-*` est utilisée
