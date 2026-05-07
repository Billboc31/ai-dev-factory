# Implementation Fix Request — T008

Status: IMPLEMENTATION_FIX_REQUIRED

## Défaut bloquant 1 — Transition après step en échec

Dans `run_ticket.py`, après `_call_run_step(...)`, le code capture `rc` mais ne bloque pas si `rc != 0`.

Correction obligatoire :
- si `rc != 0`, logger l’échec
- ne pas appeler `_determine_next_state`
- ne pas sauvegarder de nouvel état
- retourner exit code 2

## Défaut 2 — Portabilité écriture temporaire state.json

Remplacer :

```python
path.with_suffix(".json.tmp")
```

par une construction portable :

```python
path.parent / (path.name + ".tmp")
```

## Défaut 3 — Monitoring runtime.log documenté

Mettre à jour `README.md` pour indiquer que pendant une étape longue, on peut suivre :

```bash
tail -f runs/TXXX/runtime.log
```

## Résultat attendu

Corriger l’implémentation sans changer l’architecture générale validée :
- `state.json` reste source de vérité
- `workflow-status.md` reste append-only
- pas de PR auto
- pas de merge auto
- `--auto` reste une seule étape par invocation
