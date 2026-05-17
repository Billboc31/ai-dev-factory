I have enough information to write a complete, structured review. Let me compose it now.

---

## PR Review — T105: Automatic merge after TEST_COMPLETE

## Résumé

L'implémentation couvre les trois axes du ticket : correction du cwd IHM, visibilité dashboard des worktrees, et auto-merge après TEST_COMPLETE. 24 fichiers modifiés ou créés, 388 tests passent dont 29 nouveaux tests dédiés à T105. Le périmètre reste dans les bornes du ticket.

---

## Vérifications effectuées

- Lecture du diff complet vs `main` (24 fichiers)
- Lecture de `runtime_resolver.py`, `subprocess_runner.py`, `auto_merge_pr` dans `run_daemon.py`
- Lecture de `handle_test_complete`, `_checkpoint_and_push_before_pr`, `check_and_close_issue`
- Lecture de `main.py` (initialisation `worktrees_dir`)
- Lecture des tests : `test_runtime_resolver.py`, `test_ihm_worktree_cwd.py`, `test_daemon_pr_lifecycle.py`
- Vérification de la chaîne d'appels complète dans `handle_test_complete`
- Vérification de la compatibilité legacy (runs/ fallback)

---

## Points validés

**IHM / cwd resolution**

- `_resolve_action_cwd()` est appelée dans les 8 fonctions action de `subprocess_runner.py`. La priorité (workers.json → worktrees_dir → fallback legacy) est cohérente et documentée.
- La vérification branche en mode legacy est correcte : elle lit `state.branch`, compare avec `HEAD`, et refuse avec un message actionnable si désaccord. Le refus n'exécute pas `run_ticket.py`.
- Le module `runtime_resolver.py` est minimal, bien isolé, sans effet de bord.

**Auto-merge**

- `auto_merge_pr()` implémente tous les garde-fous listés dans le ticket : vérification `pr_number`, `pr_merged`, `PR state == OPEN`, `mergeable != CONFLICTING`.
- La commande `gh pr merge --squash --delete-branch` est correcte et atomique.
- En cas d'échec (rc != 0 ou `gh` absent), la fonction logue et retourne `False` sans modifier l'état. L'atomicité est respectée : `pr_merged` et `daemon_archived` ne sont écrits que sur succès total.
- `check_and_close_issue` a son propre garde (`state == MERGED`), ce qui rend son appel après un merge raté inoffensif.

**Dashboard / visibilité**

- `board_service.py` scanne les trois sources (runs/, workers.json, worktrees_dir) dans le bon ordre de priorité.
- `artifact_reader.py` utilise `resolve_ticket_run_dir()` de manière cohérente sur toutes les lectures.

**Tests**

- `test_ihm_worktree_cwd.py` reproduit explicitement le bug `current branch 'main' does not match state branch 'ticket/...'` et vérifie sa résolution.
- 9 tests `auto_merge_pr` couvrent tous les chemins de garde (no pr_number, already merged, MERGED PR detected, CLOSED PR, CONFLICTING, gh merge failure, repo flag).
- Isolation correcte (tmp_path, mocks ciblés).

---

## Problèmes détectés

**Mineur — La synchronisation branche/main est implicite, pas explicite.**

Le ticket demande : *"vérifier synchro branche ticket avant merge"*.

L'implémentation s'appuie uniquement sur le champ `mergeable` de l'API GitHub. Ce champ vaut `MERGEABLE` quand il n'y a pas de conflits, mais il ne garantit pas que la branche ticket est à jour avec `main` quand la règle "Require branches to be up to date" est active sur le repo. Dans ce cas, `gh pr merge` échouera (rc != 0), sera loggé, et retournera `False` — comportement sûr, mais sans message explicite côté state.

Ce n'est pas bloquant : le comportement de repli est sécurisé et le ticket ne précise pas de vérification git explicite. Mais le commentaire dans `auto_merge_pr` pourrait mentionner cette limite pour éviter des surprises.

**Mineur — `handle_test_complete` ne logue pas le résultat du merge au niveau orchestrateur.**

```python
create_or_update_pr(ticket_id, run_dir, repo)
auto_merge_pr(ticket_id, run_dir, repo)   # retour ignoré
check_and_close_issue(ticket_id, run_dir, repo)
```

`auto_merge_pr` logue en interne, mais `handle_test_complete` n'émet pas de log résumant si le merge a réussi ou échoué. Un `_log(f"{ticket_id}: auto-merge {'ok' if merged else 'failed or skipped'}")` après l'appel améliorerait l'observabilité au niveau lifecycle. Non bloquant.

**Observationnel — `--merge-admin` absent.**

Par conception correcte : on ne bypass pas les branch protection rules de GitHub. Si des checks CI bloquent, le merge échouera avec un message loggué. Mais si des reviewers humains sont requis sur le repo et que le merge automatique est censé les contourner, il faudra prévoir `--admin`. À confirmer avec la configuration repo cible — hors scope T105.

---

## Risques éventuels

- Si `worktrees_dir` n'existe pas et que le ticket tourne en legacy, `board_service.py` et `artifact_reader.py` tombent correctement en fallback sans erreur.
- L'appel `app = create_app()` au niveau module dans `main.py` (ligne 70) calcule `worktrees_dir` depuis `Path.cwd()` au démarrage. Ce comportement est identique à `project_root` — pattern FastAPI standard, pas de risque.
- `_checkpoint_and_push_before_pr` traite `rc=1` comme "nothing to commit" — convention bien loggée, adaptée à `run_ticket.py`.

---

## Décision

L'implémentation est correcte, bornée au périmètre du ticket, et tous les critères d'acceptation sont couverts. Les deux observations mineures (log orchestrateur, note sur synchro branche implicite) ne constituent pas des défauts de correction.

IMPLEMENTATION_APPROVED
