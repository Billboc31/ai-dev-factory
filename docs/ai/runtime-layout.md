# Runtime Layout — ai-dev-factory

## Architecture cible

```text
~/runtime/ai-dev-factory/
├── clones/
│   ├── ai-dev-factory/          # git clone du framework
│   ├── doc-platform/            # git clone du projet doc-platform
│   └── rag-admin/               # git clone du projet rag-admin
│
├── worktrees/
│   ├── ai-dev-factory/
│   │   ├── T114/                # worktree agent pour ticket T114
│   │   └── T115/                # worktree agent pour ticket T115
│   └── doc-platform/
│       └── T041/                # worktree agent pour ticket T041
│
├── state/
│   ├── runtime.db               # SQLite runtime DB
│   ├── workers.json             # registry des workers actifs
│   ├── issue-intake.json        # index anti-doublon issues GitHub
│   └── daemon.pid               # PID du daemon
│
└── logs/
    ├── daemon.log               # log principal du daemon
    ├── T114.log                 # log d'exécution ticket T114
    └── intake.log               # log de l'issue intake
```

---

## Architecture actuelle (état réel — 2026-05-19)

L'architecture actuelle diffère de la cible sur plusieurs points :

```text
~/dev/ai-dev-factory/            # clone humain ET runtime (couplé)
├── .runtime/
│   └── runtime.db               # SQLite DB dans le clone (gitignored)
├── runs/
│   ├── daemon.log               # log daemon dans le clone (gitignored)
│   ├── daemon.pid               # PID daemon dans le clone (gitignored)
│   ├── workers.json             # registry dans le clone (gitignored)
│   └── <ticket>/
│       ├── runtime.log          # log ticket dans le clone (gitignored)
│       └── state.json           # état ticket dans le clone (versionné)
└── [worktrees dans ../ai-dev-factory-worktrees/]
```

---

## Écarts et notes de migration

| Élément              | Actuel                        | Cible                                      |
|----------------------|-------------------------------|--------------------------------------------|
| SQLite DB            | `.runtime/runtime.db` (clone) | `~/runtime/.../state/runtime.db`           |
| Daemon logs          | `runs/daemon.log` (clone)     | `~/runtime/.../logs/daemon.log`            |
| Ticket logs          | `runs/T*/runtime.log` (clone) | `~/runtime/.../logs/<ticket>.log`          |
| Workers registry     | `runs/workers.json` (clone)   | `~/runtime/.../state/workers.json`         |
| Worktrees            | `../ai-dev-factory-worktrees` | `~/runtime/.../worktrees/<project>/`       |
| Clone runtime        | Clone humain (couplé)         | Clone dédié sous `~/runtime/.../clones/`   |

**La migration effective est hors scope de T114.** Elle fera l'objet d'un ticket dédié.

---

## Règles de nommage

- Un worktree par ticket : `worktrees/<project>/<ticket-id>/`
- Un clone par projet géré : `clones/<project-name>/`
- Le nom du projet correspond au nom du dépôt GitHub (sans l'organisation)

---

## Invariants filesystem

- `clones/` ne contient que des `git clone` complets
- `worktrees/<project>/` ne contient que des `git worktree add` créés depuis `clones/<project>/`
- `state/` et `logs/` sont gitignorés dans tous les clones
- Aucun fichier sous `state/` ou `logs/` n'est jamais commité

---

## Sentinel runtime

Chaque clone sous `clones/` doit contenir `.ai-dev-factory-runtime` à sa racine.

Ce fichier signale au daemon qu'il s'exécute dans un clone runtime légitime.
Il est ajouté manuellement lors de la création du clone runtime et n'est **pas versionné** (gitignored).
