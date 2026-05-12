Le plan est écrit dans `runs/T013/plan.md`. Voici un résumé de ce qui a été planifié.

---

## Plan T013 — Synthèse

**Fichier unique modifié** : `tools/agent_runner/run_ticket.py`

### 4 étapes

**1. `--branch` → `--ensure-branch` + garde-fous**
La fonction `checkout_branch()` reçoit un appel à `_check_working_tree_clean()` avant tout, refuse si le working tree est sale, et logue chaque action dans `runtime.log`.

**2. `commit_ticket()` — refus si rien à committer + message state-aware**
Avant de stager, on vérifie via `git status --porcelain runs/<ticket_id>/` qu'il y a quelque chose à committer. Le message par défaut inclut l'état courant lu dans `state.json` (ex. `T013: checkpoint [PLAN_APPROVED] — update workflow artifacts`). Le sha du commit est loggé.

**3. `push_branch()` — vérification state.json + logging**
Avant le push, on charge `state.json` et on compare la branche courante à `state["branch"]`. Refus si mismatch. Si `state.json` est absent : warning non-bloquant. Logging avant et après.

**4. `--auto-commit` / `--auto-push` dans `auto_run()`**
Deux nouveaux flags opt-in. Après une transition d'état réussie, `--auto-commit` déclenche `commit_ticket()`, puis `--auto-push` déclenche `push_branch()` si le commit a réussi. Un échec ne modifie pas l'état déjà sauvegardé — warning seulement.

### Risques identifiés
- `load_state()` absent dans commit/push → fallback/warning, pas d'erreur fatale
- Renommage `--branch` → casse potentielle de scripts existants (faible, outil interne)
- `--auto-commit` borné à `runs/TXXX/` uniquement (pas de `git add .` aveugle)
