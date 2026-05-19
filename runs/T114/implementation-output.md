Only the 4 pre-existing `test_daemon_checkpoint.py` failures remain. All other tests pass, including the 7 new `_check_runtime_clone` tests.

Here's a summary of everything implemented for T114:

---

**Files created:**

- `docs/ai/architecture.md` — Vue d'ensemble : séparation humain/runtime, runtime root, tableau comparatif, sentinel de protection, note migration
- `docs/ai/runtime-layout.md` — Arborescence filesystem cible complète, état actuel documenté, table d'écarts, règles de nommage, note de migration hors scope
- `docs/ai/workflow-invariants.md` — 6 invariants formels (I1–I6), règles Git/worktree, table des points d'enforcement dans le code

**Files modified:**

- `tools/agent_runner/run_daemon.py` — Ajout de `_check_runtime_clone()` juste avant `parse_args()`, appelée au tout début de `main()`. Refuse le démarrage (exit 2) si ni le sentinel `.ai-dev-factory-runtime` ni `AI_DEV_FACTORY_RUNTIME_ROOT` ne sont présents.
- `tests/test_run_daemon.py` — Import de `_check_runtime_clone`, 4 nouveaux tests dédiés, 2 tests `main()` existants mis à jour pour patcher `_check_runtime_clone`, 1 nouveau test `test_main_returns_2_when_not_runtime_clone`
- `tests/test_daemon_issue_polling.py` — 5 tests `main()` mis à jour pour patcher `_check_runtime_clone`
- `.gitignore` — Pattern `.ai-dev-factory-runtime` ajouté avec commentaire
- `docs/ai/decisions-log.md` — Entrée T114 datée 2026-05-19
