---

## Review — T008 mode `--auto`

### Périmètre

- `tools/agent_runner/run_ticket.py` (implementation complète)
- `README.md` (section `--auto`)
- `.gitignore`
- `tools/agent_runner/run_step.py` (contrat d'interface)

---

### 1. Progression automatique cohérente ✅

La table `TRANSITIONS` correspond exactement au plan v2 : 8 états, 9 arcs, `TEST_COMPLETE` terminal avec `None`. La fonction `_determine_next_state()` est correcte :

- Déterministe → `possible_next[0]`, sans lire la sortie.
- Review → regex `^KEYWORD$` multiline, protection contre les faux positifs inline/markdown.
- Ambiguïté (plusieurs keywords) → warning + premier utilisé. Comportement documenté.

Le diagramme ASCII du README correspond à l'implémentation. ✅

Le README montre 6 invocations pour le chemin heureux (INIT → TEST_COMPLETE + 1 finale). Le plan v2 annonçait 7 — le plan comptait peut-être `--auto-init`. L'implémentation est correcte, le plan était imprécis.

---

### 2. Logs visibles ✅

Tous les événements clés sont journalisés dans `runtime.log` :

| Événement | Log présent |
|---|---|
| `--auto-init` | ✅ |
| Gate failure (branch, dirty tree) | ✅ |
| Lancement d'étape | ✅ |
| Fin d'étape + rc | ✅ |
| Keyword absent | ✅ |
| Transition réussie | ✅ |
| Workflow complet | ✅ |

Le `runtime.log` est ignoré par git (`.gitignore`). La commande `tail -f` est documentée dans le README. ✅

---

### 3. Gates workflow respectés ✅

Les 5 gates du plan sont tous présents et bloquants :

| Gate | Impl. | Exit |
|---|---|---|
| `state.json` absent/corrompu | `load_state()` | 2 |
| État inconnu | `load_state()` | 2 |
| `TEST_COMPLETE` | guard explicite | 0 |
| Branche divergente | `_get_current_branch()` | 2 |
| Working tree sale | `_check_working_tree_clean()` | 2 |

`--exec-cmd` absent → exit 2 dans `main()` avant `auto_run()`. ✅

`state.json` et `runtime.log` sont dans `.gitignore` → le gate 5 ne se déclenche pas à tort après `--auto-init`. ✅

`save_state()` est atomique (write + rename). ✅

---

### 4. Absence d'autonomie dangereuse ✅

- Aucun merge automatique.
- Aucune création de PR.
- Aucune boucle automatique — une étape par invocation, contrôlée par l'humain.
- Aucun appel réseau hors des commandes git et du `--exec-cmd` explicitement fourni.
- Le commentaire d'en-tête docstring le confirme explicitement.

---

### 5. Boucle review/fix contrôlée ✅

Les cycles `PLAN_FIX_REQUIRED → PLAN_REVIEW_NEEDED` et `IMPLEMENTATION_FIX_REQUIRED → IMPLEMENTATION_REVIEW_NEEDED` sont bornés : chaque itération exige une invocation manuelle + `--commit`. Aucun risque de boucle infinie mécanique.

---

### Défauts identifiés

#### MOYEN — Stderr LLM silencieusement perdu

**Fichier** : `run_step.py:218` / `run_ticket.py:230`

`run_step.py` capture le stderr du LLM dans `stderr` (ligne 218) mais ne le reprint sur son propre stderr que si `--stderr-log` est fourni. `_call_run_step()` n'utilise pas `--stderr-log`. Résultat : en cas d'erreur LLM (auth, rate-limit, timeout), l'utilisateur voit uniquement `rc=1` sans message explicatif.

**Impact** : debugging très difficile en pratique.

**Correction suggérée** dans `run_step.py` (bloc `exec_cmd`, après `write_output`) :

```python
if stderr:
    print(stderr, end="", file=sys.stderr)
```

Ou dans `_call_run_step()`, passer `--stderr-log runs/TXXX/runtime.log` en argument.

---

#### MINEUR — `init_auto()` non atomique vs `save_state()` atomique

**Fichier** : `run_ticket.py:302`

`init_auto()` écrit `state.json` avec `path.write_text(...)` directement, alors que `save_state()` utilise write + rename. Risque d'état partiel si le processus est tué pendant l'écriture. La probabilité est faible (fichier court, opération ponctuelle), mais l'incohérence stylistique avec `save_state()` est notable.

---

#### MINEUR — `DEFAULT_OUTPUTS` dupliqué entre les deux modules

**Fichiers** : `run_ticket.py:49` et `run_step.py:38`

Le commentaire `# Must stay in sync with run_step.py DEFAULT_OUTPUTS` signale la dette. Pour T008, pas bloquant, mais les deux dicts divergeront à la première évolution (`memory-updater` est déjà absent de `run_ticket.py`).

---

### Verdict global

**IMPLEMENTATION_APPROVED**

L'implémentation respecte fidèlement le plan v2 : source de vérité unique (`state.json`), gates stricts, zéro autonomie dangereuse, journal lisible (`workflow-status.md`) jamais relu pour décider. Les trois corrections de l'itération précédente (`.gitignore`, warning output manquant, exemple README avec `--commit`) sont toutes correctement intégrées.

Le seul point qui mérite une action avant merge : le stderr LLM silencieux (défaut MOYEN). Les deux points mineurs peuvent être traités ultérieurement.
