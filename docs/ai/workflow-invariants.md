# Workflow Invariants — ai-dev-factory

## Invariants formels

Les invariants suivants sont des règles strictes du système. Toute violation est une erreur.

---

### I1 — Le daemon ne tourne jamais dans un clone humain

```text
Le daemon doit être lancé uniquement depuis un clone runtime.
Un clone runtime est identifié par la présence de .ai-dev-factory-runtime
à la racine du clone, ou par la variable d'environnement AI_DEV_FACTORY_RUNTIME_ROOT.
```

**Enforcement code** : `run_daemon.py` — fonction `_check_runtime_clone()`, appelée au début de `main()`. Sans détection valide → exit code 2.

---

### I2 — Les worktrees agents sont créés uniquement sous `worktrees/`

```text
git worktree add doit toujours cibler un chemin sous
~/runtime/ai-dev-factory/worktrees/<project>/<ticket>.
Aucun worktree ne doit être créé dans un clone humain.
```

**Enforcement code** : `worktree_manager.py` — paramètre `worktrees_dir` transmis par le daemon. Le daemon ne passe jamais un chemin humain comme `worktrees_dir`.

---

### I3 — Les projets gérés sont isolés du framework

```text
Chaque projet géré dispose d'un clone runtime dédié sous clones/.
Le framework et les projets gérés ne partagent jamais le même clone Git.
```

**Enforcement** : convention de nommage `clones/<project>/` + sentinel `.ai-dev-factory-runtime` par clone.

---

### I4 — Les fichiers runtime ne polluent pas les clones humains

```text
La SQLite DB, les logs daemon, les workers registry, les fichiers PID
ne doivent jamais être créés dans un clone humain.
```

**Enforcement** : séparation physique clone humain / runtime root. Le daemon ne démarre pas dans un clone humain (voir I1).

---

### I5 — Une branche Git n'est checkoutée qu'une seule fois

```text
Une même branche ne peut pas être active simultanément dans deux
worktrees ou clones différents. git worktree add échoue si la
branche est déjà checkoutée ailleurs.
```

**Enforcement** : comportement natif de Git. Le daemon vérifie l'existence du worktree avant création (`worktree_manager.py`).

---

### I6 — Les logs runtime ne sont jamais versionnés

```text
runs/*/runtime.log, runs/daemon.log, runs/daemon.pid,
et tout contenu de logs/ sont gitignorés dans tous les clones.
```

**Enforcement** : `.gitignore` du dépôt. Patterns couvrant `runs/**/runtime.log`, `runs/daemon.log`, `runs/daemon.pid`.

---

## Règles Git / worktree

| Règle | Description |
|-------|-------------|
| Worktree source | Un worktree est toujours créé depuis un clone runtime (`clones/<project>/`) |
| Chemin worktree | Toujours sous `worktrees/<project>/<ticket>/` |
| Branche unique | Une branche = un seul worktree actif |
| Pull avant lancement | Le daemon fait `git pull --ff-only` avant chaque step |
| Checkout main | Interdit dans le daemon (remplacé par worktree `_intake`) |
| Commits runtime | Jamais depuis un clone humain |

---

## Points d'enforcement dans le code

| Invariant | Fichier | Mécanisme |
|-----------|---------|-----------|
| I1 | `tools/agent_runner/run_daemon.py` | `_check_runtime_clone()` au début de `main()` |
| I2 | `tools/agent_runner/worktree_manager.py` | paramètre `worktrees_dir` contrôlé par le daemon |
| I5 | Git natif + `worktree_manager.py` | `git worktree add` échoue si branche déjà checkoutée |
| I6 | `.gitignore` | patterns `runs/**/runtime.log`, `runs/daemon.*` |

---

## Détection du runtime clone (I1)

Le daemon accepte deux mécanismes :

1. **Sentinel file** : `.ai-dev-factory-runtime` présent à la racine du clone (`REPO_ROOT`)
2. **Variable d'environnement** : `AI_DEV_FACTORY_RUNTIME_ROOT` définie (valeur non vide)

Si aucun mécanisme n'est actif au démarrage → message explicite sur `stderr` + exit code 2.

Le sentinel est gitignored et doit être créé manuellement lors de la mise en place d'un clone runtime.
