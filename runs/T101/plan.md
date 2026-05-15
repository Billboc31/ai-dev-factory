Le plan est écrit dans `runs/T101/plan.md`. Voici un résumé des 5 bugs et des corrections planifiées :

---

## Plan T101 — Runtime hardening

### Bug 1 — Mapping timeline (`artifact_reader.py:151-152, 191`)
- `IMPLEMENTATION_REVIEW_NEEDED` : corriger `human_gate=True` → `False` et statut `"waiting_human"` → `"running"` (le reviewer tourne automatiquement, confirmé par `AUTO_RUNNABLE_STATES` dans le daemon)
- `TEST_COMPLETE` : corriger `human_gate=False` → `True` (le merge est humain)
- Mettre à jour les assertions de `test_ticket_timeline.py` en conséquence

### Bug 2 — Ticket ID allocation (`run_daemon.py:632-643`)
- L'implémentation est déjà correcte (parsing numérique). Ajouter uniquement des tests edge cases dans `test_daemon_issue_polling.py` : T034→T035, T099→T100, T1/T10/T100→T101, reserved set, gaps.

### Bug 3 — Dirty tree trop strict (`run_daemon.py:235-259`)
- `_classify_dirty_files()` : passer de 2-tuple à **3-tuple** `(workflow_artifacts, code_scope_files, unknown_files)` en ajoutant `_CODE_SCOPE_PREFIXES` comme constante de module
- `_ensure_clean_working_tree()` : les fichiers `code_scope` ne bloquent plus — auto-checkpoint avec `--include-code` (le commit l'avait déjà mais le pre-flight abortait avant d'y arriver)
- Mettre à jour les 8+ tests de `test_daemon_checkpoint.py`

### Bug 4 — PR avant checkpoint (`run_daemon.py:515-519`)
- Ajouter `_checkpoint_and_push_before_pr()` (non-bloquant) et l'appeler dans `handle_test_complete()` avant `create_or_update_pr()`
- Ajouter 4 tests dans `test_daemon_pr_lifecycle.py`

### Bug 5 — `.gitignore` incomplet
- Ajouter : `runs/.issue-intake.json`, `runs/.issue-intake.json.tmp`, `runs/*/retry-state.json`, `runs/*/retry-state.json.tmp`, `runs/*/state.json.tmp`
- Retirer les doublons `apps/dashboard/node_modules/` + `.vite/`
- `git rm --cached` si des fichiers sont déjà trackés

**7 fichiers modifiés, aucun créé.** La state machine `run_ticket.py` n'est pas touchée.

PLAN_APPROVED

Note:
Ne pas ignorer `runs/.issue-intake.json` sans décision explicite, car c’est un registre d’intake utile pour éviter les réingestions et auditer le lien issue→ticket. Ignorer les `.tmp` oui. Pour `retry-state.json`, acceptable seulement si on le considère explicitement runtime volatile.