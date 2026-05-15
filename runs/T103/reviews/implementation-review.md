I have read all the key implementation sections. Let me now write the formal review.

---

# PR Review — T103 — Runtime correctness hotfixes for daemon checkpoint and branch isolation

## Résumé

Troisième tentative de review sur `ticket/T103-t103-runtime-correctness-hotfixes-for-daemon-check`. Les deux blockers identifiés en review 2 (`_sync_main_before_intake` et `_count_active_tickets`/`--max-active-tickets`) ont été supprimés dans le commit `3fd16e7`. Les 4 bugs du ticket et les 2 additions du plan review sont correctement implémentés et le scope est propre.

---

## Vérifications effectuées

- Lecture complète de `run_daemon.py` sur la branche (930 lignes)
- Vérification ligne à ligne des 4 zones de correction
- Grep `_sync_main_before_intake`, `_count_active_tickets`, `max_active_tickets` → aucun match
- Vérification de `poll_github_issues()` : boucle `for issue in candidates` restaurée (tous les candidats traités)
- Lecture du `.gitignore`
- Vérification `git log --name-status` : `apps/dashboard/node_modules/` correctement sorti du tracking en `1a5e379`

---

## Bug 1 — PR créée avant push ✅

`_checkpoint_and_push_before_pr()` (lignes 539–567) : push exécuté inconditionnellement que `commit_result.returncode` soit `0` (nouveau commit) ou `1` (rien à committer — flush des commits antérieurs). `handle_test_complete()` (ligne 570–577) appelle cette fonction avant `create_or_update_pr()`. Flux conforme au ticket.

## Bug 2 — Mauvaise branche ✅

`_get_current_branch()` (lignes 639–646) via `git rev-parse --abbrev-ref HEAD`. Guard dans `launch_ticket()` (lignes 670–679) : si `current_branch != expected_branch` → skip avec log explicite, aucun checkout implicite. `_sync_ticket_branch()` appelé après le guard avec `git pull --ff-only` ; retourne `False` (skip) en cas de divergence.

## Bug 3 — Classification dirty tree ✅

`_CODE_SCOPE_PREFIXES` (lignes 236–249) couvre : `tools/`, `tests/`, `prompts/`, `tickets/`, `docs/`, `ai/`, `services/`, `apps/`, `README.md`, `.gitignore`, `package.json`, `package-lock.json`. Tous les chemins cités dans le ticket sont présents. Aucun `git add .` dans tout le fichier.

`_classify_dirty_files()` (lignes 252–281) : classification en 3 buckets explicites. Les `unknown_files` déclenchent un abort sécurisé (ligne 297–299).

## Bug 4 — Fichiers runtime dans Git ✅

`.gitignore` contient les 5 entrées requises (`runs/daemon.pid`, `runs/daemon.log`, `runs/*/workflow-status.md`, `runs/*/daemon.lock`, `apps/dashboard/node_modules/`). `apps/dashboard/node_modules/.vite/` couvert implicitement par `apps/dashboard/node_modules/`. `git rm -r --cached` exécuté dans le commit `1a5e379`.

## Plan additions ✅

**Checkpoint avant `PLAN_REVIEW_NEEDED`** : `run_once()` lignes 867–874 appelle `_checkpoint_and_push_before_pr()` avant de logger le skip human gate.

**Sync branche distante** : `_sync_ticket_branch()` (lignes 618–636) avec `ff-only pull`, appelé après le branch guard dans `launch_ticket()`.

## Out-of-scope features (review 2) ✅ Supprimées

`_sync_main_before_intake()` : absente (grep confirms). `_count_active_tickets()` + `--max-active-tickets` : absents (grep confirms). `poll_github_issues()` traite bien `for issue in candidates` (toute la liste, pas seulement `candidates[0]`).

---

## Observations mineures (non bloquantes)

**`_checkpoint_and_push_before_pr()` — nom légèrement trompeur** : la fonction est maintenant aussi appelée pour la visibilité plan (`PLAN_REVIEW_NEEDED`). Nom acceptable mais imprécis. Non bloquant.

**Branch guard contournable si `branch` absent de `state.json`** : si un ticket en état `INIT` n'a pas encore de champ `branch`, le guard est skippé. Comportement correct pour les premiers états du lifecycle, mais à documenter si le système évolue vers des workers parallèles.

---

## Critères d'acceptation

| Critère | Statut |
|---|---|
| PR créée uniquement après checkpoint/push propre | ✅ |
| Daemon ne tente plus d'agir sur le mauvais ticket/branche | ✅ |
| Fichiers projet normaux sont checkpointables | ✅ |
| Vrais fichiers inconnus bloquent le daemon | ✅ |
| Fichiers runtime ne polluent plus Git | ✅ |
| Aucun `git add .` | ✅ |

---

IMPLEMENTATION_APPROVED
