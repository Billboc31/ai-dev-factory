# T106 — T106 — Project issue tree agent and dependency map

**Source**: GitHub Issue #48

## Description

# T106 — Project issue tree agent and dependency map

## Objectif

Créer un agent global projet capable de :

- lire les issues ouvertes
- construire une vue arbre/graphe des tickets
- détecter dépendances et parallélisation possible
- recommander l’ordre d’exécution
- alimenter une nouvelle page dashboard

Sans créer automatiquement de nouveaux tickets.

---

## Vision

Le système doit progressivement évoluer de :

```text
issue queue FIFO
```

vers :

```text
project-aware orchestration
```

---

## Fonctionnement

L’agent :

```text
lit les issues ouvertes
→ analyse les relations
→ construit une map projet
→ détecte :
   - blocked
   - runnable
   - parallelizable
   - depends-on
→ écrit un artefact versionné
```

---

## Dashboard

Ajouter une page :

```text
Project Map
```

avec :

- arbre des tickets
- dépendances
- statut runtime
- tickets bloqués
- tickets parallélisables
- next recommended ticket
- capacité disponible

---

## Agent activity page

Ajouter une vue :

```text
Issue Mapper Activity
```

avec :

- dernier scan
- décisions prises
- reasoning simplifié
- ambiguïtés détectées
- suggestions d’ordre d’exécution

---

## Intégration daemon

Le daemon ne doit plus intake simplement par ordre des issues.

Le daemon doit pouvoir utiliser :

```text
project issue map
```

pour décider :

- quoi lancer
- quoi garder en attente
- quoi paralléliser

---

## Contraintes

- Git reste source de vérité
- pas de DB dédiée
- pas de création automatique d’issues dans cette V1
- garder human gates
- système observable via dashboard et artefacts

---

## Critères d’acceptation

- l’agent produit une map projet exploitable
- le dashboard affiche l’arbre des tickets
- les tickets parallélisables sont détectés
- les tickets bloqués sont identifiés
- le daemon peut utiliser la map pour l’intake/scheduling
