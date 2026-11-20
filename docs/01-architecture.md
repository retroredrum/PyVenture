# 01 — Architecture cible

## 1. Principes

1. **Le moteur ne dépend d'aucune interface.** `pyventure.core` ne doit jamais importer pygame, Tkinter, Rich ou quoi que ce soit de graphique.
2. **Le contenu est une donnée, pas du code.** Le jeu se charge depuis un projet YAML validé.
3. **Le contenu et l'état sont séparés.** Le contenu est immuable pendant une partie ; l'état est sérialisable.
4. **Le mode texte reste un citoyen de première classe.** Terminal et fenêtre pygame partagent le même moteur.
5. **Tout est testable sans afficher de fenêtre.** Les tests du moteur tournent en headless.
6. **On migre progressivement.** Le moteur historique reste jouable jusqu'à parité.

## 2. Arborescence cible

```text
PyVenture/
├── pyproject.toml
├── Makefile
├── README.md
├── CONTRIBUTING.md
├── docs/
├── examples/
│   └── mini-game/
│       ├── game.yaml
│       └── art/
├── pyventure/
│   ├── __init__.py
│   ├── __main__.py
│   ├── cli.py
│   ├── core/
│   │   ├── model.py        # dataclasses du contenu
│   │   ├── loader.py       # YAML -> modèle, migrations
│   │   ├── schema.py       # validation JSON Schema + règles sémantiques
│   │   ├── parser.py       # texte -> Command
│   │   ├── engine.py       # GameState + exécution des tours
│   │   ├── rules.py        # conditions, effets, registre de specs
│   │   ├── i18n.py         # LocalizedText, fallback, formatage
│   │   ├── save.py         # sauvegarde/chargement JSON
│   │   ├── art.py          # résolution des assets + placeholders
│   │   ├── events.py       # OutputLine, TurnResult, styles
│   │   └── errors.py
│   ├── ui/
│   │   ├── terminal/
│   │   │   ├── app.py
│   │   │   └── render.py
│   │   └── pygame/
│   │       ├── app.py
│   │       ├── game.py
│   │       ├── art_view.py
│   │       ├── transcript.py
│   │       ├── command_input.py
│   │       ├── inventory_panel.py
│   │       ├── text.py
│   │       └── theme.py
│   ├── editor/
│   │   ├── app.py
│   │   ├── document.py     # document + undo/redo
│   │   ├── main_window.py
│   │   ├── forms/
│   │   ├── map_view.py
│   │   ├── translation_view.py
│   │   ├── validation_panel.py
│   │   ├── preview.py
│   │   └── assets.py
│   ├── schema/
│   │   └── game.schema.json
│   └── locales/
│       ├── ui.fr.yaml
│       └── ui.en.yaml
├── tests/
│   ├── core/
│   ├── ui/
│   ├── editor/
│   └── golden/
└── tools/
    └── convert_legacy.py
```

## 3. Dépendances entre couches

```text
                 +-------------------+
                 |   pyventure.cli   |
                 +---------+---------+
                           |
          +----------------+----------------+
          |                                 |
  +-------v--------+                +-------v--------+
  | ui/terminal    |                | ui/pygame      |
  +-------+--------+                +-------+--------+
          |                                 |
          +----------------+----------------+
                           |
                  +--------v--------+
                  |  core (pur)     |
                  +-----------------+
                           ^
                           |
                  +--------+--------+
                  |    editor       |
                  |  (Tkinter/ttk)  |
                  +-----------------+
```

- `core` : standard library + `ruamel.yaml` + `jsonschema`.
- `ui/terminal` : `core` + `rich` (optionnel, fallback ANSI).
- `ui/pygame` : `core` + `pygame-ce` + `Pillow`.
- `editor` : `core` + Tkinter/ttk + `Pillow`.
- Tkinter est fourni avec Python, mais nécessite le paquet système `python3-tk` sur Linux.
- Aucun import de `ui` ou `editor` dans `core`.

## 4. Flux d'exécution d'un tour

