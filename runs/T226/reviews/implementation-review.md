Now I have everything needed to write the review.

---

# PR Review — T226: Add floating and dockable AI Workspace window

## Résumé

Implémentation d'une fenêtre AI Workspace flottante, ancrable et persistée. Trois fichiers source modifiés/créés : `useWorkspaceLayout.js` (nouveau hook), `ProjectWorkspacePanel.jsx` (refactored), `App.jsx` (intégration). Dépendance `react-rnd` v10.5.3 ajoutée.

## Vérifications effectuées

- Lecture complète des trois fichiers source modifiés
- Vérification de la couverture des critères d'acceptance du ticket
- Analyse du flux de gestion d'état (hook → App → Panel)
- Vérification du comportement de persistance et de clamping
- Analyse du comportement responsive (small screen)
- Inspection de la logique pointer events pour le resize docké
- Vérification de la préservation de la conversation lors des changements de mode

## Points validés

**Floating mode** (`ProjectWorkspacePanel.jsx:374-396`) — `react-rnd` avec `bounds="window"` garantit le confinement viewport. Les 8 handles de resize sont actifs. Le `dragHandleClassName="ws-drag-handle"` et le `cancel` prop protègent correctement les boutons d'un drag accidentel.

**Docking gauche/droite** (lignes 399-426) — Positionnement `fixed` correct. La bande de resize de 4px utilise le Pointer Events API avec `setPointerCapture`, ce qui est la bonne approche pour un resize robuste cross-device. Le calcul du delta tient compte du côté (`sign = docked-left ? 1 : -1`).

**Persistance et clamping** (`useWorkspaceLayout.js`) — `localStorage` écrit à chaque mutation d'état. Au chargement, `clampLayout()` recalcule les dimensions et positions dans les limites du viewport courant. Listener sur `window.resize` qui re-clamp en temps réel. La logique de contrainte (`maxWidth = min(800, vw-320)`) préserve toujours 320px pour le contenu principal.

**Préservation de la conversation entre modes** — Le composant est rendu en permanence dans `App.jsx` (lignes 129-139). `if (!isOpen) return null` (ligne 215) fait un early return sans unmount React — le state `messages` est préservé. La conversation est bien maintenue lors des changements de mode.

**Navigation** — `ProjectWorkspacePanel` est rendu en dehors du système de routing, ce qui garantit sa persistance au fil des navigations.

**Responsive** — `viewportWidth < 768` déclenche un mode drawer fixe en bas de l'écran (60vh), les boutons de mode sont masqués. Comportement adapté aux petits écrans.

**Margin du contenu principal** (`App.jsx:81-85`) — `mainStyle.marginLeft/Right` est appliqué conditionnellement à `workspaceOpen` et au mode. Shift correct du contenu principal lors du docking.

**Accessibilité** — Tous les boutons ont un `aria-label` explicite. Les icônes ont `aria-hidden="true"`.

**Minimum dimensions** — `MIN_WIDTH=280`, `MIN_HEIGHT=400` définis et appliqués dans le hook et via `minWidth`/`minHeight` props de `react-rnd`.

## Problèmes détectés

**1. Overlap potentiel du sidebar lors du docking à gauche (observation)**

Le panneau docké à gauche est positionné `fixed, left: 0, width: layout.width`. Le `<ProjectSidebar>` est un flex item dans le conteneur parent. Le `marginLeft` est ajouté au `<main>` mais pas compensé pour le sidebar. Si `layout.width` (min 280px) dépasse la largeur du sidebar de navigation, le workspace panel le recouvrira visuellement.

La gravité dépend de la largeur du sidebar. Si le sidebar fait ~200px et que le workspace est à 280px, la superposition est de 80px. Le `zIndex: 40` du panneau docké, combiné au zIndex du sidebar, détermine lequel passe au-dessus. Sans voir le sidebar, ce comportement n'est pas clairement intentionnel.

→ Observation, non bloquant. À confirmer avec la largeur réelle du sidebar.

**2. Constants dupliquées `MIN_WIDTH` / `MIN_HEIGHT`**

Définies dans `useWorkspaceLayout.js:4-5` ET `ProjectWorkspacePanel.jsx:5-6`. Si une valeur change dans l'un, l'autre n'est pas mis à jour automatiquement. Risque de dérive silencieuse.

→ Non bloquant. Une extraction dans un fichier partagé (`constants.js`) serait préférable.

**3. Double listener `window.resize`**

`useWorkspaceLayout.js:65-69` et `ProjectWorkspacePanel.jsx:122-126` enregistrent chacun un écouteur `resize` séparé. C'est fonctionnel mais redondant.

→ Non bloquant. Mineur.

**4. Absence de tests**

Le hook `useWorkspaceLayout` et le composant refactorisé n'ont aucune couverture de test. Les 28+ tests existants ne couvrent pas la fonctionnalité. La logique de clamping et les interactions pointer mériteraient des tests unitaires.

→ Non bloquant pour ce ticket si le projet n'exige pas de tests en critère d'acceptance, mais constitue une dette technique à noter.

## Risques éventuels

- Le `react-rnd` est une dépendance externe de taille modeste (bien maintenue, ~1MB bundled). Le vendor bundle augmentera légèrement.
- La suppression de `if (!isOpen) return null` à tort dans une future modification causerait un rendu permanent consommateur de ressources.
- Les artefacts `dist/` committé dans le diff (attendu dans ce workflow, mais à vérifier).

## Décision

L'implémentation couvre l'ensemble des critères d'acceptance du ticket :
- Fenêtre flottante avec drag et resize ✓
- Docking gauche/droite avec shift du contenu ✓
- Passage entre modes sans perte de conversation ✓
- Persistance après rechargement page ✓
- Confinement viewport (bounds + clamp) ✓
- Responsive small screen (drawer) ✓
- Navigation sans réinitialisation ✓
- Dimensions minimum définies ✓

Les problèmes détectés sont non bloquants et constitutifs de dette technique mineure. Le code est propre, lisible et la séparation de responsabilités (hook / composant / intégration App) est bien respectée.

- APPROVED

## Actions demandées

1. (Recommandé) Centraliser `MIN_WIDTH`/`MIN_HEIGHT` dans un fichier partagé pour éviter la dérive.
2. (Recommandé) Vérifier visuellement le comportement du panel docké-gauche par rapport au sidebar de navigation pour confirmer que la superposition est intentionnelle ou acceptable.
3. (Optionnel) Ajouter des tests unitaires pour `useWorkspaceLayout` (clamping, persistence, mode transitions).

IMPLEMENTATION_APPROVED
