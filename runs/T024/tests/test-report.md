# Test Report — T024 Daemon GitHub Issue Polling

**Date:** 2026-05-15  
**State avant test:** IMPLEMENTATION_APPROVED  
**Résultat:** PASS — tous les critères d'acceptation sont satisfaits

---

## Commandes exécutées

```bash
python -m pytest tests/test_daemon_issue_polling.py -v
# → 39 passed in 0.03s

python -m pytest tests/ -v
# → 166 passed in 0.11s (suite complète, aucune régression)
```

---

## Critères d'acceptation

| Critère | Statut | Evidence |
|---|---|---|
| Le daemon peut détecter une issue prête | PASS | `fetch_ready_issues()` appelle `gh issue list --label <label> --json number,title --state open`. Testé : `test_fetch_ready_issues_returns_parsed_issues`, `test_fetch_ready_issues_passes_label_flag`. |
| Le daemon appelle `run_issue_intake.py` | PASS | `call_issue_intake()` spawne un subprocess `run_issue_intake.py --issue N --ticket-id TXXX --branch-slug SLUG`. Testé : `test_call_issue_intake_passes_correct_args`. |
| Un run local est créé pour l'issue | PASS | Délégué intégralement à `run_issue_intake.py`. Le daemon passe les bons arguments, ne duplique aucune logique d'intake. Testé : `test_poll_github_issues_ingests_new_issue` (vérifie index mis à jour après intake réussi). |
| Une issue déjà traitée n'est pas réingérée | PASS | Index `runs/.issue-intake.json` chargé à chaque cycle, mise à jour atomique seulement après succès. Testé : `test_poll_github_issues_skips_already_ingested`, `test_poll_github_issues_does_not_update_index_on_intake_failure`. |
| Les runs locaux existants continuent d'être orchestrés | PASS | `run_once()` appelé après `poll_github_issues()` dans chaque cycle, y compris en mode `--once`. Testé : `test_main_poll_issues_flag_calls_poll_before_run_once`. |
| Les logs daemon sont explicites | PASS | Messages distincts pour : issue détectée, ignorée (déjà ingérée), ingérée avec succès, retry sur échec, aucune issue trouvée. Testé : `test_poll_github_issues_skips_already_ingested`, `test_poll_github_issues_logs_retry_on_intake_failure`, `test_poll_github_issues_no_issues_found_logs`. |
| Le comportement peut être testé sans appeler réellement GitHub | PASS | 39 tests, tous avec mocks. `test_fetch_ready_issues_returns_empty_when_gh_not_found` vérifie la dégradation gracieuse si `gh` est absent. |

---

## Régressions

Aucune. La suite complète (166 tests) passe sans modification.

- `tests/test_run_daemon.py` : 19 tests existants — tous PASS
- `tests/test_run_issue_intake.py` : 16 tests existants — tous PASS
- Autres suites (commit_push, human_approval, prompt_resolution, etc.) : inchangés

---

## Observations

Les points suivants ont déjà été signalés en review d'implémentation. Ils sont confirmés ici mais non bloquants :

1. **`--dry-run` non propagé à `poll_github_issues`** — En mode `--dry-run --poll-issues`, `call_issue_intake` est appelé réellement. Hors scope T024, à adresser dans un ticket dédié.

2. **Log potentiellement ambigu après échec `gh`** — `"gh issue list failed"` suivi de `"no issues found with label=..."` s'affichent ensemble. Lisible mais légèrement redondant.

Ces deux points ne bloquent pas la validation.

---

## Conclusion

TEST_COMPLETE — l'implémentation satisfait l'ensemble des critères d'acceptation du ticket T024. Aucune régression détectée. Le comportement est couvert par des tests reproductibles sans accès réseau.
