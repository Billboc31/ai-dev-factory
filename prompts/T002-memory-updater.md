# Prompt Memory Updater — T002

Rôle : Memory Updater

Lis attentivement :

* docs/ai/global-context.md
* docs/ai/project-life.md
* docs/ai/workflow.md
* ai/roles/memory-updater.md
* ai/skills/memory-management.md
* ai/skills/documentation.md
* ai/templates/memory-update-template.md
* tickets/TODO/T002-pr-lifecycle-and-agent-artifacts.md
* Plan T002
* Review T002
* Implémentation fournie

## Objectif

Mettre à jour la mémoire projet après validation de T002.

## Travail attendu

Mettre à jour :

* docs/ai/project-life.md
* éventuellement docs/ai/decisions-log.md si nécessaire

Documenter :

* l’ajout du lifecycle PR IA
* la standardisation des artefacts `runs/TXXX/`
* la séparation prompts canoniques / snapshots d’exécution
* le rôle GitHub-centric du workflow
* les responsabilités ChatGPT / agent local / humain

Créer également :

`runs/T002/memory/memory-update.md`

conforme à `ai/templates/memory-update-template.md`.

## Contraintes

* ne pas inventer de comportements non validés
* ne pas modifier le workflow officiel
* ne pas ajouter de nouvelles conventions non approuvées
* la mémoire doit refléter uniquement le comportement validé

## Résultat attendu

* mémoire projet mise à jour
* impacts architecture documentés
* dette technique éventuelle documentée
* résumé mémoire créé dans runs/T002/memory/
