# Documentation PyVenture

Ce dossier contient le plan de développement et les spécifications du projet.

## Par où commencer ?

| Document | Contenu |
| --- | --- |
| [00 — Audit et propositions](00-audit-propositions.md) | État des lieux, bugs, idées d'amélioration, décisions validées |
| [01 — Architecture](01-architecture.md) | Organisation cible du code, flux d'exécution, dépendances |
| [02 — Modèle de données](02-modele-de-donnees.md) | Format YAML, pièces, objets, interactions, conditions, effets |
| [03 — Roadmap](03-roadmap.md) | Phases, tâches, critères d'acceptation |
| [04 — Éditeur graphique](04-editeur.md) | Spécifications de l'éditeur de contenu |
| [05 — Multilingue](05-i18n.md) | Stratégie de traduction et de localisation |
| [06 — Workflow de développement](06-workflow-dev.md) | Installation, tests, conventions, contributions |

## Raccourcis

- Schéma JSON : [`pyventure/schema/game.schema.json`](../pyventure/schema/game.schema.json)
- Exemple de projet : [`examples/mini-game/game.yaml`](../examples/mini-game/game.yaml)
- Contribution : [`CONTRIBUTING.md`](../CONTRIBUTING.md)
- Licence : [`LICENSE`](../LICENSE) (MIT)

## Décisions clés

| Sujet | Choix |
| --- | --- |
| Fenêtre de jeu | pygame-ce, rendu logiciel, 320×180 |
| Éditeur | Tkinter/ttk (application séparée) |
| Format de contenu | YAML + schéma JSON |
| Langues | FR + EN |
| Plateformes | Linux d'abord, portabilité rétro préparée |
| Licence | MIT |

## Statut

- **Phase 0 (cadrage)** : terminée, décisions validées.
- **Phase 1 (moteur + terminal)** : terminée. Moteur data-driven, parseur, règles, sauvegarde, autosave, terminal et migration du contenu historique.
- **Phase 2 (fenêtre pygame)** : terminée. La fenêtre joue le jeu complet (art pixel, transcript, inventaire, saisie, menu, thème clair/sombre, taille de police, transitions).
- **Phase 3 (éditeur Tkinter)** : terminée. Arbre de projet, formulaires par langue, sorties, YAML synchronisé, validation, undo/redo, autosave/backups, lancement du jeu.
- Le moteur historique (`start.py`, `engine.py`, `content.py`) reste jouable via `python3 -m pyventure play --legacy`.