```text
Saisie utilisateur
      |
      v
Parser (langue courante, vocabulaire du projet)
      |
      v
Command(verbe, objet, préposition, objet indirect)
      |
      v
Engine.execute(command, state)
      |
      +--> interactions du projet (conditions -> effets)
      +--> commandes intégrées (look, get, drop, examine, inventory, go...)
      +--> erreurs contextuelles
      |
      v
TurnResult(output, state, art_hint, sound, ended)
      |
      v
Renderer terminal ou pygame
```

### Types principaux

```python
@dataclass(frozen=True)
class Command:
    verb: str
    direct: str | None = None
    preposition: str | None = None
    indirect: str | None = None
    raw: str = ""

@dataclass
class TurnResult:
    lines: list[OutputLine]
    state: GameState
    art: ArtHint | None = None
    sound: str | None = None
    ended: Ending | None = None

@dataclass(frozen=True)
class OutputLine:
    text: str
    style: Style = Style.NORMAL
```

`Style` est sémantique (`ROOM_TITLE`, `DESCRIPTION`, `EXIT`, `ITEM`, `ERROR`, `SYSTEM`, `DIALOGUE`). Le terminal le traduit en ANSI, pygame en couleurs et polices. Le moteur ne connaît aucune couleur.

## 5. Contenu vs état

### Contenu (`GameProject`)

Chargé une fois, immuable :

- métadonnées, langues, vocabulaire ;
- pièces, sorties, variantes ;
- objets, états ;
- interactions, conditions, effets ;
- messages, flags initiaux, compteurs, fins ;
- chemins d'assets.

### État (`GameState`)

Créé au démarrage ou chargé depuis une sauvegarde :

- pièce courante, langue ;
- emplacement des objets (pièce, inventaire, nulle part) ;
- états d'objets et variantes de pièces ;
- flags, compteurs, score, nombre de tours ;
- historique pour `undo` ;
- graine aléatoire éventuelle.

L'état ne contient **jamais** de texte traduit en dur : il référence des clés ou des IDs.

## 6. Parseur

- Normalisation : minuscules, espaces multiples, ponctuation légère, accents ignorés pour la comparaison.
- Articles ignorés : `le, la, les, un, une, des, the, a, an`.
- Verbes et directions issus du vocabulaire du projet, avec synonymes et abréviations.
- Verbes multi-mots supportés (`pick up`, `switch on`), match du plus long au plus court.
- Résolution des objets dans la portée visible : inventaire + objets de la pièce + objets fixes visibles.
- Ambiguïté : « Prendre quelle lampe ? » plutôt qu'un choix arbitraire.
- Formes supportées : `verbe`, `verbe objet`, `verbe objet préposition objet`.
- Les interactions du projet sont testées **avant** les commandes intégrées, pour pouvoir surcharger `use` ou `push`.
- Toute erreur est localisée et contextuelle.

## 7. Règles et interactions

Chaque interaction déclare :

- un ou plusieurs verbes canoniques ;
- un objet direct et/ou indirect optionnel ;
- des conditions (`when`) ;
- des effets ordonnés ;
- `once` et une priorité éventuelle.

Les conditions et effets sont évalués par un registre central (`rules.py`) qui fournit aussi les métadonnées utilisées par l'éditeur pour construire les formulaires. Une seule source de vérité pour le moteur, le validateur et l'UI.

## 8. Sauvegarde

Format JSON versionné :

```json
{
  "format": "pyventure-save",
  "format_version": 1,
  "project": {"id": "the-old-house", "version": "0.1.0"},
  "saved_at": "2026-11-20T12:00:00Z",
  "language": "fr",
  "state": {}
}
```

- Vérification de l'ID du projet au chargement.
- Migration si `format_version` change.
- Autosave dans le dossier de sauvegarde de l'utilisateur.
- `undo` par snapshot de `GameState` (petit, copie profonde acceptable).

## 9. Graphismes avec pygame

