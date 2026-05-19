---

# PR Review — T117 (second review cycle)

## Résumé

Deuxième cycle de review. Les deux problèmes bloquants identifiés lors du premier cycle ont été correctement corrigés. Les 6 fixes planifiés sont tous présents et fonctionnels. Le correctif Docker/deploy, bien qu'hors scope selon le plan approuvé, est architecturalement justifié et résout un problème réel de compatibilité host-daemon. L'implémentation est prête pour approbation.

## Vérifications effectuées

- Lecture du diff complet `main...HEAD` sur tous les fichiers de production (6 fichiers modifiés/créés hors workflow artifacts)
- Vérification des deux bloquants du premier cycle : `git rebase --abort` + docker-compose bind mount
- Vérification de la correction mineure signalée : returncode de `git checkout -f main`
- Lecture de `docs/daemon-lifecycle.md`
- Lecture de `deploy/.env.example`
- Comparaison plan approuvé ↔ implémentation actuelle

## Points validés

| Étape plan | Fichier | Fix 1 | Fix 2 | Verdict |
|---|---|---|---|---|
| Fix 1 : `--auto-commit`, `--auto-push`, `--worktrees-dir` | `daemon_manager.py` | ✅ | — | Correct |
| Fix 2 : `git checkout -f main` à chaque `ensure_intake_worktree` | `worktree_manager.py` | ✅ | ✅ warning ajouté | Correct |
| Fix 3 : `git ls-files --error-unmatch` avant restore | `run_issue_intake.py` | ✅ | — | Correct |
| Fix 4 : création on-demand + skip sans fallback legacy | `run_daemon.py` | ✅ | — | Correct |
| Fix 5 : `--rebase` + `git rebase --abort` sur échec | `run_daemon.py` | ✅ | ✅ abort ajouté | Correct |
| Fix 6 : documentation lifecycle daemon | `docs/daemon-lifecycle.md` | ✅ | — | Complète et précise |

### BLOQUANT #1 résolu — Docker/deploy

Le premier cycle flaggait l'introduction d'un named Docker volume (`runtime-data:/runtime`) qui cassait l'accès host-side du daemon, et la suppression de `deploy/.env` qui cassait les fresh deploys.

État actuel du diff vs `main` :
- `docker-compose.yml` : volume `~/runtime/ai-dev-factory:/runtime` (bind mount) — daemon host-side peut accéder aux fichiers runtime au chemin habituel. Correct architecturalement.
- `env_file` : passage en forme longue avec `required: false` — déploiement sans `.env` ne crashe plus.
- `deploy/.env.example` : template complet (35 lignes), aucun secret, documentation des variables attendues.

### BLOQUANT #2 résolu — `git rebase --abort` sur échec

```python
# run_daemon.py, _sync_ticket_branch()
_log(f"{ticket_id}: sync branch {branch!r} failed — rebase conflict: {stderr}")
subprocess.run(["git", "rebase", "--abort"], cwd=cwd, capture_output=True)
return False
```

Le worktree ne reste plus en état `rebase in progress` indéfiniment. Chaque cycle daemon peut reprendre normalement après un conflit.

### MINEUR résolu — returncode `git checkout -f main`

```python
# worktree_manager.py
if co.returncode != 0:
    print(f"[worktree_manager] warning: git checkout -f main failed in _intake: {co.stderr.strip()}", file=sys.stderr)
return True, intake_path
```

Warning loggué, retour `True` conservé (acceptable — l'intake peut continuer même si le checkout échoue dans certains états edge).

## Risques éventuels

### Observation mineure — incohérence doc `.env.example`

Le commentaire dans `deploy/.env.example` dit :
> Run it on the host with RUNTIME_ROOT pointing at the **Docker named volume mount**

Mais `docker-compose.yml` utilise désormais un bind mount (`~/runtime/ai-dev-factory:/runtime`), pas un named volume. La phrase devrait dire "bind mount" ou "runtime directory". Non bloquant — le fichier est un template commenté, le comportement effectif est dans `docker-compose.yml`.

### Observation — docker-compose.yml hors scope plan approuvé

Le plan approuvé liste explicitement `Docker / deploy` comme hors scope. Ces changements y touchent. Cependant :
- La contrainte ticket impose « keep daemon host-side » et « preserve canonical runtime architecture from T116 »
- Un named Docker volume est structurellement incompatible avec un daemon host-side qui doit accéder aux mêmes fichiers
- Le premier cycle de review a déjà examiné ce point — le fix corrige la bonne direction
- Le résultat est architecturalement correct

Risque résiduel : si un déploiement existant utilisait `runtime-data` comme named volume, le passage au bind mount change l'emplacement des données. Acceptable dans le contexte d'un projet en développement actif.

## Décision

- APPROVED

Les deux bloquants du premier cycle sont résolus. Les 6 fixes du plan sont correctement implémentés. La documentation est complète. Aucun nouveau problème bloquant introduit.

IMPLEMENTATION_APPROVED
