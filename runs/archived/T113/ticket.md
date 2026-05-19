# T113 — T113 — Isolate daemon and intake from developer main repository using dedicated worktrees

**Source**: GitHub Issue #61

## Description

# T113 — Isolate daemon and intake from developer main repository using dedicated worktrees

## Contexte

Le daemon utilise encore le repository principal développeur (`main`) pour :

- intake GitHub issues
- génération project-map
- runtime bookkeeping
- checkpoint temporaires
- validation working tree clean

Cela provoque régulièrement :

- main dirty
- intake bloqué
- runtime logs sur main
- pycache dans main
- changements intempestifs de branche
- conflits avec travail humain
- daemon bloqué si développeur modifie le repo

T111 a amélioré le runtime state avec SQLite mais le daemon dépend encore du repo principal.

## Objectif

Isoler complètement le daemon/runtime du repository développeur humain.

Le daemon ne doit plus jamais modifier le repo principal.

## Architecture cible

```text
~/ai-dev-factory
→ repo humain principal
→ utilisé uniquement par le développeur

~/ai-dev-factory-worktrees/_intake
→ worktree dédié intake/runtime
→ checkout main propre

~/ai-dev-factory-worktrees/TXXX
→ worktrees tickets dédiés
```

## Travail demandé

Créer un worktree dédié daemon/intake.

Le daemon doit :

- ne jamais écrire dans le repo principal
- effectuer les scans/intake dans `_intake`
- utiliser `_intake` pour validation clean tree
- générer project-map uniquement dans `_intake`
- effectuer runtime bookkeeping uniquement dans `_intake`
- créer les worktrees tickets depuis `_intake`

## Contraintes

- backward compatible
- aucun impact sur workflow ticket existant
- aucun changement UX board
- migration automatique si possible
- fallback legacy accepté

## Tests

Valider que :

- modifier `main` humain ne bloque plus intake
- daemon peut tourner pendant travail humain
- aucun fichier runtime n’apparaît dans repo principal
- intake fonctionne même avec repo humain dirty
- TXXX worktrees continuent fonctionner

## Critères d’acceptation

- repo développeur reste propre
- daemon totalement découplé du repo humain
- plus aucun blocage intake lié à main dirty
- plus aucun checkout automatique dans repo humain
