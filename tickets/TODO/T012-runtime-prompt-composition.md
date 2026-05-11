# T012 — Runtime prompt composition

## Contexte

T010 a montré que les prompts locaux trop courts peuvent faire dériver les rôles.

Le runner doit charger automatiquement le contexte global, le rôle et les skills avant le prompt local du ticket.

## Objectif

Composer automatiquement le prompt runtime final.

Ordre attendu :

1. contexte global
2. rôle
3. skills du rôle
4. prompt local du ticket
5. contexte runtime éventuel

## Inclus

- définir une convention rôle vers skills
- charger les fichiers associés automatiquement
- garder les prompts ticket courts
- renforcer le rôle planner
- imposer qu'un plan soit complet et autonome
- refuser les faux plans trop courts ou assimilables à un changelog
- logger les fichiers injectés

## Hors scope

- pas de merge automatique
- pas de PR automatique
- pas de validation par modèle externe

## Critères d'acceptation

- le prompt runtime inclut global context, rôle et skills
- un planner ne produit pas un résumé à la place d'un plan
- les retries planner restent complets
- les logs indiquent les fichiers chargés
