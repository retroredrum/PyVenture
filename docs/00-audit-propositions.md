# 00 — Audit et propositions

## 1. État des lieux

Le projet est aujourd'hui un moteur d'aventure texte minimal et lisible :

- `start.py` lance `mainGame()`.
- `engine.py` contient la boucle de jeu, le parseur embryonnaire et les commandes.
- `content.py` contient les pièces, objets et actions sous forme de listes parallèles.
- `map.xlsx` sert de brouillon de carte ; certaines pièces (12 à 15) ne sont pas encore dans le code.

**Points forts**

- Le jeu tourne, l'ambiance est posée et les descriptions sont déjà écrites.
- Le code est simple, facile à modifier pour prototyper.
- Les énigmes existent déjà : lampe torche, clé, statue, porte verrouillée.

**Limites structurelles**

- Données et code mélangés (`from content import *`).
- Pièces indexées par des entiers et décrites par des listes positionnelles (`curRoomDesc[id][3]["object"]`), donc fragiles.
- Une seule action possible par pièce, portée par la pièce plutôt que par l'objet.
- Textes dans le code : édition et traduction impossibles sans toucher au Python.
- Aucune séparation entre contenu, état de partie et interface.
- Pas de sauvegarde, pas de tests, pas de validation des données.

## 2. Bugs et incohérences repérés

| # | Problème | Détail | Correctif prévu |
| --- | --- | --- | --- |
| 1 | Entrée vide | `re.findall` renvoie `[]`, puis `commandInputSplit[0]` lève `IndexError` | Parser tolérant, message d'aide |
| 2 | `get` sans objet | `commandInputSplit[1]` sans garde | Parser + message contextuel |
| 3 | `examine` ignore le nom | Affiche toujours l'`examine` de l'objet de la pièce | Résolution de l'objet ciblé |
| 4 | `quit` mort | `elif commandInputSplit == 'quit'` compare une liste à une chaîne | Commande gérée par le parseur |
| 5 | État global muté | `roomUpdate()` modifie `content.py` en mémoire : impossible de rejouer proprement | Séparation contenu / état |
| 6 | `use` trop brutal | Retire systématiquement l'objet de l'inventaire | Effets explicites dans les interactions |
| 7 | Une action par pièce | `curRoomActions` limite les possibilités | Interactions multiples, conditions et priorités |
| 8 | Exits incohérents | Ex. pièce 8 `n` → 9, pièce 9 `u` → 7 ; descriptions vides 10/11 ; pièces 12–15 absentes | Validation + migration de la carte |
| 9 | Pas de synonymes | Il faut taper exactement le nom de l'objet | Synonymes par langue |
| 10 | Pas de mode texte portable | Tout est couplé à `print`/`input` | Moteur pur + renderers terminal et pygame |
| 11 | Pas de sauvegarde | Partie perdue à la fermeture | État sérialisable JSON |
| 12 | Pas de tests | Régressions invisibles | Tests unitaires + transcripts dorés |

## 3. Propositions d'amélioration

### 3.1 Moteur

- **Contenu data-driven** : pièces, objets, interactions, flags et messages dans un fichier YAML validé par un schéma JSON.
- **Parseur plus robuste** : verbe + objet + préposition + objet, articles ignorés, synonymes, accents tolérés, abréviations (`n`, `i`, `l`), messages d'erreur contextuels.
- **État de partie explicite** : pièce courante, inventaire, flags, compteurs, états d'objets, variantes de pièces, score, tour, langue.
- **Interactions déclaratives** : conditions (`has`, `flag`, `room`, `object_state`…) et effets (`say`, `set_flag`, `move_object`, `set_room_variant`…) plutôt que du code ad hoc.
- **Sauvegarde / chargement / annulation** : JSON versionné, autosave, `undo` sur un tour.
- **Commandes de debug** : `/goto`, `/give`, `/flags`, `/set`, `/reload`, réservées au mode développeur.
- **Tests** : parseur, conditions, effets, i18n, validation, transcripts de référence.

### 3.2 Contenu et outils

- IDs stables en slug (`bedroom`, `flashlight`) au lieu d'entiers.
- Objets avec propriétés : portable, fixe, conteneur, ouvrable, verrouillé, source de lumière.
- Interactions globales filtrables par pièce, objet, verbe et condition.
- Flags et compteurs pour les énigmes et le score.
- Validateur : références cassées, exits non réciproques, pièces inaccessibles, traductions manquantes, assets absents.
- Convertisseur `content.py` → YAML pour ne pas ressaisir le jeu existant.

### 3.3 Graphismes

- Panneau pixel art au-dessus du transcript, dans la même fenêtre.
- Résolution de base **320×180** (16:9), agrandissement entier au plus proche voisin (`nearest-neighbor`).
- Une illustration par pièce, avec **variantes d'état** (pièce éclairée, porte ouverte, statue poussée…).
- Icônes d'objets pour l'inventaire et l'examen.
- Générateur d'images provisoires pour les pièces sans art (nom + couleur déterministe), afin de jouer pendant le développement.
- Plus tard : animations idle, effets de lumière, sons, musique, shader CRT optionnel.
- Accessibilité : taille de police, contraste, réduction des animations, navigation clavier.

### 3.4 Éditeur graphique