- `ArtResolver` choisit l'image : variante de pièce > pièce > placeholder.
- Résolution de base **320×180**, scale entier, filtre nearest.
- Chargement via `pygame.image.load`, conversion `convert_alpha()`, cache côté UI uniquement.
- Agrandissement via `pygame.transform.scale` (pas `smoothscale`).
- Placeholder déterministe généré avec Pillow si l'asset manque.
- Les chemins sont relatifs à la racine du projet.
- Validation : existence, dimensions, format PNG.
- Rendu logiciel uniquement : pas de shader ni de dépendance GPU obligatoire.

### Fenêtre de jeu

- Une seule fenêtre : art en haut, transcript au centre, saisie en bas.
- Le transcript est une liste de lignes stylées, avec wrapping et scroll.
- Saisie clavier native pygame : caractères, backspace, historique, copier/coller via `pygame.scrap` si disponible.
- Police pixel pour les titres, police lisible pour le corps ; tailles configurables.
- Inventaire en panneau latéral ou en overlay.
- Menus simples (nouvelle partie, sauvegarder, charger, langue, aide).

## 10. Éditeur Tkinter/ttk

- `ProjectDocument` : modèle en mémoire + pile d'undo/redo maison.
- `ruamel.yaml` en mode round-trip pour préserver commentaires et ordre.
- Validation en continu (schéma + règles sémantiques).
- Formulaires `ttk`, arbre `ttk.Treeview`, onglets `ttk.Notebook`, texte `tk.Text`.
- Vue carte sur `tk.Canvas` : nœuds, flèches, drag-and-drop.
- Aperçu : lancement du jeu pygame dans un sous-processus, ou aperçu statique de la pièce.
- L'éditeur ne modifie jamais les fichiers sans passer par le document.
- Autosave et backups dans `.pyventure/` à la racine du projet.
- Tkinter reste optionnel : le jeu et le mode terminal ne l'importent jamais.

## 11. Migration depuis le moteur historique

1. Garder `engine.py`, `content.py`, `start.py` intacts pendant la Phase 1.
2. Écrire `tools/convert_legacy.py` : `content.py` → YAML (meilleur effort).
3. Capturer des transcripts dorés des pièces 0 à 11 avec l'ancien moteur.
4. Faire tourner le nouveau moteur sur les mêmes commandes et comparer.
5. Corriger les bugs listés dans l'audit, en documentant les différences.
6. Supprimer l'ancien moteur seulement après validation.

## 12. Tests et qualité

- Tests unitaires du parseur, des conditions, des effets, de l'i18n et du validateur.
- Tests « golden » : suite de commandes → transcript attendu, par langue.
- Validation du schéma et de l'exemple dans la CI.
- Tests pygame headless avec `SDL_VIDEODRIVER=dummy` et `SDL_AUDIODRIVER=dummy`.
- Tests Tkinter sous `xvfb-run` si l'environnement le permet.
- Ruff pour le lint et le format.
- CI GitHub Actions : lint, tests, validation, build du wheel.

## 13. Portabilité et machines rétro

Le choix de pygame et d'un cœur pur Python prépare des portages futurs.

- **Pas de dépendance Qt** dans le runtime.
- **Rendu logiciel** : éviter les fonctions GPU-only.
- **Résolution et échelle configurables** : 320×180 par défaut, letterboxing possible en 4:3.
- **Assets portables** : PNG, YAML, polices libres ; pas de format propriétaire.
- **Pas de chemins absolus** ni de suppositions sur la casse des fichiers.
- **Mode terminal** comme secours si l'affichage graphique n'est pas disponible.
- **Dépendances minimales** : le cœur ne requiert que `ruamel.yaml` et `jsonschema`.
- **Audio optionnel** : le jeu doit rester jouable sans son.
- **Builds séparés** : PyInstaller pour Linux ; un port rétro pourra geler une version plus ancienne de Python ou réimplémenter le renderer.
- **Éditeur non embarqué** : Tkinter et Pillow restent des outils de développement.

## 14. Non-objectifs (pour l'instant)

- Éditeur de sprites intégré (utiliser Aseprite/Krita).
- Multijoueur.
- 3D.
- Qt/PySide6 dans le runtime.
- Langage de script complet : les interactions déclaratives suffisent au MVP ; des hooks Python pourront venir plus tard.
- Support mobile.
