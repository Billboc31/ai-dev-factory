I have enough information to write the full review.

---

# PR Review — T104 : Per-ticket worker worktrees and isolated runtime

## Résumé

Implémentation d'une architecture supervisor + workers isolés avec des Git worktrees par ticket. Le daemon orchestre sans exécuter directement les étapes agent. Chaque ticket actif dispose de son propre worktree, runtime, locks et logs. Le dashboard affiche les workers actifs.

---

## Vérifications effectuées

- Lecture de `worktree_manager.py` (nouveau fichier)
- Lecture de `run_daemon.py` — sections workers registry, `launch_ticket`, `scan_tickets`, `poll_github_issues`, `run_once`
- Lecture de `board_service.py` — projection board worktree-aware
- Lecture de `schemas.py` — champs `worker_pid`, `worker_cwd` sur `BoardItem`
- Lecture de `DaemonPage.jsx` — section Workers
- Lecture de `BoardPage.jsx` — affichage pid + worktree dans BoardCard
- Vérification de `run_issue_intake.py` — staging de `state.json` dans `commit_bootstrap`

---

## Points validés

**Lifecycle worktree (critère 1)**
- `get_ticket_worktree_path`, `create_ticket_worktree`, `remove_ticket_worktree` implémentés dans `worktree_manager.py`
- `git worktree add` utilisé correctement, sans `cwd` explicite (acceptable : le daemon tourne depuis le repo root)
- Refus explicite de suppression si dirty tree (`git status --porcelain` avant remove) — contrainte du ticket respectée

**Pattern supervisor/worker (critère 2)**
- `launch_ticket` délègue via `subprocess.run(..., cwd=str(worktree_path))` — le daemon n'exécute plus les étapes agent directement
- `_register_worker` / `_unregister_worker` encadrent l'exécution dans un `try/finally` propre
- `_cleanup_stale_workers` au démarrage du daemon nettoie les entrées fantômes après crash

**Isolation runtime (critère 3)**
- Les locks (`daemon.lock`), logs (`runtime.log`) et retry state (`retry-state.json`) sont écrits dans le worktree (`worktree_path/runs/TXXX/`)
- `runs/workers.json` au niveau supervisor est bien séparé des fichiers worker
- Nommage légèrement différent du ticket (`daemon.lock` vs `worker.lock`, `workers.json` vs `worker.pid`) mais la séparation supervisor/worker est respectée dans les faits

**Compatibilité backward (non-worktree)**
- Chemin legacy (`else:` dans `launch_ticket`) conservé intégralement — tickets existants sans worktree continuent de fonctionner

**Correction critique du cycle précédent**
- `commit_bootstrap` dans `run_issue_intake.py` stage maintenant `state.json` en plus de `ticket.md` — le worktree fraîchement créé dispose du state requis

**Board et dashboard (critère 5)**
- `board_service.py` lit depuis `worktree/runs/TXXX/state.json` quand le worktree existe (priorité sur le main repo)
- `schemas.py` : `worker_pid` et `worker_cwd` ajoutés à `BoardItem`
- `BoardPage.jsx` : affiche `pid:XXXX` + nom du worktree extrait du `worker_cwd`
- `DaemonPage.jsx` : section "Workers" listant les tickets en "running" avec branch, cwd, pid — polling à 5s

**max_workers (critère 4)**
- Contrôle `active_count >= max_workers` avant chaque launch, basé sur `len(workers_registry)` — défaut 1
- Architecture correctement préparée pour la parallélisation future : le registry et le chemin worktree permettent plusieurs workers indépendants

**Contraintes du ticket**
- Pas de `git add .` (staging fichier par fichier uniquement)
- Pas d'auto-merge
- Human gates conservés (`PLAN_REVIEW_NEEDED`, `TEST_COMPLETE`)
- `git pull --ff-only` dans le worktree avant chaque execution
- Pas de duplication de la state machine

---

## Problèmes détectés

**Observation (non bloquant) — `worker_pid` est le PID du daemon, pas du sous-processus**

Dans `_register_worker` (ligne 175) :
```python
"pid": os.getpid(),  # PID du daemon, pas du run_ticket.py subprocess
```
Le `worker_pid` affiché dans le dashboard est celui du daemon parent, pas de l'exécutable `run_ticket.py` enfant. En pratique cela fonctionne (nettoyage stale via PID mort du daemon crashé), mais la sémantique est trompeuse pour l'opérateur : le PID affiché ne correspond pas au processus worker réel. Ce serait plus fidèle avec `subprocess.Popen` et `proc.pid`.

**Observation (non bloquant) — `subprocess.run` bloquant rend `max_workers > 1` ineffectif**

L'architecture prépare bien la parallélisation (registry, worktrees isolés), mais le daemon reste bloqué pendant toute l'exécution d'un worker (`subprocess.run` synchrone). `max_workers=2` serait sans effet en l'état. Acceptable pour cette itération selon les contraintes du ticket ("prepare la parallélisation future").

**Observation (style, non bloquant) — import via `importlib` pour `worktree_manager`**

```python
_wm_spec = importlib.util.spec_from_file_location("_worktree_manager", ROOT / "worktree_manager.py")
```
Un `sys.path.insert` suivi d'un `import worktree_manager` serait plus lisible et moins fragile. Fonctionnel mais inhabituel.

**Observation (non bloquant) — silence sur erreur board dans DaemonPage**

```js
daemonApi.getBoardData()
  .catch(() => {})  // silencieux
```
Les erreurs API board ne sont pas remontées dans la WorkersList — risque de section vide sans feedback utilisateur. Mineur.

---

## Risques éventuels

- Si le daemon est démarré hors du repo git root, les `git worktree add` sans `cwd` explicite échoueront silencieusement (fallback legacy déclenché, avec log). Acceptable.
- En cas de crash daemon entre `_register_worker` et `_unregister_worker`, le ticket restera enregistré dans `workers.json` jusqu'au prochain démarrage (nettoyé par `_cleanup_stale_workers`). Correct.

---

## Décision

Tous les critères d'acceptation du ticket sont satisfaits :
- chaque ticket actif a son propre worktree Git ✅
- plus de conflit de branche courante entre tickets ✅
- supervisor ne lance plus directement les étapes agent ✅
- logs/locks/runtime isolés par worker ✅
- board affiche les workers actifs ✅
- architecture prête pour la parallélisation future ✅

Les observations ci-dessus sont non bloquantes et peuvent être adressées dans des tickets dédiés.

IMPLEMENTATION_APPROVED
