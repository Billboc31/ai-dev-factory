Le plan est écrit dans `runs/T024/plan.md`. Voici le résumé :

---

## Plan T024 — Daemon GitHub issue polling

**Fichiers impactés :** `tools/agent_runner/run_daemon.py` (modifié) + `tests/test_daemon_issue_polling.py` (créé). Rien d'autre.

**8 étapes :**

1. **CLI** — 3 nouveaux args : `--poll-issues` (flag), `--issue-label` (défaut `ai-ready`), `--issue-repo` (optionnel)
2. **Index anti-doublon** — `runs/.issue-intake.json` : `{"42": "T025"}`. Lecture/écriture atomique via `load_issue_index` / `save_issue_index`.
3. **`next_ticket_id`** — globbe `runs/T*/`, prend le max + 1, zero-pad à 3 chiffres.
4. **`slugify_title`** — lowercase, remplace non-alphanum par `-`, tronque à 50 chars, fallback `"issue"`.
5. **`fetch_ready_issues`** — appelle `gh issue list --json number,title`, retourne `[]` silencieusement si `gh` est absent ou en erreur.
6. **`call_issue_intake`** — subprocess `run_issue_intake.py --issue N --ticket-id TXXX --branch-slug SLUG`, retourne bool succès.
7. **`poll_github_issues`** — orchestre les 4 fonctions ci-dessus, met à jour l'index seulement après succès, log issues détectées/ignorées/ingérées.
8. **Intégration boucle** — `poll_github_issues()` appelé **avant** `run_once()` à chaque cycle si `--poll-issues`.

**Choix anti-doublon retenu :** index JSON explicite (`runs/.issue-intake.json`) — O(1) lookup, pas de dépendance au format de `ticket.md`, retry automatique en cas d'échec d'intake.

**Risque principal :** `run_issue_intake.py` peut échouer si le working tree est sale ou si la branche existe déjà — l'index n'est pas mis à jour, le daemon réessaiera au cycle suivant.
