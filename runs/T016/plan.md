Le plan est écrit dans `runs/T016/plan.md`. Voici le résumé :

---

**Diagnostic précis**

Le `effective_prompt` est entièrement assemblé dans `run_step.py:main()` — après l'appel à `compose_runtime_prompt()` (ligne 351) et l'éventuel append de l'extra-context (ligne 357). Il est ensuite passé à `execute_external_command()` (ligne 365) mais jamais persisté.

---

**Plan en 3 étapes, un seul fichier modifié**

1. **`_write_prompt_snapshot(ticket_id, step, prompt) → Path`** dans `run_step.py` : compte les fichiers `{step}-attempt-*.md` existants dans `runs/TXXX/prompts/` pour déterminer le numéro de tentative, puis écrit le snapshot.

2. **Appel dans `main()`**, dans le bloc `if args.exec_cmd:`, après l'assemblage complet de `effective_prompt` et avant `execute_external_command()`. Suivi d'un `_log_runtime()` avec le chemin du snapshot.

3. **`tests/test_prompt_snapshot.py`** : tests directs sur `_write_prompt_snapshot()` (création, nommage, incrémentation, contenu, extra-context) + tests d'intégration via `main()`.

**`run_ticket.py` n'est pas modifié** : il appelle déjà `run_step.py --exec-cmd`, donc le snapshot sera écrit automatiquement à chaque step.
