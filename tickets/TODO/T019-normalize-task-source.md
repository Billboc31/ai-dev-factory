# T019 — Normalize task source

## Contexte

Le workflow utilise aujourd’hui des tickets locaux et des prompts spécifiques par ticket.

À terme, la source métier doit pouvoir venir d’un système externe ou d’un fichier local, mais chaque run doit conserver une copie stable de la tâche.

Cible :

```text
source externe ou locale
→ runs/TXXX/ticket.md
→ state.json
→ workflow steps
```

## Objectif

Ajouter un mécanisme explicite pour créer `runs/TXXX/ticket.md` depuis une source locale.

Ce fichier devient le snapshot runtime de la tâche.

## Inclus

- ajouter une option d’initialisation de ticket depuis un fichier local
- copier le contenu source vers `runs/TXXX/ticket.md`
- refuser les chemins dangereux
- refuser les fichiers absents
- préserver la compatibilité avec les prompts existants
- préparer une future source externe sans l’implémenter maintenant
- logger la source utilisée dans `runtime.log`
- ajouter des tests ciblés

## Hors scope

- watcher local
- daemon permanent
- appel réseau
- création automatique de PR
- suppression des prompts existants
- refactor complet de la composition runtime
- merge automatique

## Critères d’acceptation

- `runs/TXXX/ticket.md` peut être créé depuis un fichier local
- le contenu est copié fidèlement
- le snapshot reste stable si la source change ensuite
- les erreurs sont explicites
- le workflow existant continue de fonctionner
- aucune autonomie implicite n’est ajoutée

## Fichiers potentiellement modifiés

```text
tools/agent_runner/run_ticket.py
tools/agent_runner/run_step.py
tests/
README.md
```
