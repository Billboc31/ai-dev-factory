All checks pass. Here is the test report:

---

## Test Report — T017 Workflow-Aware Commit and Push

### Tests formels

```
tests/test_commit_push.py — 12/12 PASSED
Full suite — 43/43 PASSED (zero regressions)
```

### Validation par critère d'acceptation

| Critère | Résultat |
|---|---|
| `COMMIT_SCOPE` borné (pas de `.` ni `*`) | PASS |
| Refus commit mauvaise branche (rc=2) | PASS |
| Commit branche correcte (rc=0) | PASS |
| Jamais `git add .` | PASS |
| `include_code=False` → seul `runs/TXXX/` stagé | PASS |
| `include_code=True` → `runs/` + tous les chemins COMMIT_SCOPE | PASS |
| Rien à committer → rc=1 | PASS |
| Fichiers hors scope loggés et non stagés | PASS |
| Refus push mauvaise branche (rc=2) | PASS |
| Warning dirty tree au push (non-bloquant, rc=0) | PASS |
| Push cible uniquement la branche ticket | PASS |

### Smoke test live

Commande exécutée sur T017 :
```bash
python tools/agent_runner/run_ticket.py T017 --commit --include-code
```

- Branche validée contre `state.json` : `ticket/T017-workflow-aware-commit-and-push`
- Fichier stagé : `runs/T017/prompts/tester-attempt-1.md` (1 fichier, 190 lignes)
- Message : `T017: checkpoint [IMPLEMENTATION_APPROVED] — update workflow artifacts`
- Log runtime : entrée `commit-checkpoint: sha=696f140` confirmée
- Aucun `git add .`

### Compatibilité

- `--auto-commit` appelle `commit_ticket(ticket_id, None)` sans `include_code` → comportement inchangé
- Fix loops, review loops, `--auto-init`, `--ensure-branch` : aucune modification détectée dans les tests existants

### Conclusion

**Validation : APPROUVÉE.** L'implémentation respecte tous les critères d'acceptation du ticket T017. Aucune régression détectée.
