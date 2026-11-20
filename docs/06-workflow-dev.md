# 06 — Workflow de développement

## 1. Prérequis

- Python **3.11+** (3.12 recommandé).
- Git.
- Un environnement graphique pour pygame (Linux, Windows, macOS).
- `python3-tk` pour l'éditeur Tkinter sur Linux (`sudo apt install python3-tk`).
- Facultatif : Aseprite, Krita ou tout éditeur d'images pour le pixel art.

## 2. Installation

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows : .venv\Scripts\activate
python -m pip install -e ".[dev,gui]"
```

> Sur Debian/Ubuntu récents, le Python système est « externally managed » (PEP 668) :
> `pip install` direct est refusé. Utilisez un environnement virtuel comme ci-dessus.
> Le jeu ne nécessite que les dépendances de base ; `[gui]` ajoute pygame et Pillow,
> `[dev]` ajoute les outils de test.

Extras :

| Extra | Contenu |
| --- | --- |
| *(aucun)* | Moteur + terminal (`ruamel.yaml`, `jsonschema`, `rich`) |
| `gui` | `pygame-ce`, `Pillow` |
| `dev` | `pytest`, `pytest-cov`, `ruff`, `pre-commit` |
| `all` | Tout |

Tkinter n'est pas installable via pip : c'est un paquet système (`python3-tk`). L'éditeur le détecte et affiche un message clair s'il manque.

## 3. Commandes courantes

```bash
# Jeu historique (référence, ne pas casser)
python3 start.py

# Nouveau moteur (Phase 1)
python3 -m pyventure play
python3 -m pyventure play --lang en
python3 -m pyventure play --fresh        # ignorer la reprise automatique
python3 -m pyventure play --no-autosave
python3 -m pyventure play --gui          # fenêtre pygame (Phase 2)
python3 -m pyventure play --gui --size 1280x800

# Éditeur (Phase 3)
python3 -m pyventure editor

# Validation d'un projet
python3 -m pyventure validate examples/mini-game/game.yaml
python3 -m pyventure validate --strict-i18n

# Conversion du contenu historique
python3 tools/convert_legacy.py

# Tests et qualité
pytest
pytest tests/golden
UPDATE_GOLDEN=1 pytest tests/golden
ruff check .
ruff format .

