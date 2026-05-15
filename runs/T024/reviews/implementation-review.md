---

## Review — T024 Daemon GitHub Issue Polling

### Résumé

L'implémentation est conforme au ticket et au plan. Les 7 fonctions planifiées sont présentes, le wiring CLI est correct, et les 39 tests couvrent tous les cas nominaux et d'erreur sans appel réel à GitHub ou git. Aucun problème bloquant n'est identifié.

---

### Critères d'acceptation

| Critère | Statut |
|---|---|
| Détecter une issue prête | ✅ `fetch_ready_issues` via `gh issue list --label` |
| Appeler `run_issue_intake.py` | ✅ `call_issue_intake` — subprocess, sans duplication logique |
| Run local créé pour l'issue | ✅ délégué à `run_issue_intake.py`, daemon n'y touche pas |
| Anti-doublon | ✅ index `runs/.issue-intake.json`, écriture atomique via rename |
| Runs locaux existants orchestrés | ✅ `run_once()` conservé, appelé après `poll_github_issues` |
| Logs explicites | ✅ détectée / ignorée / ingérée / retry — distincts |
| Testable sans GitHub | ✅ tous les subprocesses mockés |

---

### Conformité au plan

Toutes les 8 étapes du plan sont implémentées. Un écart positif par rapport au plan :

- `next_ticket_id` accepte un `reserved: set[str]` optionnel, permettant d'assigner des IDs séquentiels corrects quand plusieurs issues sont ingérées dans le même cycle. Le plan ne couvrait que le cas single-issue par cycle. La correction est juste et bornée.

---

### Code quality

**Points positifs :**

- Fonctions courtes et à responsabilité unique — `fetch_ready_issues`, `call_issue_intake`, `poll_github_issues` sont clairement séparées.
- Dégradation gracieuse si `gh` est absent (`FileNotFoundError` capturé), si `gh` échoue (`returncode != 0`), ou si le JSON est invalide.
- Écriture atomique de l'index via `tmp.replace(path)` — correct sur POSIX.
- Pas de `shell=True`, pas d'interpolation de données externes dans les commandes — aucune injection possible.
- L'index n'est mis à jour qu'après succès d'intake — retry automatique au prochain cycle en cas d'échec.

**Observations mineures (non bloquantes) :**

1. **`--dry-run` n'est pas propagé à `poll_github_issues`** (`run_daemon.py:289-298`). En mode `--dry-run --poll-issues`, `call_issue_intake` est quand même appelé et crée des runs réels. C'est une incohérence du contrat dry-run, mais ce cas combiné n'est pas dans les critères du ticket. Peut être adressé dans un ticket dédié.

2. **Log ambigu quand `gh` échoue** : `fetch_ready_issues` logue `"gh issue list failed"` puis retourne `[]`, et `poll_github_issues` logue ensuite `"no issues found with label=..."`. Les deux messages apparaissent ensemble, ce qui est suffisant, mais "no issues found" peut prêter à confusion après un échec. Mineur.

3. **`ROOT` pointe sur `tools/agent_runner/`** (`run_daemon.py:21`) — correct puisque `run_ticket.py` et `run_issue_intake.py` sont dans le même répertoire. Aucun problème.

---

### Sécurité

- Aucun secret hardcodé.
- Pas de données sensibles dans les logs (numéros d'issue et titres sont des données publiques GitHub).
- Aucune opération destructive implicite.
- Subprocesses appelés avec liste d'args (pas de shell), `check=False` explicite.

---

### Scope

Uniquement deux fichiers modifiés : `tools/agent_runner/run_daemon.py` et `tests/test_daemon_issue_polling.py` (nouveau). Aucune dérive vers les éléments hors scope (PR auto, labels, fermeture d'issue, etc.).

---

### Tests

39 tests, organisés par fonction. Couverture : cas nominaux, cas d'erreur (`gh` absent, JSON invalide, intake échoué), CLI (label, repo, dry-run absent, appel poll avant run_once). Pas d'appel réseau ou git réel. Les tests `test_poll_github_issues_multiple_issues_sequential_ids` et `test_next_ticket_id_ignores_non_ticket_dirs` valident les edge cases pertinents.

---

### Conclusion

Implémentation correcte, bornée au scope du ticket, robuste sur les chemins d'erreur, bien testée. Les deux observations mineures ci-dessus ne justifient pas un blocage.

IMPLEMENTATION_APPROVED
