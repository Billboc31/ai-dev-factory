I have now fully reviewed all implementation files. Let me write the review.

---

## PR Review — T031 (attempt 2) : Daemon terminal-ticket skip and commit/checkpoint hardening

### Résumé

Les trois blocqueurs remontés par la review précédente sont tous corrigés. L'implémentation est complète, dans le scope, sécurisée, et correctement testée. Aucun nouveau problème bloquant n'est détecté.

---

### Vérifications effectuées

- `tools/agent_runner/run_ticket.py` — `COMMIT_SCOPE`, `archive_daemon()`, argparse `--archive-daemon`, `--checkpoint`
- `tools/agent_runner/run_daemon.py` — `scan_tickets()`, `create_or_update_pr()`, `run_once()` guard TEST_COMPLETE
- `services/control_api/services/subprocess_runner.py` — `commit_ticket()`, `checkpoint_ticket()`, `archive_ticket()`
- `services/control_api/routes/tickets.py` — endpoint `POST /tickets/{id}/archive`
- `apps/dashboard/src/api/tickets.js` — `archiveDaemon()`
- `apps/dashboard/src/pages/TicketDetailPage.jsx` — bouton "Archive daemon"
- `tests/test_run_daemon.py`, `tests/test_daemon_pr_lifecycle.py`, `tests/test_commit_push.py`, `tests/test_control_api_subprocess.py`

---

### Résolution des blocqueurs précédents

**[RÉSOLU] COMMIT_SCOPE incomplet** — `run_ticket.py:88-89` inclut désormais `"package.json"` et `"package-lock.json"`. Conforme au ticket §8 et au plan.

**[RÉSOLU] Test manquant `pr_skipped_no_diff` dans `run_once`** — `test_run_daemon.py:137-147` : `test_run_once_skips_test_complete_when_pr_skipped_no_diff` présent, sans `daemon_archived` dans le state (ce qui est correct — force le passage par la garde de `run_once` plutôt que le filtre de `scan_tickets`). ✓

**[RÉSOLU] Test manquant `package.json` dans COMMIT_SCOPE** — `test_commit_push.py:64-66` : `test_commit_scope_contains_package_json` présent et correct. ✓

---

### Points validés

**Daemon skip `daemon_archived`** — `scan_tickets()` (run_daemon.py:432-434) filtre immédiatement les tickets `daemon_archived=true` avec log explicite. ✓

**Détection no-diff + marquage terminal** — `create_or_update_pr()` (run_daemon.py:345-349) détecte `"No commits between"` dans stderr et persiste simultanément `pr_skipped_no_diff=true` + `daemon_archived=true`. Le ticket ne sera plus retraité à aucun cycle. ✓

**Guard TEST_COMPLETE** — `run_once()` (run_daemon.py:631) vérifie `issue_closed` ou `pr_skipped_no_diff` avant de déclencher `handle_test_complete()`. ✓

**`archive_daemon()`** (run_ticket.py:324-344) — écriture atomique via tmp+rename, log dans `runtime.log`, validation de l'existence de `state.json`. ✓

**`--archive-daemon` CLI** (run_ticket.py:858, 892-893) — dispatch correct vers `archive_daemon()`. ✓

**`--checkpoint` alias** (run_ticket.py:855, 901) — alias vers `commit_ticket()` ajouté et fonctionnel. ✓

**API archive** — `archive_ticket()` (subprocess_runner.py:121-127) appelle `--archive-daemon` ; endpoint `POST /tickets/{ticket_id}/archive` (routes/tickets.py:160-164) correctement câblé. ✓

**commit/checkpoint avec `--include-code`** — `commit_ticket()` (subprocess_runner.py:98) et `checkpoint_ticket()` (subprocess_runner.py:116) passent tous deux `--commit --include-code`. ✓

**Dashboard "Archive daemon"** — `archiveDaemon()` (tickets.js:22) et bouton `variant="danger"` dans `TicketDetailPage.jsx:163`. ✓

**Sécurité git** — aucun `git add .`. Chaque path de `COMMIT_SCOPE` est stagé individuellement (run_ticket.py:265-270). Validation ticket ID avec `re.fullmatch(r"T\d{3,}")` dans run_ticket.py et subprocess_runner.py. ✓

**Couverture tests complète** (ticket §9) :
- `test_scan_tickets_skips_daemon_archived` ✓
- `test_scan_tickets_skips_daemon_archived_logs_message` ✓
- `test_create_or_update_pr_marks_archived_on_no_diff_error` ✓
- `test_create_or_update_pr_does_not_mark_archived_on_other_error` ✓
- `test_run_once_skips_test_complete_when_issue_closed` ✓
- `test_run_once_skips_test_complete_when_pr_skipped_no_diff` ✓ *(nouveau)*
- `test_archive_daemon_writes_daemon_archived_flag` ✓
- `test_archive_daemon_returns_2_when_state_missing` ✓
- `test_commit_ticket_includes_include_code_flag` ✓
- `test_checkpoint_ticket_uses_commit_with_include_code` ✓
- `test_archive_ticket_calls_archive_daemon_flag` ✓
- `test_commit_scope_contains_apps_and_services` ✓
- `test_commit_scope_contains_package_json` ✓ *(nouveau)*
- `test_commit_never_calls_git_add_dot` ✓

---

### Observations mineures (non-bloquantes)

**`subprocess_runner.checkpoint_ticket()` appelle `--commit` et non `--checkpoint`** — cohérent et correct : l'alias `--checkpoint` existe pour l'usage CLI humain, le runner API peut appeler directement `--commit`. Les deux chemins appellent `commit_ticket()` dans run_ticket.py, le comportement est identique.

**`COMMIT_SCOPE` inclut `"runs/"`** — ce path est stagé séparément comme `runs/TXXX/` lors du commit, il n'est donc pas doublé ; la présence dans COMMIT_SCOPE ne cause pas de problème car le code filtre correctement.

---

### Risques résiduels

Aucun risque de sécurité identifié. La logique de skip est conservative (rate plutôt qu'excès). Le bouton "Archive daemon" est en `variant="danger"`, signalétique adaptée à une action irréversible sur le cycle daemon.

---

### Décision

Tous les critères d'acceptation du ticket sont satisfaits. Les trois blocqueurs de la review précédente sont corrigés. Aucune dérive de scope. Aucun comportement git dangereux.

IMPLEMENTATION_APPROVED
