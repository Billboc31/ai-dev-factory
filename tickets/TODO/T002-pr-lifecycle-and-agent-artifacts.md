# T002 — Définir le lifecycle PR IA et la structure des artefacts agent

## Contexte

Le workflow IA de ai-dev-factory est maintenant défini :

- planner
- review plan
- coder
- reviewer
- tester
- review implémentation
- memory updater
- review mémoire

Le système utilise GitHub PR comme protocole de communication entre agents.

Avant de coder un agent local minimal, il faut standardiser les artefacts et le lifecycle PR.

## Objectif

Définir le lifecycle officiel des PR IA et la structure standard des artefacts générés par les agents.

## Inclus

- conventions de branches
- conventions PR
- statuts workflow
- structure des runs
- structure des prompts
- structure des reviews
- structure des fix prompts
- responsabilités ChatGPT / agent local / humain
- règles d’escalade

## Exclus

- implémentation agent local
- intégration OpenAI API
- intégration Claude/Cursor
- merge automatique

## Travail attendu

Créer :

- docs/ai/pr-lifecycle.md

Définir une structure type :

```text
runs/TXXX/
  prompts/
  reviews/
  fixes/
  tests/
  memory/
```

## Contraintes

- rester générique
- GitHub = source de vérité
- conserver les 3 reviews obligatoires
- ne pas dépendre du projet RAG

## Critères d’acceptation

- lifecycle PR documenté
- artefacts standardisés
- responsabilités documentées
- prêt pour agent local minimal
