J'ai maintenant une image complète. Voici la review structurée.

---

## Review T008 — mode `--auto`

### Verdict global

**IMPLEMENTATION_FIX_REQUIRED**

L'implémentation est solide dans sa structure et les 3 fixes revendiqués sont correctement appliqués. Un défaut bloquant est identifié : le gate "working tree clean" inclut les fichiers non-trackés, ce qui auto-bloque la première invocation `--auto` après `--auto-init`. Deux points mineurs.

---

### Les 3 fixes revendiqués — vérification

| Fix | Localisation | Statut |
|---|---|---|
| rc != 0 → state unchanged, exit 2 | `run_ticket.py:346-349` | ✅ Correct |
| `path.parent / (path.name + ".tmp")` | `run_ticket.py:190` | ✅ Correct |
| `tail -f runs/TXXX/runtime.log` dans README | `README.md:38` | ✅ Correct |

---

### Défaut 1 — BLOQUANT : gate 5 auto-bloque après `--auto-init`

**Localisation** : `run_ticket.py:202-209` (`_check_working_tree_clean`) + absence de `.gitignore` projet.

`git status --porcelain` remonte les fichiers **non-trackés** (`?? ...`) comme du "dirty". Après `--auto-init`, `state.json` est créé mais non commité. La première invocation `--auto` échoue donc immédiatement sur le gate 5 avec "working tree is not clean".

Le plan dit `state.json` est "non versionné directement" — mais sans `.gitignore` pour l'exclure, et sans `--commit` obligatoire dans le README avant le premier `--auto`, le workflow est auto-bloquant dès le départ.

Il existe un `.gitignore` projet à créer (il n'en existe pas, seul `.venv/.gitignore` est présent). Ce même problème affecte `runtime.log` : créé par `_log_runtime` lors du premier `--auto`, il bloque le suivant.

**Correction requise** — deux options, à choisir :
- Option A : Ajouter un `.gitignore` projet qui exclut `runs/*/state.json` et `runs/*/runtime.log`.
- Option B : Filtrer les lignes `??` dans `_check_working_tree_clean` (exclure les untracked) — plus permissif, moins conforme à l'intention du plan.

Option A est préférable car cohérente avec "non versionné directement" et préserve l'intention du gate.

---

### Défaut 2 — MOYEN : sortie review lue depuis le fichier, pas stdout

**Localisation** : `run_ticket.py:245-248`

```python
output_path = Path("runs") / ticket_id / output_rel
output_content = output_path.read_text(encoding="utf-8") if output_path.exists() else ""
```

Si `run_step.py` n'écrit pas le fichier attendu (step échoue partiellement, chemin divergent), `output_content` est `""` et la détection de keyword échoue silencieusement avec exit 1. Aucune trace du fichier manquant dans le log.

**Recommandation** : Loguer un warning explicite si `output_path` n'existe pas après un rc = 0.

```python
if not output_path.exists():
    print(f"warning: expected output file {output_path} not found", file=sys.stderr)
    _log_runtime(ticket_id, f"auto-run: output file missing: {output_path}")
```

---

### Défaut 3 — MINEUR : session example dans README trompeuse

**Localisation** : `README.md:73-94`

L'exemple de session enchaîne 6 `--auto` sans aucun `--commit` entre les étapes. Avec gate 5 en place (même corrigé, les fichiers de sortie des steps — `plan.md`, `reviews/review.md` — seront trackés ou modifiés), l'utilisateur doit commiter entre chaque étape. L'exemple ne le montre pas.

**Recommandation** : Ajouter un commentaire dans l'exemple :

```bash
# After each step, commit artifacts before the next --auto
python tools/agent_runner/run_ticket.py T009 --commit
```

---

### Points positifs

- **State machine** : table `TRANSITIONS` exhaustive et cohérente avec le plan. Toute transition non listée est impossible structurellement.
- **`_determine_next_state`** : regex `^KEYWORD$` multilignes correcte, gestion du cas multi-keyword avec warning.
- **`save_state`** : écriture atomique via write + rename — correctement implémentée.
- **Pas de merge, pas de loop** : `TEST_COMPLETE` sort avec exit 0 sans aucune action supplémentaire. La boucle review/fix est contrôlée (une étape par invocation, re-invocation manuelle uniquement).
- **Logs** : `runtime.log` exhaustif, warnings vers stderr, prints vers stdout — séparation correcte.
- **`--auto-init` protégé** : refus d'écraser un `state.json` existant.
- **Gate 4** (branche) et **gate 5** (working tree) correctement positionnés après le guard `TEST_COMPLETE`.
- **Code mort minimal** : le bloc `if transition is None` (ligne 334) est dead code documenté — acceptable.

---

### Résumé des actions requises

| # | Sévérité | Action |
|---|---|---|
| 1 | Bloquant | Créer `.gitignore` projet excluant `runs/*/state.json` et `runs/*/runtime.log`, ou filtrer les untracked dans gate 5 |
| 2 | Moyen | Logger un warning si le fichier de sortie attendu est absent après rc = 0 |
| 3 | Mineur | Ajouter `--commit` entre les étapes dans l'exemple README |
