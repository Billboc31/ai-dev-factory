Plan produced and state advanced to `PLAN_REVIEW_NEEDED`. Here's a summary:

---

## Plan T104 — Per-ticket worker worktrees

**11 étapes, 8 fichiers impactés, 1 nouveau fichier.**

### Nouveaux fichiers
- `tools/agent_runner/worktree_manager.py` — `create_ticket_worktree`, `remove_ticket_worktree`, `get_ticket_worktree_path`

### Modifications clés

| Fichier | Changement |
|---------|-----------|
| `run_daemon.py` | + `runs/workers.json` registry, + `--worktrees-dir`/`--max-workers`, launch avec `cwd=worktree`, monitor PID workers |
| `run_ticket.py` | skip `git checkout` si déjà sur la bonne branche (cas worktree), + `--repo-root` flag |
| `run_issue_intake.py` | retour à la branche d'origine après bootstrap |
| `board_service.py` | lire state depuis worktree quand actif, enrichir cards avec metadata worker |
| `artifact_reader.py` | résolution dynamique du chemin artifacts (worktree vs repo principal) |
| `DaemonPage.jsx` + `BoardPage.jsx` | affichage workers actifs (PID, branch, cwd) |

### Architecture de base
- `~/ai-dev-factory-worktrees/T104/` — worktree isolé par ticket
- `runs/workers.json` — registre supervisor (dans repo principal)
- `{worktree}/runs/T104/worker.pid` et `worker.lock` — runtime isolé
- `max_workers=1` par défaut, architecture prête pour N > 1

### Hors scope
Exécution parallèle effective, changements state machine, migration tickets actifs.
