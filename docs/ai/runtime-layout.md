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

## État réel après T116 (2026-05-19)

Les chemins canoniques sont désormais imposés via `AI_DEV_FACTORY_RUNTIME_ROOT` :

```text
/runtime/<instance>/             # RUNTIME_ROOT — seul lieu autorisé pour les artefacts runtime
├── .runtime/
│   └── ai-dev-factory.sqlite    # SQLite DB canonique (une seule instance autorisée)
├── runs/
│   └── <ticket>/
│       ├── runtime.log          # log ticket (dans le worktree associé si actif)
│       └── state.json           # état ticket (versionné dans le worktree)
├── worktrees/
│   └── <ticket>/                # worktree jetable par ticket
├── clones/
│   └── ai-dev-factory/          # clone runtime (sentinel .ai-dev-factory-runtime présent)
├── state/
│   ├── workers.json             # registry des workers actifs (hors runs/)
│   └── .issue-intake.json       # index anti-doublon issues GitHub (hors runs/)
└── logs/
    └── daemon.log               # log daemon (file logging activé quand RUNTIME_ROOT est set)
```

Interdictions enforced par le code :
- Aucune DB SQLite dans les worktrees (fallback `git common-dir` supprimé)
- `workers.json` et `.issue-intake.json` dans `state/` (séparé de `runs/`)
- Board Docker lit `RUNTIME_ROOT/.runtime/ai-dev-factory.sqlite` (path hardcodé supprimé)

---

## Écarts résiduels

| Élément              | T116                                          | Cible long terme                        |
|----------------------|-----------------------------------------------|-----------------------------------------|
| Ticket logs          | `runs/T*/runtime.log` dans le worktree        | `logs/<ticket>.log` dans RUNTIME_ROOT   |
| Daemon logs          | `RUNTIME_ROOT/logs/daemon.log` (file logging) | ✓ implémenté                            |
| Workers registry     | `RUNTIME_ROOT/state/workers.json`             | ✓ implémenté                            |
| SQLite DB            | `RUNTIME_ROOT/.runtime/ai-dev-factory.sqlite` | ✓ implémenté                            |
| Board Docker         | Lit depuis RUNTIME_ROOT                       | ✓ implémenté                            |

Migration progressive : `deploy/bootstrap.sh` copie les anciens artefacts vers les nouvelles destinations au démarrage Docker (best-effort, sans suppression).

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
