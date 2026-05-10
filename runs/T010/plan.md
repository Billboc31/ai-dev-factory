Le plan T010 est finalisé dans `runs/T010/plan.md`.

**Verdict : PLAN_APPROVED** — aucune correction requise.

Résumé du plan :
- **Un seul fichier modifié** : `tools/agent_runner/run_step.py`
- **4 ajouts** : `import datetime`, `_log_runtime_step()`, `_compute_attempt_number()`, `_write_prompt_snapshot()`
- **Intégration** dans `main()` : snapshot écrit après `effective_prompt`, avant `execute_external_command`
- **Fix loops T009** couverts via `has_extra_context=bool(args.extra_context_file)`
- **Documentation** : section à ajouter dans `tools/agent_runner/README.md`