- Arbre de projet : pièces, objets, interactions, messages, flags, fins, assets.
- Formulaire de pièce : noms/descriptions par langue, sorties, variantes, art, effets d'entrée.
- Formulaire d'objet : noms, synonymes, description, emplacement, portabilité, états, art.
- Constructeur d'interactions : verbes, objets, conditions et effets en listes déroulantes, avec un onglet YAML avancé.
- Vue carte : nœuds de pièces déplaçables, flèches de sorties, validation visuelle.
- Vue traduction : colonnes par langue, filtrage des manques, import/export CSV.
- Panneau de validation cliquable, aperçu du jeu intégré, hot reload.
- Undo/redo, autosave, sauvegardes de secours, gestion des assets.

### 3.5 Multilingue

- Textes localisés dans le contenu (`{fr: ..., en: ...}`) avec langue par défaut et fallback.
- Vocabulaire du parseur par langue (verbes, directions, prépositions, synonymes).
- Chaînes d'interface dans des catalogues YAML séparés.
- Rapport de traductions manquantes, mode pseudo-locale pour tester les débordements.
- Gestion progressive du genre et du pluriel, sans sur-ingénierie au départ.

### 3.6 Qualité et distribution

- Package Python `pyventure`, CLI `pyventure` et `pyventure-editor`.
- `pyproject.toml`, Ruff, pytest, pre-commit, CI GitHub Actions.
- Mode terminal conservé comme mode de première classe.
- Packaging ultérieur (PyInstaller) pour Windows/Linux/macOS.

## 4. Priorisation

| Priorité | Chantier | Pourquoi | Effort |
| --- | --- | --- | --- |
| **Must** | Refonte data-driven + moteur | Prérequis de l'éditeur, de l'i18n et des graphismes | M |
| **Must** | Mode terminal à parité | Garantit qu'on ne casse pas le jeu | S |
| **Must** | Fenêtre pygame + panneau pixel art | Cœur de la demande | M |
| **Must** | Éditeur MVP pièces/objets/interactions | Cœur de la demande | L |
| **Must** | FR/EN de bout en bout | Cœur de la demande | M |
| **Should** | Sauvegarde/chargement, validation | Confort et fiabilité | S |
| **Should** | Vue carte et gestion d'assets | Rend l'éditeur vraiment utile | M |
| **Should** | Vue traduction | Rend l'i18n praticable | M |
| **Could** | Sons, animations, PNJ, succès | Polish | L |
| **Could** | Packaging et distribution | Diffusion | M |

## 5. Décisions validées

### Jeu : pygame-ce

- **pygame-ce** pour la fenêtre de jeu, le rendu pixel art et la boucle d'événements. C'est un fork moderne de pygame, importé sous le nom `pygame`.
- Le texte reste au cœur du jeu : transcript défilant, saisie clavier, historique, autocomplétion.
- Le rendu est volontairement simple : surfaces, `pygame.transform.scale`, pas de dépendance GPU.
- **Pas de Qt** dans le runtime du jeu : cela garde la porte ouverte aux portages rétro et aux machines modestes.

### Éditeur : Tkinter/ttk

- L'éditeur est une **application séparée**, réservée à la machine de développement.
- **Tkinter/ttk** (stdlib) pour les formulaires, l'arbre de projet, les onglets, le texte et le canevas de carte.
- `Pillow` pour les aperçus d'images et l'import d'assets.
- Aperçu du jeu par lancement d'un sous-processus pygame, ou aperçu statique de la pièce dans l'éditeur.
- Alternative si l'éditeur devient trop complexe : PySide6. Mais on commence léger.

### Format de contenu : YAML + schéma JSON

- YAML pour les textes multi-lignes, les commentaires et la lisibilité en Git.
- `ruamel.yaml` pour préserver commentaires et ordre lors des sauvegardes de l'éditeur.
- Schéma JSON comme contrat, utilisé par le validateur, l'éditeur et les tests.
- Export JSON possible plus tard pour d'autres outils.

### Graphismes

- Base **320×180**, PNG, agrandissement entier au plus proche voisin.
- Convention : `art/rooms/<piece>.png`, `art/rooms/<piece>_<variante>.png`, `art/objects/<objet>.png`, `art/endings/<fin>.png`.
- Placeholder automatique si l'asset manque.
- Résolution et facteur d'échelle configurables pour les portages.

### Plateformes

- **Linux** en priorité.
- Portabilité rétro préparée : cœur pur Python, dépendances minimales, assets portables, rendu logiciel, mode terminal de secours.
- L'éditeur n'a pas vocation à être embarqué sur les machines rétro.

### Licence

- **MIT**. Fichier `LICENSE` ajouté, mention dans le `README` et `pyproject.toml`.

### Migration

- Ne pas supprimer le moteur historique tant que la parité n'est pas prouvée.
- Convertisseur + transcripts dorés pour comparer ancien et nouveau comportement.
- Les bugs listés ci-dessus seront corrigés et documentés comme changements volontaires.

## 6. Périmètre validé

Le MVP est confirmé :

1. moteur data-driven et mode terminal à parité ;
2. fenêtre pygame avec panneau pixel art au-dessus du transcript ;
3. éditeur Tkinter pour pièces, objets et interactions ;
4. FR/EN de bout en bout ;
5. tests, validation et CI.

La vue carte, la vue traduction, les sons et les animations viennent après le MVP.

## 7. Points à affiner plus tard

1. **Style artistique** : palette, police pixel, ambiance visuelle.
2. **Troisième langue** : à décider après le MVP.
3. **Ports rétro** : cible matérielle, version de Python, taille mémoire, audio.
4. **Distribution** : GitHub Releases, itch.io, paquets Linux.
5. **Accessibilité** : contraste, taille de police, réduction des animations.
