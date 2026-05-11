## Test Report T013 — Git Workflow Automation Primitives

**Verdict : TEST_COMPLETE**

---

### Environnement

- Branch : `ticket/T013-git-workflow-automation-primitives`
- State : `IMPLEMENTATION_APPROVED`
- Python : system python3
- Fichier testé : `tools/agent_runner/run_ticket.py`

---

### Cas testés

#### TC1 — CLI : tous les flags présents
```
python run_ticket.py --help
```
- `--branch`, `--ensure-branch`, `--commit`, `--commit-message`, `--push`
- `--auto-commit`, `--auto-push`
- **Résultat : OK** — tous les flags sont présents et documentés

#### TC2 — `--commit` refuse si rien à committer dans `runs/`
```
python run_ticket.py T013 --commit
# working tree propre, aucun changement dans runs/T013/
```
- **Résultat : OK** — `rc=1`, stderr = `nothing to commit in runs/ artifacts`
- Log runtime : `commit-checkpoint: refused — nothing to commit in runs/`

#### TC3 — `--ensure-branch` sur branche existante, working tree propre
```
python run_ticket.py T013 --ensure-branch --branch-slug git-workflow-automation-primitives
```
- **Résultat : OK** — `rc=0`, git checkout sans écrasement
- Log runtime : `ensure-branch: switching to existing branch ...` + `ensure-branch: done`

#### TC4 — `--ensure-branch` refuse si working tree sale
```
# fichier non tracké ajouté dans runs/T013/tests/
python run_ticket.py T013 --ensure-branch --branch-slug ...
```
- **Résultat : OK** — `rc=2`, stderr = `working tree is not clean — commit or stash changes first`
- Log runtime : `ensure-branch: refused — working tree is not clean`

#### TC5 — `--push` refuse si branche ≠ `state.json["branch"]`
```
# state.json modifié temporairement : branch = "ticket/T013-some-other-branch"
python run_ticket.py T013 --push
```
- **Résultat : OK** — `rc=2`, message d'erreur clair avec les deux valeurs
- Log runtime : `push: refused — current branch ... does not match state branch ...`

#### TC6 — `--push` warning non-bloquant si `state.json` absent
```
# state.json temporairement renommé
python run_ticket.py T013 --push
```
- **Résultat : OK** — `rc≠0` (push échoue car branche `ticket/T013-work` n'existe pas, attendu)
- stderr : `warning: state.json not found — skipping branch verification`
- Log runtime : `push: warning — state.json absent, branch not verified`

#### TC7 — `--push` avec branche correspondante (happy path)
```
python run_ticket.py T013 --push --branch-slug git-workflow-automation-primitives
```
- **Résultat : OK** — `rc=0`, push réussi vers origin
- Log runtime : `push: pushing branch=...` + `push: done branch=...`

#### TC8 — `--commit` avec message par défaut state-aware
```
# fichier créé dans runs/T013/tests/
python run_ticket.py T013 --commit
```
- **Résultat : OK** — message commit = `T013: checkpoint [IMPLEMENTATION_APPROVED] — update workflow artifacts`
- Log runtime : `commit-checkpoint: sha=140ba8d message='T013: checkpoint ...'`

#### TC9 — Parsing `--auto-commit` et `--auto-push`
```python
args = parse_args(['T013', '--auto', '--exec-cmd', '...', '--auto-commit', '--auto-push'])
# auto_commit=True, auto_push=True
args2 = parse_args(['T013', '--auto', '--exec-cmd', '...'])
# auto_commit=False, auto_push=False (opt-in)
```
- **Résultat : OK** — flags sont opt-in, valeur par défaut `False`

---

### Logging runtime

Toutes les actions testées ont généré les entrées attendues dans `runs/T013/runtime.log`. Les formats correspondent à la documentation `docs/ai/git-workflow.md`.

---

### Anomalies

Aucune anomalie critique. Une observation mineure :

- TC6 : quand `state.json` est absent et qu'aucun `--branch-slug` n'est fourni, le fallback est `ticket/T013-work` (slug par défaut "work"). Ce comportement est cohérent avec `branch_name()` mais pourrait surprendre. C'est documenté implicitement par la logique du code — pas un défaut.

---

### Conclusion

Les 6 critères d'acceptation du ticket sont validés par les tests :

1. `checkout_branch()` refuse sur working tree sale — **OK**
2. `checkout_branch()` ne crée pas la branche si elle existe déjà — **OK**
3. `commit_ticket()` refuse si rien à committer dans `runs/` — **OK**
4. Message de commit par défaut inclut l'état courant — **OK**
5. `push_branch()` vérifie `state.json` avant push, warning si absent — **OK**
6. `--auto-commit` et `--auto-push` sont opt-in et correctement parsés — **OK**

**TEST_COMPLETE**
