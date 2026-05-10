Plan produit dans `runs/T010/plan.md`. Voici le résumé :

---

## Plan T010 — Ce qui va changer

**Un seul fichier de code modifié : `tools/agent_runner/run_step.py`**

### 4 ajouts dans `run_step.py`

1. **`import datetime`** — manquant aujourd'hui.

2. **`_log_runtime_step(ticket_id, message)`** — même contrat que le `_log_runtime` de `run_ticket.py`, écrit dans le même `runtime.log`. Les deux scripts cohabitent sans conflit (entrées horodatées).

3. **`_compute_attempt_number(run_dir, step)`** — compte les fichiers existants `<step>-attempt-*.md` et retourne `len + 1`. Simple, robuste aux trous.

4. **`_write_prompt_snapshot(...)`** — écrit `runs/TXXX/prompts/<step>-attempt-N.md` avec un frontmatter YAML (ticket, step, attempt, timestamp, canonical, extra_context) suivi du prompt effectif complet.

### Intégration dans `main()`

Dans le bloc `if args.exec_cmd:`, **après** la construction de `effective_prompt` et **avant** `execute_external_command` :

```python
snapshot_path = _write_prompt_snapshot(...)
_log_runtime_step(ticket_id, f"prompt-snapshot: {snapshot_path}")
print(f"prompt snapshot: {snapshot_path}")
```

Le snapshot est donc écrit même si l'external command échoue.

### Documentation

Section **Runtime prompt snapshots** ajoutée dans `tools/agent_runner/README.md`.

### Pas touché

- `run_ticket.py` — aucun changement
- `prompts/` — aucun changement
- Aucune autonomie ajoutée
