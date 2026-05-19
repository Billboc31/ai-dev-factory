# Architecture — ai-dev-factory

## Vue d'ensemble

ai-dev-factory distingue strictement deux types de clones Git :

- **Clone humain** — utilisé par le développeur pour coder, reviewer, débugger
- **Clone runtime** — utilisé exclusivement par les agents et le daemon

Le daemon ne doit **jamais** tourner dans un clone humain.

---

## Clone humain

```text
~/dev/ai-dev-factory
~/dev/doc-platform
```

Utilisé pour :
- développement humain
- architecture et design
- reviews de PR
- expérimentation et debugging manuel

**Contrainte** : aucun daemon, aucun worktree agent, aucun fichier runtime n'y est créé.

---

## Runtime root

```text
~/runtime/ai-dev-factory/
```

Point d'entrée unique de tout le runtime agentique. Contient :

```text
~/runtime/ai-dev-factory/
├── clones/       # clones runtime des projets gérés
├── worktrees/    # worktrees agents par projet et ticket
├── state/        # SQLite DB, registries, daemon state
└── logs/         # daemon logs, runtime logs, execution logs
```

---

## Clones runtime

```text
~/runtime/ai-dev-factory/clones/<project>
```

Exemples :
```text
~/runtime/ai-dev-factory/clones/ai-dev-factory
~/runtime/ai-dev-factory/clones/doc-platform
~/runtime/ai-dev-factory/clones/rag-admin
```

Les agents travaillent **uniquement** dans ces clones. Chaque clone est un `git clone` dédié, séparé du clone humain.

---

## Worktrees runtime

```text
~/runtime/ai-dev-factory/worktrees/<project>/<ticket>
```

Exemples :
```text
~/runtime/ai-dev-factory/worktrees/ai-dev-factory/T114
~/runtime/ai-dev-factory/worktrees/doc-platform/T041
```

Les worktrees sont créés depuis les clones runtime via `git worktree add`. Ils ne sont **jamais** créés depuis un clone humain.

---

## Runtime state

```text
~/runtime/ai-dev-factory/state/
```

Contient :
- SQLite runtime DB (`runtime.db`)
- issue index (`issue-intake.json`)
- workers registry (`workers.json`)
- daemon state (`daemon.pid`, `daemon.lock`)

Ces fichiers ne sont **jamais** versionnés dans Git.

---

## Runtime logs

```text
~/runtime/ai-dev-factory/logs/
```

Contient :
- `daemon.log` — log du daemon principal
- `<ticket>.log` — log d'exécution par ticket
- `intake.log` — log de l'issue intake

Ces fichiers ne sont **jamais** versionnés dans Git.

---

## Isolation des projets gérés

Chaque projet géré par ai-dev-factory dispose de son propre clone runtime sous `clones/`. Le framework et les projets gérés ne partagent **jamais** le même clone Git.

---

## Séparation humain / runtime — résumé

| Élément            | Clone humain | Runtime root |
|--------------------|:------------:|:------------:|
| Développement      | ✓            | ✗            |
| Daemon             | ✗            | ✓            |
| Worktrees agents   | ✗            | ✓            |
| SQLite DB          | ✗            | ✓            |
| Logs runtime       | ✗            | ✓            |
| Reviews / PR       | ✓            | ✗            |

---

## Sentinel de protection

Un clone runtime doit contenir un fichier `.ai-dev-factory-runtime` à sa racine, **ou** définir la variable d'environnement `AI_DEV_FACTORY_RUNTIME_ROOT`.

Sans l'un ni l'autre, le daemon refuse de démarrer (exit code 2).

Ce mécanisme protège le développeur contre un lancement accidentel du daemon dans son clone humain.

---

## Migration depuis l'architecture actuelle

L'architecture actuelle stocke :
- la SQLite DB dans `.runtime/` (dans le clone)
- les logs dans `runs/*/runtime.log` (versionnés ou ignorés dans le clone)

La migration vers `~/runtime/ai-dev-factory/state/` et `~/runtime/ai-dev-factory/logs/` est **hors scope** de T114 et fera l'objet d'un ticket dédié.
