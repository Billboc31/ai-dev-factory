Le plan est écrit dans `runs/T020/plan.md`. Voici le résumé :

---

**Ce que le plan couvre :**

1. **`tools/agent_runner/run_daemon.py`** — nouveau script uniquement, `run_ticket.py` n'est pas touché.
2. **Constantes** : `AUTO_RUNNABLE_STATES` (6 états) et `HUMAN_GATE_STATES` (`PLAN_REVIEW_NEEDED`, `TEST_COMPLETE`).
3. **Scanner** : glob `runs/*/state.json`, ignore les fichiers corrompus.
4. **PID lock** : `runs/TXXX/daemon.lock` — vérifie si le PID est vivant, nettoie les locks stales.
5. **Lancement** : subprocess `run_ticket.py TXXX --auto --exec-cmd <cmd>`.
6. **CLI** : `--exec-cmd` (requis), `--interval`, `--once`, `--dry-run`, `--runs-dir`.
7. **Tests** : 15 tests unitaires dans `tests/test_run_daemon.py` couvrant tous les invariants.

**Hypothèse signalée** : `DONE` est mentionné dans le ticket comme gate humain mais n'existe pas dans `VALID_STATES` de `run_ticket.py`. Le plan le traite comme absent — à valider avant implémentation.

**Aucune dérive de scope** : pas de modification de `run_ticket.py`, pas de GitHub API, pas de logique d'orchestration avancée.
