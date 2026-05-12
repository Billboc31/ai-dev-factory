Le plan est écrit dans `runs/T016/plan.md`. Voici le résumé :

---

**Diagnostic**

`effective_prompt` est assemblé entièrement dans `run_step.py:main()` — `compose_runtime_prompt()` puis append de l'extra context (lignes 346–353). Il est ensuite passé à `execute_external_command()` (ligne 360) mais jamais persisté. Le dossier `prompts/` est créé par `ensure_run_tree()` mais toujours vide.

---

**Plan : 2 fonctions + 1 appel + 1 fichier de tests**

1. **`_next_attempt_number(ticket_id, step)`** : compte les fichiers `{step}-attempt-*.md` existants dans `runs/TXXX/prompts/`, retourne `n+1`.

2. **`_write_prompt_snapshot(ticket_id, step, prompt)`** : détermine le numéro de tentative, écrit le snapshot, log dans `runtime.log`.

3. **Appel dans `main()`** : premier appel dans `if args.exec_cmd:`, avant `execute_external_command()`. À ce point, `effective_prompt` inclut déjà l'extra context.

4. **`tests/test_run_step_snapshots.py`** : 6 tests ciblés (création, nommage, incrémentation, extra-context, contenu exact, absence de snapshot sans `--exec-cmd`).

**`run_ticket.py` n'est pas modifié** — il appelle `run_step.py` en subprocess, les snapshots sont gérés automatiquement dans chaque invocation.
