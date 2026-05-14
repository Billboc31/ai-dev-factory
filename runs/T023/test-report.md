# Test Report — T023 GitHub issue intake

## Résumé

Validation complète. Tous les critères d'acceptation sont satisfaits. Aucune régression détectée.

## Suite de tests

```
20 passed  tests/test_run_issue_intake.py  (0.02s)
87 passed  reste de la suite               (0.09s)
─────────────────────────────────────────────────
107 passed total — 0 failed
```

## Critères d'acceptation

| Critère | Statut | Vérification |
|---|---|---|
| Une issue GitHub peut créer un run local | ✅ PASS | `test_happy_path` : `rc=0`, artefacts créés dans `tmp_path` |
| `ticket.md` correctement généré | ✅ PASS | `test_ticket_md_format` : titre, source, body présents |
| Branche ticket créée | ✅ PASS | `test_branch_name_basic/slugifies` + `test_happy_path` : `git checkout -b` appelé avec le bon nom |
| `state.json` initialisé | ✅ PASS | `test_state_json_format` : `state=INIT`, `ticket_id`, `branch`, `updated_at` |
| Logs explicites | ✅ PASS | Stdout verbeux + `runtime.log` créé (`test_happy_path`) |
| Workflow existant compatible | ✅ PASS | `run_ticket.py` inchangé (0 commit sur la branche) — 87 tests du reste de la suite verts |

## Interface CLI

```
usage: run_issue_intake.py --issue ISSUE --ticket-id TICKET_ID
                           --branch-slug BRANCH_SLUG [--repo REPO]
```

Correspond exactement à l'exemple du ticket :

```bash
python tools/agent_runner/run_issue_intake.py \
  --issue 123 \
  --ticket-id T023 \
  --branch-slug github-issue-intake
```

## Guards (erreurs attendues)

| Cas | Comportement | Statut |
|---|---|---|
| ticket-id invalide (BAD, T1, t007…) | `rc=2` + message explicite | ✅ |
| `state.json` déjà présent | `rc=2` + "state.json already exists" | ✅ |
| working tree dirty | `rc=2` + "working tree is not clean" | ✅ |
| branche déjà existante | `rc=2` + "already exists" | ✅ |
| `gh` auth failure | `rc=2` + hint "gh auth login" | ✅ |

## Régressions

Aucune. Les 87 tests existants passent tous sans modification.

## Anomalies détectées

Aucune anomalie bloquante.

**Observation mineure (non bloquante)** — si `gh` n'est pas installé, `subprocess.run()` lève un `FileNotFoundError` non rattrapé par `IntakeError`. L'erreur est lisible mais le message est moins orienté utilisateur qu'un check explicite. Hors scope du ticket.

## Décision

TESTS_PASSED
