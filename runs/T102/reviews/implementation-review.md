I have a complete picture. Writing the review now.

---

# PR Review — T102

## Résumé

L'implémentation couvre les 5 travaux demandés : synchronisation Git avant intake, politique de capacité `max_active_tickets`, sélection de la première issue candidate, endpoint `GET /daemon/board`, et page Board dans le dashboard. Le scope est respecté, aucune DB externe n'a été introduite, pas de `git add .`. Un problème de séquencement dans `poll_github_issues` nécessite une correction avant approbation.

---

## Vérifications effectuées

- Lecture complète de `run_daemon.py`, `board_service.py`, `schemas.py`, `routes/daemon.py`, `BoardPage.jsx`, `api/daemon.js`
- Comparaison avec les 8 critères d'acceptation du ticket
- Vérification des contraintes (pas de DB, Git source de vérité, pas de git add ., pas d'auto-merge)
- Vérification du plan (7 étapes, 7 fichiers)

---

## Points validés

- **Git sync** : `_sync_main_before_intake()` vérifie `git status --porcelain`, classe les fichiers, refuse checkout si fichiers inconnus (safe abort), puis `git checkout main` + `git pull origin main` avec logs explicites ligne par ligne. Contraintes de sécurité respectées.
- **Capacité** : `_count_active_tickets()` compte les tickets non archivés/non fermés. Comparaison `active >= max_active_tickets` correcte. Flag `--max-active-tickets` CLI ajouté avec default 1.
- **Sélection single-issue** : tri par numéro croissant, intake du premier candidat uniquement, les autres loggés `queued` ou `skipped-for-capacity`. Design extensible via le tri.
- **API board** : `GET /daemon/board` retourne 7 colonnes avec classification stricte par priorité (done → pr_ready → waiting_human → blocked → running → queued → backlog). Projection pure, pas de nouvelle source de vérité. Backlog = issues non ingérées via `gh issue list`, failure silencieuse (colonne vide, pas d'erreur 500).
- **UI board** : `BoardPage.jsx` 7 colonnes, code-couleur, polling 10s via `usePolling`, lien ticket_id vers `/tickets/:id`, route `/board` et nav ajoutés dans `App.jsx`.
- **Qualité** : fonctions courtes, nommage explicite, erreurs gérées explicitement, logs utiles, aucune dépendance nouvelle.
- **Scope** : aucune dérive détectée, `run_ticket.py` non modifié, pas de DB.

---

## Problèmes détectés

### [BLOQUANT] `_sync_main_before_intake()` appelée inconditionnellement à chaque cycle de polling

**Fichier** : `tools/agent_runner/run_daemon.py:813`

```python
def poll_github_issues(...):
    if not _sync_main_before_intake():   # ← toujours appelé
        _log("issue intake aborted — git sync failed")
        return
    issues = fetch_ready_issues(label, repo)
    ...
    active = _count_active_tickets(runs_dir)
    if active >= max_active_tickets:
        # log skipped-for-capacity
        return
    # intake
```

La synchronisation Git (`git checkout main` + `git pull origin main`) s'exécute à **chaque cycle de 30 secondes**, même quand :
- toutes les issues sont déjà ingérées (pas de candidats)
- la capacité est pleine (`active >= max_active_tickets`)
- il n'y a aucune issue `ai-ready`

Le ticket spécifie : *"Avant tout intake d'une issue GitHub : checkout main, pull origin main, then run issue intake"*. La synchronisation doit être une précondition de l'intake, pas une précondition de la vérification des issues.

En mode continu, cela provoque un `git checkout main` toutes les 30 secondes en état stable (quand un ticket est en cours de traitement), ce qui est perturbateur pour un développeur travaillant sur une branche ticket et génère des appels réseau (`git pull`) sans utilité.

**Correction** : déplacer `_sync_main_before_intake()` après la vérification des candidats et de la capacité, juste avant l'intake effectif :

```python
def poll_github_issues(...):
    issues = fetch_ready_issues(label, repo)
    if not issues:
        return
    index = load_issue_index(runs_dir)
    candidates = sorted([i for i in issues if str(i["number"]) not in index], key=lambda i: i["number"])
    already_ingested = [i for i in issues if str(i["number"]) in index]
    for issue in already_ingested:
        _log(f"issue #{issue['number']} already ingested as {index[str(issue['number'])]} — skipping")
    if not candidates:
        _log(f"found {len(issues)} issue(s) with label={label!r} — all already ingested")
        return
    active = _count_active_tickets(runs_dir)
    _log(f"found {len(candidates)} candidate issue(s) active_tickets={active} max_active_tickets={max_active_tickets}")
    if active >= max_active_tickets:
        for issue in candidates:
            _log(f"issue #{issue['number']} ({issue.get('title', '')!r}) skipped-for-capacity active={active} max={max_active_tickets}")
        return
    # Sync main uniquement si on est effectivement sur le point d'intaker
    if not _sync_main_before_intake():
        _log("issue intake aborted — git sync failed")
        return
    issue = candidates[0]
    ...
```

---

### [MINEUR] `BoardItem.title` non renseigné pour les tickets ingérés

**Fichier** : `services/control_api/services/board_service.py:83-88`

Le `title` des tickets n'est pas peuplé dans `BoardItem` — seules les items `backlog` (issues GitHub) ont un titre. Les cartes de tickets affichent `state` ou `branch` en sous-titre (`BoardPage.jsx:34`). Fonctionnel, mais moins lisible. Le titre est disponible dans `runs/{ticket_id}/ticket.md` (première ligne `# ...`) mais pas dans `state.json`. À adresser dans un ticket dédié ou en enrichissant `state.json` lors de l'intake.

---

### [MINEUR] `GET /daemon/board` ne transmet pas `repo` au service

**Fichier** : `services/control_api/routes/daemon.py:40-41`

```python
def daemon_board(request: Request) -> BoardResponse:
    return board_service.get_board(_root(request))
```

`repo` n'est pas passé : `get_board` utilise `repo=None`, donc `gh issue list` s'exécute sans `--repo`. Acceptable en V1 (repo implicite via contexte Git), mais pas extensible si la Control API doit servir plusieurs repos. À documenter ou à corriger si le pattern `request.app.state.repo` est ajouté.

---

## Risques éventuels

- En mode `--once` avec `--poll-issues`, le `_sync_main_before_intake()` inconditionnelle est moins problématique (exécution unique), mais le même problème de séquencement existe.
- Les tickets en `cooldown` (retry-state.json a `cooldown_until` mais pas `stopped=true`) apparaissent en colonne `queued` du board, ce qui peut être trompeur. Comportement accepté par le plan (7 colonnes sans colonne cooldown dédiée).

---

## Décision

Une correction est requise sur le séquencement de `_sync_main_before_intake()` dans `poll_github_issues`. La correction est localisée, à faible risque, et ne nécessite pas de refactoring structurel.

## Actions demandées

1. **[BLOQUANT]** Dans `poll_github_issues` (`run_daemon.py`), déplacer l'appel à `_sync_main_before_intake()` après la vérification des candidats et de la capacité, juste avant l'appel à `call_issue_intake`. Supprimer le `return` early actuel au début de la fonction.

2. **[OPTIONNEL / V2]** Peupler `BoardItem.title` depuis `runs/{ticket_id}/ticket.md` dans `board_service.py`.

3. **[OPTIONNEL / V2]** Transmettre `repo` depuis `app.state` dans `daemon_board` si un pattern multi-repo est envisagé.

---

IMPLEMENTATION_FIX_REQUIRED
