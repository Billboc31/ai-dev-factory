Le plan est écrit dans `runs/T031/plan.md`. Voici le résumé :

---

## Plan T031 — résumé

### Problème 1 — Daemon spam TEST_COMPLETE

**3 modifications dans `run_daemon.py`** :
1. **`scan_tickets()`** — skip immédiat si `daemon_archived=true` (log explicite inclus)
2. **`create_or_update_pr()`** — détecte "No commits between" dans stderr de `gh pr create`, persiste `pr_skipped_no_diff=true` + `daemon_archived=true` dans state.json
3. **`run_once()`** — avant `handle_test_complete()`, charge state.json et skip si `issue_closed=true` ou `pr_skipped_no_diff=true`

### Problème 2 — Commit/checkpoint sans include-code

**`subprocess_runner.py`** — ajoute `--include-code` à `commit_ticket()` et `checkpoint_ticket()`.

**Bug connexe** : `--checkpoint` n'existe pas dans `run_ticket.py` (unrecognized argument). → Ajout d'un alias `--checkpoint` → `commit_ticket()` dans l'argparse.

### Nouveautés

- **`run_ticket.py`** : commande `--archive-daemon`, `COMMIT_SCOPE` étendu avec `README.md`, `.gitignore`, `package.json`, `package-lock.json`
- **API** : `POST /tickets/{id}/archive` + `archive_ticket()` dans subprocess_runner
- **UI** : bouton "Archive daemon" dans `TicketDetailPage.jsx`

### Tests

14 nouveaux tests répartis sur 5 fichiers de test existants.
