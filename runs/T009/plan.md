## Plan T009 — Artifact-aware fix loop (v2)

### Problème

Quand `--auto` transite vers `PLAN_FIX_REQUIRED` ou `IMPLEMENTATION_FIX_REQUIRED`, il relance
planner/coder avec **uniquement le prompt canonique** — sans le contexte du retry (output
précédent, review, fix instructions). L'humain doit assembler ça manuellement.

### Solution (3 fichiers, invocation humaine préservée)

---

#### `run_step.py` — flag `--extra-context-file`

Ajout d'un paramètre `--extra-context-file <path>` :

- Lit le fichier et **appende** son contenu au prompt canonique avant envoi à l'external command
- Séparateur : `\n\n---\n\n## Contexte de retry injecté par run_ticket.py\n\n`
- Aucun changement de comportement si le flag est absent

---

#### `run_ticket.py` — 3 nouvelles fonctions + modification de `auto_run`

##### `_collect_fix_artifacts(ticket_id, state) -> dict`

Retourne un dict `{"previous_output": Path, "review": Path, "fix_instructions": Path}`.
Lève `TicketRunnerError` avec le chemin exact attendu si un artefact est absent.

**Règles de sélection verrouillées :**

| État | Clé | Règle |
|------|-----|-------|
| `PLAN_FIX_REQUIRED` | `previous_output` | chemin fixe `runs/TXXX/plan.md` |
| `IMPLEMENTATION_FIX_REQUIRED` | `previous_output` | chemin fixe `runs/TXXX/implementation-output.md` |
| `PLAN_FIX_REQUIRED` | `review` | glob `reviews/plan-review*.md`, dernier par mtime |
| `IMPLEMENTATION_FIX_REQUIRED` | `review` | glob `reviews/implementation-review*.md`, dernier par mtime |
| `PLAN_FIX_REQUIRED` | `fix_instructions` | glob `fixes/plan-fix-*.md`, dernier par mtime |
| `IMPLEMENTATION_FIX_REQUIRED` | `fix_instructions` | glob `fixes/implementation-fix-*.md`, dernier par mtime |

**Exclusion explicite des fichiers générés :** tout fichier dont le nom commence par `context-`
est filtré avant la sélection par mtime — évite l'auto-inclusion récursive des `fixes/context-*.md`.

Cette exclusion s'applique aux globs `fixes/plan-fix-*.md` et `fixes/implementation-fix-*.md`
(le pattern les exclut déjà, mais le filtre est défensif et documenté).

##### `_build_fix_context_file(ticket_id, artifacts) -> Path`

Concatène les 3 artefacts collectés en `runs/TXXX/fixes/context-<ts>.md` avec en-têtes de
section explicites. Retourne le chemin du fichier créé.

##### Modification de `auto_run`

Avant `_call_run_step`, si l'état courant est `PLAN_FIX_REQUIRED` ou
`IMPLEMENTATION_FIX_REQUIRED` :

1. Appelle `_collect_fix_artifacts()` — lève `TicketRunnerError` si un artefact manque
2. Appelle `_build_fix_context_file()` — crée le fichier contexte horodaté
3. Logue chaque artefact injecté dans `runtime.log` :
   ```
   auto-run: fix context: previous_output=runs/TXXX/plan.md
   auto-run: fix context: review=runs/TXXX/reviews/plan-review.md
   auto-run: fix context: fix_instructions=runs/TXXX/fixes/plan-fix-1.md
   auto-run: fix context: context_file=runs/TXXX/fixes/context-20260508T120000Z.md
   ```
4. Passe `extra_context_file` à `_call_run_step`

`_call_run_step` reçoit `extra_context_file: Path | None = None` et, si présent, ajoute
`--extra-context-file <path>` à l'invocation de `run_step.py`.

---

#### `tools/agent_runner/README.md` — section fix loop

Documenter :

- Convention de nommage des reviews :
  - plan : `reviews/plan-review.md` (stable, ou versionné `plan-review-vN.md`)
  - implémentation : `reviews/implementation-review.md` (stable, ou `implementation-review-vN.md`)
- Convention de nommage des fix files :
  - plan : `fixes/plan-fix-N.md` ou `fixes/plan-fix-<slug>.md`
  - implémentation : `fixes/implementation-fix-N.md`
- Règle de sélection : **dernier fichier par mtime** (couvre stable et versionné)
- Fichiers `fixes/context-*.md` : générés par le runner, jamais écrits manuellement
- Quand créer un fix file : après chaque review qui produit `*_FIX_REQUIRED`
- Commande de relance : `python run_ticket.py TXXX --auto --exec-cmd "..."`
- Exemple de `runtime.log` après fix loop

---

### Invariants préservés

- L'humain crée le fichier fix instructions ET relance `--auto` manuellement
- Pas de boucle automatique, pas de LLM implicite, pas de PR/merge auto
- `state.json` atomique, prompts canoniques non modifiés, logs transparents
- `fixes/context-*.md` sont des fichiers générés — jamais injectés récursivement