# Raccourcis
make play
make test
make lint
make format
make validate
```

## 4. Structure du dépôt

| Chemin | Rôle |
| --- | --- |
| `pyventure/core/` | Moteur pur, sans UI |
| `pyventure/ui/terminal/` | Rendu terminal |
| `pyventure/ui/pygame/` | Fenêtre de jeu pygame || `pyventure/editor/` | Éditeur de contenu |
| `pyventure/schema/` | Schéma JSON du format |
| `pyventure/locales/` | Chaînes d'interface |
| `examples/` | Projets d'exemple |
| `tests/` | Tests unitaires, golden, UI |
| `tools/` | Scripts de migration/maintenance |
| `docs/` | Spécifications et roadmap |

## 5. Conventions de code

- **Langue du code** : identifiants, docstrings et commentaires techniques en anglais.
- **Langue des docs et de l'UI** : français pour les docs, contenu localisé pour l'UI.
- **Typage** : annotations partout sur les APIs publiques.
- **Style** : Ruff, ligne 100, guillemets doubles.
- **Imports** : absolus (`from pyventure.core.engine import Engine`), pas d'étoile.
- **Erreurs** : exceptions dédiées dans `core/errors.py`, messages actionnables.
- **Pas de `print` dans `core`** : le moteur produit des `OutputLine`.
- **Pas d'état global mutable** : tout passe par `GameState` ou `ProjectDocument`.
- **Pas de dépendance UI dans `core`**.

## 6. Git

### Branches

- `main` (ou `master`) : stable.
- `feat/<sujet>` : nouvelle fonctionnalité.
- `fix/<sujet>` : correction.
- `docs/<sujet>` : documentation.
- `refactor/<sujet>` : refonte sans changement de comportement.

### Commits

Format [Conventional Commits](https://www.conventionalcommits.org/) :

```text
feat(core): add declarative interaction engine
fix(parser): handle empty input
docs(roadmap): detail phase 3
test(i18n): cover fallback chain
chore(deps): add pygame extra
```

Un commit = une intention claire. Éviter les commits fourre-tout.

### Pull requests

- Décrire le changement et les tests effectués.
- Lier l'issue ou la tâche de la roadmap.
- Vérifier que `pytest`, `ruff check` et la validation passent.
- Mettre à jour la doc si le comportement change.

## 7. Definition of Done

Une tâche est terminée quand :

- [ ] le code est implémenté et typé ;
- [ ] les tests couvrent le cas nominal et au moins un cas d'erreur ;
- [ ] `ruff check .` et `ruff format --check .` passent ;
- [ ] la validation du projet exemple passe ;
- [ ] la documentation est à jour ;
- [ ] le mode terminal n'est pas cassé ;
- [ ] la roadmap est cochée.

## 8. Ajouter du contenu

### Une pièce

1. Ajouter l'entrée dans `rooms` avec `name`, `description`, `art`.
2. Déclarer les sorties et vérifier la réciprocité.
3. Ajouter les variantes si l'état change.
4. Valider : `python -m pyventure validate <projet>`.
5. Jouer depuis la pièce (`/goto <id>` en debug).

### Un objet

1. Ajouter l'entrée dans `objects`.
2. Définir `location` (`room`, `inventory`, `nowhere`).
3. Ajouter les synonymes par langue.
4. Définir les états si nécessaire.
5. Ajouter l'icône dans `art/objects/`.

### Une interaction

1. Choisir les verbes canoniques.
2. Identifier l'objet direct/indirect.
3. Écrire les conditions `when`.
4. Écrire les effets dans l'ordre.
5. Mettre `once: true` si l'action ne doit arriver qu'une fois.
6. Tester avec `/give`, `/goto`, puis la commande réelle.

### Une traduction

1. Ajouter la langue dans `languages`.
2. Traduire les textes du contenu.
3. Ajouter le vocabulaire du parser.
4. Créer le catalogue UI.
5. Lancer en mode strict : `python -m pyventure play --lang xx --strict-i18n`.

### Un asset

1. Créer l'image en 320×180 (pièce) ou 32×32/64×64 (objet).
2. L'enregistrer en PNG dans `art/`.
3. Référencer le chemin dans le YAML.
4. Vérifier l'affichage et le redimensionnement entier.

## 9. Debug

Commandes prévues (mode développeur) :

| Commande | Effet |
| --- | --- |
| `/goto <room>` | Téléporte |
| `/give <object>` | Ajoute à l'inventaire |
| `/take <object>` | Retire de l'inventaire |
| `/flags` | Liste les flags |
| `/set <flag> <true/false>` | Modifie un flag |
| `/state` | Affiche l'état complet |
| `/reload` | Recharge le projet |
| `/lang <code>` | Change la langue |

Le mode debug est activé par `--debug` ou une variable d'environnement, jamais par défaut en release.

## 10. Tests

```bash
pytest                              # tous les tests
pytest tests/core                   # moteur uniquement
pytest -m "not gui"                 # sans pygame
SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest tests/ui
xvfb-run -a pytest tests/editor     # si Tkinter a besoin d'un affichage
```

Types de tests :

- **Unitaires** : parseur, conditions, effets, i18n, sauvegarde.
- **Golden** : suite de commandes → transcript attendu.
- **Validation** : projets valides/invalides.
- **UI** : rendu pygame headless (`SDL_VIDEODRIVER=dummy`).
- **Éditeur** : formulaires Tkinter sous `xvfb-run` si disponible.
- **Round-trip** : YAML → modèle → YAML.

## 11. CI

GitHub Actions, à chaque push/PR :

1. Installer Python 3.11 et 3.12.
2. `pip install -e ".[dev,gui]"`
3. `ruff check .`
4. `ruff format --check .`
5. `pytest -m "not gui"`
6. `SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy pytest -m gui`
7. `python -m pyventure validate examples/mini-game/game.yaml`
8. `python -m build` (wheel)

## 12. Release

1. Mettre à jour la version dans `pyproject.toml` et `pyventure/__init__.py`.
2. Mettre à jour le changelog.
3. Tag Git `vX.Y.Z`.
4. Construire le wheel et, plus tard, les exécutables PyInstaller.
5. Publier sur GitHub Releases (et itch.io si pertinent).

## 13. Licence

Le projet est distribué sous **licence MIT**. Voir le fichier [`LICENSE`](../LICENSE).

## 14. Portabilité rétro

Pour préparer d'éventuels portages :

- garder `core` sans dépendance graphique ;
- éviter les API spécifiques à Linux dans le moteur ;
- utiliser des chemins relatifs et des assets PNG/YAML ;
- tester le rendu en 320×180 et en 4:3 ;
- garder le son optionnel ;
- conserver le mode terminal comme fallback ;
- documenter les versions de Python et de pygame utilisées pour les builds figés.
