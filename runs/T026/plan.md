Le plan est écrit dans `runs/T026/plan.md`. Voici un résumé :

---

## Plan T026 — Résumé

**8 étapes, 5 fichiers.**

### Ce qui existe déjà
- `commit_ticket()` et `push_branch()` dans `run_ticket.py`
- Flags `--auto-commit` et `--auto-push` dans `run_ticket.py`
- `gh issue list/view` dans le daemon

### Ce qui manque

**Étape 1** — `run_issue_intake.py` : ajouter `issue_number` dans `state.json`

**Étape 2** — `run_ticket.py` : ajouter `include_code` dans `auto_run()` + flag `--auto-include-code`

**Étape 3** — `run_daemon.py` : passer `--auto-commit --auto-push --auto-include-code` à `launch_ticket()` + nouveaux flags daemon

**Étapes 4–7** — `run_daemon.py` : fonctions PR lifecycle
- `_load_state_json()` / `_save_state_json()` — lecture/écriture atomique
- `create_or_update_pr()` — `gh pr create/list/edit`, stocke `pr_number` dans state
- `check_and_close_issue()` — détecte merge, ferme issue, retire label `ai-ready`
- `handle_test_complete()` — orchestrateur appelé depuis `run_once()` pour `TEST_COMPLETE`

**Étape 8** — Tests : `test_daemon_checkpoint.py` (5 tests) + `test_daemon_pr_lifecycle.py` (10 tests), tous avec mocks gh

### Risques clés
- Double PR → gardé par `pr_number` dans state + `gh pr list --head` avant create
- `save_state()` dans `run_ticket.py` → préserve les champs inconnus (`issue_number`, `pr_number`) via `{**state_dict, ...}` ✓
- Toutes les erreurs gh sont non-bloquantes (loggées, daemon continue)
