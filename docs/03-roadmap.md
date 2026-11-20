# 03 — Roadmap de développement

## Définition du MVP

Le MVP est atteint quand :

1. le jeu existant est jouable avec le nouveau moteur, en terminal **et** dans une fenêtre pygame ;
2. la fenêtre affiche une illustration pixel art au-dessus du transcript ;
3. l'éditeur permet de créer/modifier des pièces, objets et interactions sans écrire de YAML ;
4. le jeu et l'éditeur fonctionnent en français et en anglais ;
5. les tests et la validation passent.

Les phases 4 à 6 enrichissent l'ensemble mais ne bloquent pas le MVP.

---

## Phase 0 — Cadrage et socle (terminée)

**Objectif :** poser les décisions, la documentation et l'outillage.

- [x] Audit du moteur existant
- [x] Propositions d'amélioration
- [x] Architecture cible
- [x] Modèle de données et schéma JSON
- [x] Exemple de projet `examples/mini-game`
- [x] Roadmap, spécifications éditeur et i18n
- [x] `pyproject.toml`, Makefile, Ruff, pytest, pre-commit
- [x] Valider les décisions avec le mainteneur (pygame, 320×180, FR/EN, Linux, MIT)
- [x] Créer la CI GitHub Actions
- [x] Définir la licence (MIT)

**Critère de sortie :** les choix structurants sont validés et le squelette du dépôt est prêt.

---

## Phase 1 — Moteur data-driven et parité terminale (terminée)

**Objectif :** un moteur pur, testé, qui rejoue le jeu existant en mode texte.

### 1.1 Modèle et chargement

- [x] Dataclasses `GameProject`, `Room`, `Exit`, `GameObject`, `Interaction`, `Condition`, `Effect`, `Ending`
- [x] Chargement YAML avec `ruamel.yaml`
- [x] Résolution des textes localisés et fallback
- [x] Validation JSON Schema
- [x] Validation sémantique (références, exits, accessibilité)
- [x] Erreurs de chargement lisibles avec chemin YAML

### 1.2 État et moteur

- [x] `GameState` sérialisable
- [x] `Engine.execute(Command, GameState) -> TurnResult`
- [x] Commandes intégrées : `look`, `inventory`, `get`, `drop`, `examine`, `use`, `push`, `go`, `wait`, `help`, `quit`, `score`, `undo`
- [x] Interactions déclaratives, priorités, `once`
- [x] Conditions et effets du modèle
- [x] Déplacement, inventaire, états d'objets, variantes de pièces
- [x] Score et fins
- [x] Générateur aléatoire seedé pour les tests

### 1.3 Parseur

- [x] Tokenisation et normalisation (accents, articles, ponctuation)
- [x] Verbes, directions, prépositions par langue
- [x] Synonymes et verbes multi-mots
- [x] Résolution d'objets et ambiguïtés
- [x] Messages d'erreur contextuels et localisés

### 1.4 Persistance et i18n

- [x] Sauvegarde/chargement JSON versionné
- [x] Autosave
- [x] `undo` par snapshot
- [x] Catalogue UI `locales/ui.<lang>.yaml`
- [x] Changement de langue à chaud
- [x] Rapport de traductions manquantes

### 1.5 Migration et terminal

- [x] `tools/convert_legacy.py` : `content.py` → YAML
- [x] Convertir les 12 pièces existantes
- [x] Transcripts dorés de l'ancien moteur
- [x] Renderer terminal avec Rich
- [x] `python -m pyventure play`
- [x] Tests unitaires et golden

**Critère de sortie :** le jeu historique est jouable en terminal via le nouveau moteur, en FR et EN, avec sauvegarde, et les tests passent.

**État :** terminée. Moteur, parseur, règles, sauvegarde, autosave, terminal et migration du contenu historique (`examples/legacy-game`) livrés. Transcripts dorés de l'ancien et du nouveau moteur en place.

**Effort indicatif :** 3 à 5 jours.

---

## Phase 2 — Fenêtre graphique (terminée)

**Objectif :** la fenêtre pixel art + texte, en conservant le parser.

### 2.1 Fenêtre de jeu

- [x] Boucle pygame : panneau art en haut, transcript au centre, saisie en bas
- [x] Transcript défilant avec styles sémantiques et wrapping
- [x] Saisie clavier : caractères, backspace, entrée, historique haut/bas
- [x] Autocomplétion des verbes/objets (Tab)
- [x] Panneau inventaire avec icônes
- [x] Menu : nouvelle partie, sauvegarder, charger, langue, aide, quitter
- [x] Raccourcis clavier (Échap, PageUp/PageDown, molette)
- [x] Thème sombre/clair, taille de police configurable
- [x] Gestion du redimensionnement et du letterboxing

### 2.2 Art

- [x] `ArtView` : affichage 320×180, scale entier, nearest-neighbor
- [x] Résolution des variantes de pièce et d'objet
- [x] Placeholder déterministe si asset absent
- [x] Cache de surfaces
- [x] Transitions douces optionnelles
- [x] Icônes d'inventaire

### 2.3 Intégration

- [x] `pyventure play --gui`
- [x] Le mode terminal reste disponible
- [x] Gestion des erreurs de chargement dans l'UI
- [x] Mode headless `SDL_VIDEODRIVER=dummy` pour les tests
- [x] Tests headless pygame

**Critère de sortie :** on joue au jeu complet dans la fenêtre, avec art et texte, sans régression terminale.

**État :** terminée. La fenêtre joue le jeu complet : art, transcript, inventaire, saisie, menu, thème clair/sombre, taille de police et transitions.

