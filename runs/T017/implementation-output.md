43/43 pass, zero regressions. Here's the implementation summary:

---

## Résumé des changements

### Fichiers modifiés

**`tools/agent_runner/run_ticket.py`** — 5 changements bornés :

1. **`COMMIT_SCOPE`** (constante) — tuple figé de 6 chemins autorisés : `tools/`, `tests/`, `prompts/`, `tickets/`, `docs/`, `ai/`

2. **`_warn_out_of_scope(ticket_id, run_dir)`** (nouvelle fonction) — parse `git status --porcelain` global, identifie les fichiers hors `run_dir` et `COMMIT_SCOPE`, les affiche et les logue sans jamais les stager

3. **`commit_ticket(ticket_id, message, include_code=False)`** — 3 ajouts :
   - validation branche vs `state.json` en tête de fonction (refus rc=2 si mismatch)
   - staging étendu à `COMMIT_SCOPE` si `include_code=True`, chemin par chemin — jamais `git add .`
   - appel `_warn_out_of_scope` si `include_code=True`

4. **`push_branch()`** — warning non-bloquant si working tree sale au moment du push

5. **`parse_args()` / `main()`** — flag `--include-code` ajouté, transmis à `commit_ticket`

### Fichier créé

**`tests/test_commit_push.py`** — 12 tests couvrant :
- `COMMIT_SCOPE` ne contient pas `.` ou `*`
- refus commit sur mauvaise branche (rc=2)
- succès sur branche correcte
- absence de `git add .` dans tous les appels
- `include_code=False` : seul `runs/T999/` stagé
- `include_code=True` : tous les chemins `COMMIT_SCOPE` stagés
- rien à committer → rc=1
- warning fichiers hors scope (ex: `secret.env`) sans stager `tools/`
- refus push sur mauvaise branche
- warning dirty tree sur push (non-bloquant, rc=0)
- push cible uniquement la branche ticket

### Compatibilité

- `--auto-commit` appelle `commit_ticket(ticket_id, None)` sans `include_code` → comportement inchangé
- fix loops, review loops, `--auto-init`, `--ensure-branch` : aucune modification
