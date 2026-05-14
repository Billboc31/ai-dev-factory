I have everything I need. Here is the implementation review.

---

# PR Review — T023 GitHub issue intake

## Résumé

L'implémentation produit un script `run_issue_intake.py` de 199 lignes qui transforme une GitHub Issue en artefacts locaux (`ticket.md`, `state.json`, branche) prêts pour `run_ticket.py`. Le périmètre est strictement respecté, l'architecture séparée, les tests exhaustifs et tous verts.

## Vérifications effectuées

- Lecture complète de `tools/agent_runner/run_issue_intake.py` (199 lignes)
- Lecture complète de `tests/test_run_issue_intake.py` (239 lignes)
- Vérification que `run_ticket.py` est inchangé
- Exécution de la suite de tests : **20/20 passed** (0.02s)
- Contrôle du format `ticket.md` et `state.json` générés
- Contrôle de la compatibilité CLI avec l'exemple du ticket

## Points validés

**Critères d'acceptation — tous satisfaits**

| Critère | Statut |
|---|---|
| Issue GitHub → run local | ✅ |
| `ticket.md` correctement généré | ✅ |
| Branche ticket créée | ✅ |
| `state.json` initialisé à `INIT` | ✅ |
| Logs explicites (stdout + runtime.log) | ✅ |
| Workflow existant compatible | ✅ |

**Interface CLI**

L'interface correspond exactement à l'exemple du ticket : `--issue`, `--ticket-id`, `--branch-slug`, `--repo` optionnel.

**Séparation des responsabilités**

`run_issue_intake.py` n'importe rien de `run_ticket.py`. Aucun import partagé, aucune dépendance croisée. Dépendances : stdlib uniquement (`argparse`, `datetime`, `json`, `re`, `subprocess`, `pathlib`).

**Guards séquentiels (ordre correct)**

```
validate_ticket_id → check_state_absent → check_working_tree_clean
→ fetch_issue → create_branch → write_ticket_md → write_state_json
```

Chaque garde échoue proprement (rc=2) sans laisser d'état partiel visible — `state.json` n'est jamais créé si une étape antérieure échoue.

**Écriture atomique de `state.json`**

Utilisation du pattern tmp → rename (`path.name + ".tmp"` → rename) : correct et safe.

**Sécurité subprocess**

`_run()` utilise la forme liste (pas `shell=True`), `capture_output=True`. Aucune injection de commande possible via le titre ou le body de l'issue.

**Tests**

20 cas couvrant : validation ticket_id, slugification, fetch avec/sans `--repo`, auth hint, happy path, format `ticket.md`, format `state.json`, les 3 guards (state existant, tree dirty, branche existante). Isolation correcte via `tmp_path` + `os.chdir()`.

## Problèmes détectés

Aucun problème bloquant.

## Risques éventuels

**Mineur — absence de check de disponibilité de `gh`**

Si `gh` n'est pas installé, le script échoue avec un `FileNotFoundError` non contrôlé au niveau de `subprocess.run()`, non capturé par `IntakeError`. L'erreur reste lisible mais le message est moins orienté utilisateur qu'un check explicite. Acceptable pour un intake manuel.

**Mineur — issue sans body**

`data.get("body", "")` accepte silencieusement un body vide (possible sur GitHub). Le `ticket.md` généré aura une section `## Description` vide. C'est un cas valide que le planner devra gérer — comportement acceptable.

**Observation — ordre fetch/create_branch**

Le `fetch_issue()` s'exécute avant `create_branch()`. Si le fetch réussit mais la création de branche échoue, aucun artefact n'a été écrit (correct). L'ordre est sûr.

## Décision

- APPROVED

## Actions demandées

Aucune correction requise. L'implémentation est prête pour la phase suivante (Memory updater).

IMPLEMENTATION_APPROVED
