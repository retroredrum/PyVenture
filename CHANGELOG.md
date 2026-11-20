# Changelog

Toutes les modifications notables de ce projet sont documentées dans ce fichier.

Le format s'inspire de [Keep a Changelog](https://keepachangelog.com/fr/1.1.0/),
et le projet suit le [versionnage sémantique](https://semver.org/lang/fr/).

## [Non publié]

### Ajouté — Phase 3 (éditeur Tkinter)

- `pyventure/editor/` : fenêtre Tkinter avec arbre de projet (pièces, objets, interactions, messages, fins, flags), formulaires par langue et onglets Formulaire / YAML / Validation.
- Formulaires : métadonnées, pièce (avec éditeur de sorties), objet (synonymes, emplacements, états), interaction (verbes, objets, conditions/effets YAML avec modèles), message, fin, flags et compteurs.
- `ProjectDocument` : chargement/sauvegarde round-trip (commentaires préservés), undo/redo, validation, renommage d'ID avec mise à jour des références.
- Autosave et backups dans `.pyventure/`, indicateur de modifications, création de projet guidée.
- Onglet YAML synchronisé avec application contrôlée, panneau de validation, bouton « Jouer » (sous-processus pygame).
- Projets récents (menu Fichier), détection des modifications externes et hot reload de l'aperçu à la sauvegarde.
- Navigation depuis un problème de validation vers l'élément concerné, duplication de pièce/objet/interaction.
- `python3 -m pyventure editor` et option de projet.
- Tests : 43 (document et préférences sans Tk + interface Tkinter sous Xvfb).

### Ajouté — Phase 2 (fenêtre pygame)

- Fenêtre graphique `pyventure/ui/pygame/` : art pixel art en haut, transcript défilant au centre, inventaire à droite, saisie en bas.
- `ArtView` : agrandissement entier au plus proche voisin, variantes de pièce, cache de surfaces et placeholders déterministes nommés d'après la pièce.
- Transcript avec wrapping, styles sémantiques, défilement (molette, PageUp/PageDown) et barre de défilement.
- Saisie clavier : caractères, retour arrière, historique (`↑`/`↓`), complétion (`Tab`).
- Panneau d'inventaire avec icônes d'objets (placeholder lettre si l'asset manque).
- Menu en jeu (`Échap`) : nouvelle partie, sauvegarder, charger, langue, thème, taille du texte, aide, quitter.
- Thème sombre/clair et trois tailles de police, applicables à chaud.
- Transition en fondu entre deux pièces.
- Redimensionnement de fenêtre et letterboxing, autosave et reprise partagés avec le terminal.
- `python3 -m pyventure play --gui` et option `--size LxH`.
- Tests headless pygame (`SDL_VIDEODRIVER=dummy`) : 22 tests.

### Ajouté — Phase 1 (moteur data-driven)

- Cœur pur `pyventure.core` : modèle, chargement YAML, validation (schéma JSON + références), parseur multilingue, règles, moteur, état, sauvegarde et résolution d'assets.
- Interactions déclaratives : conditions (`has`, `flag`, `room`, `object_state`, `counter`, `score`, `any`, `all`, `not`) et effets (`say`, `set_flag`, `move_object`, `set_room_variant`, `set_exit`, `end_game`, …).
- Parseur : normalisation (accents, casse), articles ignorés, synonymes, verbes multi-mots, directions canoniques `n/s/e/w/u/d`, résolution d'objets dans la portée, messages d'erreur localisés.
- Sauvegarde/chargement JSON versionné, **autosave** avec reprise automatique (`--fresh`, `--no-autosave`), `undo` par snapshot, commandes de debug (`/goto`, `/give`, `/flags`, `/state`).
- Mode terminal ANSI (`python3 -m pyventure play`) avec `--lang`, `--project`, `--save`, `--no-color`, `--legacy`.
- `tools/convert_legacy.py` : conversion de `content.py` vers YAML, résultat dans `examples/legacy-game`.
- Transcripts dorés : nouveau moteur (FR/EN) et moteur historique, dans `tests/golden/`.
- 58 tests (chargeur, validation, parseur, moteur, règles, i18n, sauvegarde, terminal, golden, contenu historique).

### Modifié

- Le projet d'exemple utilise des codes de direction canoniques (`n`, `s`, `e`, `w`).

### Ajouté — cadrage

- Documentation complète : audit, architecture, modèle de données, roadmap, éditeur, i18n, workflow.
- Schéma JSON du format de contenu (`pyventure/schema/game.schema.json`).
- Projet d'exemple `examples/mini-game` (4 pièces, 2 objets, 2 interactions, FR/EN).
- CLI `pyventure` avec les commandes `play`, `validate` et `editor`.
- Socle d'outillage : `pyproject.toml`, `Makefile`, Ruff, pytest, pre-commit, CI GitHub Actions.
- Licence MIT.

### Décisions

- Fenêtre de jeu : **pygame-ce**, rendu logiciel, résolution de base 320×180.
- Éditeur : **Tkinter/ttk**, application séparée.
- Format de contenu : **YAML + schéma JSON**.
- Langues : **FR + EN**.
- Plateformes : **Linux** d'abord, portabilité rétro préparée.

## [0.1.0] — squelette initial

### Ajouté

- Moteur d'aventure texte historique : `start.py`, `engine.py`, `content.py`.
- Carte et premières pièces, objets et énigmes.
