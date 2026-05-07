Les permissions ne sont pas encore accordées pour ce fichier. Voici exactement ce que j'applique en attendant que vous les accordiez.

---

**Diff complet — `tools/agent_runner/run_ticket.py`**

**Fix 1 — `checkout_branch` (ligne 87-90 → 87-94)**

```python
# AVANT
def checkout_branch(ticket_id: str, slug: str | None) -> int:
    name = branch_name(ticket_id, slug)
    print(f"checkout branch: {name}")
    return run_git(["checkout", "-B", name])

# APRÈS
def checkout_branch(ticket_id: str, slug: str | None) -> int:
    name = branch_name(ticket_id, slug)
    print(f"checkout branch: {name}")
    # Avoid -B which silently destroys an unmerged existing branch.
    check = run_command(["git", "rev-parse", "--verify", name])
    if check.returncode == 0:
        return run_git(["checkout", name])
    return run_git(["checkout", "-b", name])
```

**Fix 2 — `commit_ticket` (ligne 93-103 → signature + staging explicite)**

```python
# AVANT
def commit_ticket(ticket_id: str, message: str | None) -> int:
    ...
    add_result = run_command(["git", "add", "."])
    ...

# APRÈS
def commit_ticket(ticket_id: str, message: str | None, extra_paths: list[str] | None) -> int:
    ...
    paths_to_stage: list[str] = [f"runs/{ticket_id}/"]
    if extra_paths:
        paths_to_stage.extend(extra_paths)
    add_result = run_command(["git", "add", "--", *paths_to_stage])
    ...
```

**Ajout — argument `--paths` dans `parse_args`**

```python
parser.add_argument("--paths", nargs="+", metavar="PATH",
                    help="Additional paths to stage (beyond runs/TXXX/)")
```

---

Une fois les permissions accordées, je pourrai écrire le fichier et enchaîner avec la création de `docs/ai/git-workflow.md` et la remise à jour de `runs/T007/workflow-status.md`. Pouvez-vous autoriser l'écriture dans `tools/agent_runner/run_ticket.py` ?
