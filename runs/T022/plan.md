Le plan est écrit dans `runs/T022/plan.md`. Voici le résumé :

**Changements bornés sur 3 points dans `run_step.py` :**

1. **`prompt_candidates()`** — ajoute `prompts/generic/{step}.md` comme dernier candidat.
2. **`find_prompt()`** — logge la source résolue (`ticket-specific` ou `generic`) dans `runtime.log`.
3. **`main()`** — détecte si le prompt résolu est générique, lit `runs/TXXX/ticket.md` et l'injecte dans le contenu de la tâche (erreur explicite si absent).

**Nouveaux fichiers :**
- `prompts/generic/` — 5 fichiers step (planner, coder, review, tester, memory-updater)
- `tests/test_prompt_resolution.py` — 5 cas de test ciblés

**Hors scope confirmé :** `run_ticket.py`, `run_daemon.py`, `memory-apply`, GitHub, UI, suppression des prompts existants.
