# T022 — Generic workflow prompts

## Contexte

Le workflow repose encore sur des prompts spécifiques par ticket :

```text
prompts/TXXX-planner.md
prompts/TXXX-coder.md
prompts/TXXX-review.md
prompts/TXXX-tester.md
```

Cette approche fonctionne mais crée beaucoup de boilerplate.

Depuis T019, `runs/TXXX/ticket.md` devient la tâche runtime canonique.

L’intelligence workflow doit maintenant migrer vers :

```text
ai/roles/
ai/skills/
runs/TXXX/ticket.md
```

Les prompts spécifiques doivent devenir optionnels.

## Objectif

Permettre au workflow de fonctionner sans prompts spécifiques TXXX.

Le système doit fallback automatiquement sur des prompts génériques basés sur :

- role
- skills
- ticket.md
- runtime artifacts

## Inclus

- ajouter un mécanisme de fallback générique
- permettre l’absence totale de `prompts/TXXX-*.md`
- conserver la compatibilité avec les prompts spécifiques existants
- ajouter des prompts génériques partagés
- logguer clairement la source du prompt utilisée
- ajouter des tests ciblés

## Comportement attendu

Ordre de résolution :

```text
1. prompt spécifique ticket
2. prompt générique workflow
3. erreur explicite si absent
```

## Hors scope

- suppression des prompts existants
- génération automatique de prompts
- GitHub integration
- UI web
- daemon changes

## Critères d’acceptation

- un ticket peut fonctionner sans prompts spécifiques
- les prompts spécifiques restent prioritaires
- les logs indiquent le prompt réellement utilisé
- le workflow existant reste compatible
- les erreurs restent explicites

## Fichiers potentiellement modifiés

```text
tools/agent_runner/run_step.py
prompts/generic/
tests/
README.md
```
