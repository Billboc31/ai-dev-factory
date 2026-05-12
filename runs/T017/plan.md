Le plan est produit dans `runs/T017/plan.md`. Voici le résumé :

---

## Plan T017 — Workflow-aware commit and push

### Problème identifié

`commit_ticket()` (ligne 162) ne stage que `runs/TXXX/` via `git add {run_dir}`. Les changements dans `tools/`, `tests/`, `prompts/`, `tickets/`, `docs/`, `ai/` restent hors du checkpoint, forçant un staging manuel.

### Solution retenue : `--include-code`

Un seul flag opt-in `--include-code` étend le staging à une liste de chemins bornés (`COMMIT_SCOPE`). `--auto-commit` reste inchangé (ne passe jamais `include_code=True`).

### Étapes (2 fichiers, 6 changements bornés)

1. **Constante `COMMIT_SCOPE`** — liste figée des chemins autorisés (`tools/`, `tests/`, `prompts/`, `tickets/`, `docs/`, `ai/`)
2. **Paramètre `include_code=False`** sur `commit_ticket()` — si `True`, stage chaque chemin de `COMMIT_SCOPE` individuellement, jamais `git add .`
3. **Warning fichiers hors scope** — détectés via diff entre `git status` global et `COMMIT_SCOPE`, affichés et logés mais jamais stagés silencieusement
4. **Flag `--include-code`** dans `parse_args()` + passage dans `main()`
5. **Dirty-tree warning sur `--push`** — avertissement non bloquant si working tree sale au moment du push
6. **`tests/test_commit_push.py`** — 10 tests couvrant staging borné, refus hors scope, mauvaise branche, dirty-tree

### Risques

- Fichiers non liés présents dans `tools/` : mitigé par affichage de la liste avant commit
- Régression `--auto-commit` : impossible, `include_code` vaut `False` par défaut