**Effort indicatif :** 4 à 6 jours.

---

## Phase 3 — Éditeur MVP (terminée)

**Objectif :** éditer le contenu sans toucher au YAML.

### 3.1 Document et shell

- [x] `ProjectDocument` + pile d'undo/redo maison
- [x] Ouvrir/créer/sauvegarder un projet
- [x] Autosave et backups (`.pyventure/`)
- [x] Projets récents
- [x] Arbre de projet
- [x] Barre d'état et panneau de validation

### 3.2 Formulaires

- [x] Pièce : noms/descriptions par langue, art, sorties, variantes, effets d'entrée
- [x] Objet : noms, synonymes, description, emplacement, portabilité, états, art
- [x] Interaction : verbes, objets, conditions, effets, `once`, priorité
- [x] Messages : clé + traductions
- [x] Flags, compteurs, fins
- [x] Onglet YAML avancé synchronisé

### 3.3 Confort

- [x] Aperçu du jeu (lancement du jeu pygame en sous-processus)
- [x] Hot reload à la sauvegarde (l'aperçu redémarre, détection des modifications externes)
- [x] Validation en continu (panneau dédié)
- [x] Navigation vers l'élément fautif depuis la validation
- [x] Création d'un projet guidée (identifiant, titre, langues)
- [x] Undo/redo et indicateur de modifications
- [x] Duplication de pièce/objet/interaction
- [x] Renommage d'ID avec mise à jour des références

**Critère de sortie :** créer un petit jeu de 3 pièces, 2 objets et 2 interactions entièrement dans l'éditeur, le valider et y jouer.

**État :** terminée. L'éditeur Tkinter permet de créer, éditer, dupliquer, renommer, valider et lancer un projet, avec projets récents et hot reload.

**Effort indicatif :** 7 à 10 jours.

---

## Phase 4 — Vue carte et gestion des assets

**Objectif :** rendre l'édition spatiale et graphique confortable.

- [ ] `tk.Canvas` avec nœuds de pièces
- [ ] Déplacement des nœuds, sauvegarde des positions
- [ ] Flèches de sorties, couleurs par type/condition
- [ ] Création d'une sortie par glisser-déposer
- [ ] Sortie réciproque en un clic
- [ ] Auto-layout
- [ ] Miniatures d'art dans les nœuds
- [ ] Vue assets : lister, prévisualiser, importer, remplacer
- [ ] Vérification dimensions/format, génération de placeholder
- [ ] Rapport des assets manquants ou inutilisés

**Critère de sortie :** éditer la carte visuellement, importer une image et la voir dans le jeu.

**Effort indicatif :** 5 à 7 jours.

---

## Phase 5 — Workflow de traduction

**Objectif :** ajouter une langue sans toucher au code.

- [ ] Vue tableau : clés × langues
- [ ] Filtres « manquant », « à relire », recherche
- [ ] Édition côte à côte
- [ ] Import/export CSV
- [ ] Rapport de couverture par langue
- [ ] Mode pseudo-locale pour tester les débordements
- [ ] Vérification des placeholders
- [ ] Aperçu du jeu dans la langue cible

**Critère de sortie :** ajouter une troisième langue complète via l'éditeur et y jouer.

**Effort indicatif :** 3 à 4 jours.

---

## Phase 6 — Finition et contenu

**Objectif :** polish, contenu et distribution.

- [ ] Sons et musique (volume, mute)
- [ ] Animations idle, effets de lumière
- [ ] PNJ et dialogues
- [ ] Succès, score, fins multiples
- [ ] Écran de sauvegarde/chargement graphique
- [ ] Accessibilité (contraste, taille, réduction des animations)
- [ ] Packaging PyInstaller (Linux d'abord)
- [ ] Préparation d'un port rétro : build figé, résolution basse, audio optionnel
- [ ] Site ou page itch.io
- [ ] Documentation joueur

**Effort indicatif :** continu.

---

## Backlog post-MVP

- Éditeur de quêtes/objectifs.
- Hooks Python pour interactions complexes.
- Système de particules/effets.
- Support manette.
- Traductions communautaires.
- Export web (pygbag ou équivalent).
- Mode « histoire » sans parser (choix cliquables).
- Tests de régression visuelle des assets.

---

## Risques et parades

| Risque | Impact | Parade |
| --- | --- | --- |
| L'éditeur devient un projet dans le projet | Retard du MVP | Périmètre MVP strict, YAML avancé en secours |
| Le texte dans pygame demande du travail (wrapping, scroll, saisie) | Retard UI | Composant texte dédié, tests headless, prototypage tôt |
| Tkinter absent sur certaines installs Linux | Friction éditeur | Documenter `python3-tk`, mode YAML de secours |
| Production d'art trop lente | Jeu vide | Placeholders, liste d'assets, style simple |
| Portage rétro plus difficile que prévu | Report | Cœur pur, dépendances minimales, mode terminal |
| Migration de contenu buggée | Régression | Transcripts dorés, conversion progressive |
| Grammaire/i18n sous-estimée | Textes bancals | Templates simples, genre/pluriel en phase 2 |
| Sauvegardes incompatibles | Perte de partie | Versionnement + migrations |
| Scope creep | Épuisement | Roadmap par phases, critères de sortie |

---

## Suivi

- Une phase = une branche (`feat/phase-1-core`, `feat/phase-2-gui`…).
- Chaque tâche terminée coche sa case dans ce document.
- Un commit par tâche cohérente, message conventionnel.
- Mise à jour du `README` et des docs à chaque changement de comportement.
