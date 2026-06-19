Now I have everything needed. Let me write the structured review.

---

# PR Review — T196: Add UI action to install agent layout on existing projects

## Résumé

L'implémentation couvre l'ensemble du flux décrit dans le ticket : bouton UI → Control API → Supervisor → orchestrateur Python → LLM → opérations Git → création de PR. Le code est propre, bien découpé, et couvert par 28 tests. Les critères d'acceptation sont fonctionnellement satisfaits.

---

## Vérifications effectuées

- Lecture complète des 7 fichiers produits : `install_agent_layout.py`, `docs_prompt_builder.py`, `test_install_agent_layout.py`, `routes/projects.py` (endpoint ajouté), `schemas.py` (nouveau modèle), `ProjectDashboardPage.jsx`, `projects.js`
- Vérification du chemin de validation de sécurité (`_validate_doc_path`)
- Vérification du flow de bout en bout (UI → Control API → Supervisor → orchestrateur)
- Vérification de l'idempotence et de la détection de layout existant
- Vérification des tests d'intégration (repo git réel, LLM mocké)
- Vérification de la couverture des critères d'acceptation du ticket

---

## Points validés

**Fonctionnel**
- Bouton d'action présent sur la page projet, appel à `/install-agent-layout` avec timeout 420 s côté client
- Le backend détecte si le layout existe déjà (`_layout_exists` vérifie `ai/`) et choisit la bonne branche (`INSTALL_BRANCH` vs `UPDATE_BRANCH`) et le bon titre de PR
- Dossiers `ai/`, `prompts/`, `runs/`, `tickets/` créés idempotentiellement sans écraser les fichiers existants
- `docs/` généré par analyse LLM réelle, pas par des placeholders vides
- Commit exclusivement sur branche dédiée — jamais sur le default branch
- Création de PR via `gh`, avec détection d'une PR existante pour éviter les doublons
- Réutilisation de l'enregistrement projet existant (pas de re-bootstrap)
- UI affiche PR URL, nom de branche, résumé d'analyse, liste des docs générés, warnings

**Sécurité (LLM → écriture fichier)**
- `_validate_doc_path` rejette les chemins absolus, le path traversal (via `resolved.relative_to(docs_root)`), et les fichiers non-markdown
- Fichiers vides ignorés avec warning
- Tests dédiés pour absolus, traversal, non-markdown — tous passants

**Architecture**
- `mapper.map()` correctement appelé côté supervisor pour le mapping host/container (ligne 1666)
- Séparation claire prompt builder (pure fonction, pas d'I/O) / orchestrateur / supervisor / control API
- Lecture fichiers cappée à 4 KB pour contrôler l'usage token

**Tests**
- 28 tests couvrant : helpers unitaires, prompt builder, intégration (git réel + LLM mocké), idempotence, absence de remote, échec LLM, traversal, absolute path, docs manquants

---

## Problèmes détectés

### Observations mineures (non bloquantes)

**1. Label du bouton statique**
`apps/dashboard/src/pages/ProjectDashboardPage.jsx:197` — Le ticket spécifie un label dynamique : `"Install AI Dev Factory agent layout"` pour les nouveaux projets, `"Regenerate agent layout / docs"` si le layout est déjà présent. L'implémentation affiche toujours `"Install agent layout"`. Le backend différencie correctement les deux cas (branche, message de commit, titre PR), seul le label visuel est figé. Acceptable pour une première livraison mais non conforme à la spec exacte.

**2. `exec_cmd` non transmis du Control API au Supervisor**
`services/control_api/routes/projects.py:208-213` — Le payload envoyé au Supervisor ne contient pas `exec_cmd`, qui est pourtant supporté dans `InstallAgentLayoutRequest` avec un défaut sain (`claude --dangerously-skip-permissions`). Cela n'est pas un problème opérationnel, mais empêche toute surcharge de la commande LLM depuis l'UI ou l'API.

**3. `docs/ai/global-context.md` absent de `docs_paths`**
`tools/agent_runner/install_agent_layout.py:142-152` — Ce fichier est créé dans `_ensure_layout_dirs` mais n'apparaît pas dans `written_paths`. Le PR body et l'UI n'en font pas mention, même si le fichier est bien committé. Discordance mineure entre l'affichage et le contenu réel du commit.

**4. Calcul `is_last` dans `_build_file_tree` avec entrées filtrées**
`tools/agent_runner/docs_prompt_builder.py:148` — `is_last = i == len(entries) - 1` est calculé sur la liste totale incluant les entrées filtrées par `_SKIP_DIRS`. Si le dernier élément de la liste totale est un dossier skip (ex. `node_modules` trié après `tests/`), le vrai dernier élément visible utilisera `├──` au lieu de `└──`. Artefact visuel cosmétique sur le file tree envoyé au LLM, sans impact fonctionnel.

---

## Risques éventuels

- **Absence de verrou de concurrence** : deux appels simultanés sur le même projet pourraient provoquer des conflits Git. Risque faible en usage mono-utilisateur.
- **Timeout LLM à 360 s** : si Claude prend plus de 6 min, l'opération échoue avec un message d'erreur. Acceptable et cohérent avec le timeout end-to-end de 420 s.
- **Parsing LLM par regex** : un LLM qui produirait des blocs `--- BEGIN FILE` mal formés (ex. avec des espaces supplémentaires) serait silencieusement ignoré avec un avertissement "missing required base docs". Le warning est produit et remonté à l'UI.

---

## Décision

Toutes les acceptance criteria du ticket sont satisfaites. Les quatre observations sont mineures et n'affectent pas la correction fonctionnelle. Le code est lisible, sécurisé et bien testé.

- APPROVED

---

## Actions demandées

Aucune correction bloquante. En amélioration optionnelle post-merge :
- Rendre le label du bouton dynamique (nécessite un endpoint GET `/projects/{id}/layout-status` ou un flag dans la réponse de listing des projets)
- Transmettre `exec_cmd` depuis le Control API au Supervisor
- Inclure `docs/ai/global-context.md` dans `docs_paths` (déplacer son écriture dans la boucle principale ou l'ajouter manuellement à `written_paths`)

IMPLEMENTATION_APPROVED
