31/31 tests passent, aucune régression. Voici le résumé de l'implémentation :

---

## Résumé des changements

### Fichiers modifiés

**`tools/agent_runner/run_step.py`** — +17 lignes

- `_next_attempt_number(ticket_id, step)` : compte les fichiers `{step}-attempt-*.md` dans `runs/TXXX/prompts/`, retourne `n+1`
- `_write_prompt_snapshot(ticket_id, step, prompt)` : écrit le snapshot avec naming déterministe, log dans `runtime.log` (`snapshot: runtime-prompt=...`)
- Appel de `_write_prompt_snapshot()` dans `main()`, avant `execute_external_command()` — à ce point `effective_prompt` inclut déjà les extra contexts

### Fichiers créés

**`tests/test_run_step_snapshots.py`** — 6 tests :

1. `test_snapshot_created` — le fichier est créé
2. `test_snapshot_naming` — format `{step}-attempt-1.md` correct
3. `test_snapshot_attempt_increment` — incrémentation à chaque appel
4. `test_snapshot_contains_extra_context` — extra context présent dans le snapshot
5. `test_snapshot_content_exact` — contenu identique au prompt runtime
6. `test_no_snapshot_without_exec_cmd` — pas de snapshot sans `--exec-cmd`

### Limites connues

- Le snapshot n'est écrit que si `--exec-cmd` est passé (conforme au plan — `--show-prompt` seul ne déclenche pas de snapshot)
- Le compteur est basé sur le glob filesystem, pas atomique — ne supporte pas l'exécution parallèle du même step sur le même ticket
