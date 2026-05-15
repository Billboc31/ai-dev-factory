All tasks complete. Here's the implementation summary:

---

## Résumé des changements

### Fichiers modifiés

**`.gitignore`**
- Suppression des 4 lignes dupliquées (14–17) — les entrées étaient déjà présentes aux lignes 7–11.

**`tools/agent_runner/run_issue_intake.py`**
- Ajout de `commit_bootstrap(ticket_id, push=False)` : stage `runs/TXXX/ticket.md` (jamais `git add .`), commit `T033: bootstrap checkpoint`, et pousse si `--push`.
- Ajout du paramètre `push=False` à `run_intake()` avec appel à `commit_bootstrap()` après la création des artefacts.
- Ajout du flag `--push` au parser CLI.

**`tools/agent_runner/run_daemon.py`**
- Ajout de `_classify_dirty_files(ticket_id)` : interroge `git status --porcelain` et classe chaque fichier en `workflow_artifacts` (`runs/`) ou `unknown_files`.
- Ajout de `_ensure_clean_working_tree(ticket_id, auto_push)` : checkpoint commit automatique si seuls des artefacts workflow sont dirty, abort sécurisé si des fichiers inconnus sont présents.
- Ajout de `_commit_after_intake(ticket_id)` : appelle `run_ticket.py TXXX --commit --include-code` pour commiter `runs/.issue-intake.json` après l'intake.
- `call_issue_intake()` : ajout du paramètre `push=False`, passe `--push` si actif.
- `poll_github_issues()` : passe `push=True` à l'intake + appelle `_commit_after_intake()` après succès.
- `launch_ticket()` : appelle `_ensure_clean_working_tree()` avant tout lancement `--auto`.

### Fichiers créés

**`tests/test_intake_checkpoint.py`** — 11 tests pour `commit_bootstrap()` et la propagation du flag `--push`.

### Fichiers étendus

**`tests/test_daemon_checkpoint.py`** — 16 nouveaux tests pour `_classify_dirty_files()`, `_ensure_clean_working_tree()`, et l'intégration dans `launch_ticket()`.

**`tests/test_daemon_issue_polling.py`** — 3 tests existants mis à jour + 4 nouveaux tests (`call_issue_intake --push`, `_commit_after_intake` appelé/non appelé).

**Résultat** : 334 tests passent, 0 régression introduite.
