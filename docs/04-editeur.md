# 04 — Éditeur graphique de contenu

## 1. Objectif

Permettre à un auteur de créer et maintenir un jeu PyVenture **sans écrire de YAML** :

- éditer les pièces, leurs textes, sorties, variantes et illustrations ;
- ajouter des objets, leurs descriptions, états et emplacements ;
- définir des interactions entre objets et environnement ;
- gérer les flags, compteurs, messages et fins ;
- traduire le tout dans plusieurs langues ;
- valider et tester le jeu immédiatement.

L'éditeur est une **application séparée** (`pyventure-editor`), même si elle réutilise les widgets de jeu.

## 2. Principes d'UX

1. **Tout est visible** : le projet, la validation et l'aperçu ne sont jamais loin.
2. **Pas de YAML obligatoire** : les formulaires couvrent 95 % des cas ; un onglet avancé reste disponible.
3. **Feedback immédiat** : validation en continu, aperçu hot reload, erreurs cliquables.
4. **Réversible** : undo/redo partout, autosave, backups.
5. **Cohérence** : les IDs et les références sont proposés, jamais saisis à l'aveugle quand c'est évitable.

## 3. Fenêtre principale

```text
+--------------------------------------------------------------------------+
| Fichier  Édition  Projet  Affichage  Aide                                |
+----------------+--------------------------------------+------------------+
| Projet         | Éditeur                              | Inspecteur       |
|                |                                      |                  |
| ▾ Pièces       | [Formulaire] [YAML]                  | - validation     |
|   Chambre      |                                      | - références     |
|   Couloir      | Nom        [Chambre            ]      | - aperçu art     |
|   Grotte       | Description FR [..................]   |                  |
| ▾ Objets       | Description EN [..................]   |                  |
|   Lampe        | Sorties    [nord → Couloir] [+ Ajouter] |                |
|   Clé          | Art        [art/rooms/bedroom.png] [Parcourir] |             |
| ▾ Interactions |                                      |                  |
| ▾ Messages     |                                      |                  |
| ▾ Flags        |                                      |                  |
| ▾ Fins         |                                      |                  |
+----------------+--------------------------------------+------------------+
| Validation : 2 avertissements, 0 erreur                                  |
+--------------------------------------------------------------------------+
| Aperçu du jeu / Console                                                   |
+--------------------------------------------------------------------------+
```

- **Gauche** : arbre du projet, recherche, filtres.
- **Centre** : onglets d'édition (formulaire, YAML, carte, traduction).
- **Droite** : inspecteur contextuel, validation, aperçu de l'art.
- **Bas** : panneau redimensionnable avec l'aperçu du jeu et la console.

## 4. Écrans et fonctionnalités

### 4.1 Accueil / projet

- Nouveau projet (assistant : titre, langues, résolution, template).
- Ouvrir un projet récent.
- Dupliquer un projet.
- Importer un projet existant (`game.yaml`).
- Vérifier la compatibilité de version.

### 4.2 Éditeur de pièce

Champs :

- ID (slug), nom et description par langue ;
- illustration et variantes ;
- sorties : direction, destination, condition, message verrouillé, visibilité ;
- variantes : nom, description, art ;
- effets `on_enter` ;
- commentaire d'auteur.

Actions :

- ajouter une sortie réciproque ;
- dupliquer la pièce ;
- prévisualiser la pièce dans l'aperçu ;
- « jouer depuis cette pièce ».

### 4.3 Éditeur d'objet

- ID, noms et synonymes par langue ;
- description par langue ;
- emplacement initial (pièce, inventaire, nulle part) ;
- portable ;
- états (nom, description, art) et état initial ;
- art et aperçu ;
- interactions liées (filtre).

### 4.4 Éditeur d'interaction

Constructeur visuel :

```text
Verbes :        [use] [push] [+]
Objet direct :  [lampe torche ▾]   Objet indirect : [— ▾]
Prépositions :  [—]
Condition :     [ET] [pièce = grotte] [flag cave_lit = faux] [+]
Effets :        [dire flashlight_on] [flag cave_lit = vrai]
                [état lampe = on] [variante grotte = lit] [+]
Une seule fois : [x]   Priorité : [0]
```

- Listes déroulantes alimentées par le registre `rules.py`.
- Validation des références en direct.
- Onglet YAML pour les cas avancés.
- Bouton « tester cette interaction » : applique la commande dans un état simulé et affiche le résultat.

### 4.5 Vue carte

- `tk.Canvas` : une pièce = un nœud déplaçable.
- Flèches pour les sorties ; couleur différente si conditionnelle ou verrouillée.
- Glisser d'un nœud à un autre pour créer une sortie.
- Clic droit : éditer, supprimer, créer la réciproque.
- Miniature de l'art dans le nœud (option).
- Auto-layout par proximité ou grille.
- Positions sauvegardées dans `.pyventure/map.yaml` pour ne pas polluer le contenu.
- Export du plan en PNG et PDF (titre, flèches colorées, légende, miniatures).
- Clic sur une flèche pour la sélectionner (jaune) puis **Suppr** pour supprimer la sortie ; les modifications ne changent pas l'onglet actif.

### 4.6 Vue traduction

- Tableau : clé, type (pièce/objet/message/UI), colonnes par langue.
- Filtres : manquant, à relire, recherche.
- Édition inline, copie d'une langue à l'autre.
- Import/export CSV.
- Compteur de couverture.
- Vérification des placeholders (`{object}` identiques dans toutes les langues).

### 4.7 Assets

- Liste des images du projet avec vignette, dimensions, poids, usage.
- Import : copie dans `art/`, vérification du format et des dimensions, proposition de redimensionnement.
- Remplacement d'un asset sans changer les références.
- Assets manquants : bouton « générer un placeholder ».
- Assets inutilisés : signalés.

### 4.8 Validation

- Panneau permanent, groupé par gravité :
  - **Erreur** : le jeu ne peut pas démarrer (référence cassée, YAML invalide).
  - **Avertissement** : sortie non réciproque, pièce inaccessible, traduction manquante, asset absent.
  - **Info** : suggestion, doublon de synonyme.
- Double-clic : ouvre l'élément fautif.
- Bouton « revalider ».
- Mode strict pour la CI.

### 4.9 Aperçu et test

- Aperçu de la pièce dans l'éditeur : art + description + sorties.
- « Jouer » lance le jeu pygame dans un sous-processus, avec le projet courant.
- « Recharger » après sauvegarde, sans perdre l'état si possible.
- « Jouer depuis la pièce sélectionnée ».
- Console de debug : `/goto`, `/give`, `/flags`, `/set`.
- Historique des commandes de test.

## 5. Undo/redo, sauvegarde, autosave

- Chaque modification passe par une commande undo/redo maison.
- Le document connaît son état « propre » (point de sauvegarde).
- Autosave toutes les 30 s dans `.pyventure/autosave.yaml`.
- Backups horodatés dans `.pyventure/backups/`.
- Récupération proposée au démarrage après un crash.
- `ruamel.yaml` en mode round-trip pour préserver commentaires et ordre des clés.

## 6. Raccourcis clavier

| Raccourci | Action |
| --- | --- |
| `Ctrl+N` | Nouveau projet |
| `Ctrl+O` | Ouvrir |
| `Ctrl+S` | Sauvegarder |
| `Ctrl+Shift+S` | Sauvegarder sous |
| `Ctrl+Z` / `Ctrl+Shift+Z` | Undo / redo |
| `Ctrl+F` | Rechercher |
| `F5` | Recharger l'aperçu |
| `F6` | Jouer depuis la pièce |
| `Ctrl+Entrée` | Valider |
| `Suppr` | Supprimer l'élément sélectionné |

## 7. Architecture technique

- **Tkinter/ttk** (stdlib) pour rester léger et cohérent avec le choix pygame.
- `ProjectDocument` : modèle en mémoire, chargement/sauvegarde, undo.
- Pile d'undo/redo maison (`UndoStack`) avec commandes réversibles.
- `tk.Canvas` pour la carte, avec objets déplaçables et flèches.
- `ttk.Treeview` pour l'arbre de projet et les listes.
- `ttk.Notebook` pour les onglets, `tk.Text` pour les descriptions et le YAML.
- `Pillow` + `ImageTk.PhotoImage` pour les aperçus d'assets.
- Préférences dans un fichier JSON (`~/.config/pyventure/editor.json`).
- Aperçu du jeu par sous-processus pygame (`subprocess`), pour isoler les crashs et le hot reload.
- Aucune dépendance de l'éditeur dans `core`.
- Si l'éditeur devient trop complexe, PySide6 reste une alternative possible, mais ce n'est pas le choix par défaut.

## 8. MVP vs plus tard

**MVP (Phase 3)**

- Ouvrir/sauvegarder un projet.
- Éditer pièces, objets, interactions, messages, flags, fins.
- Validation.
- Aperçu et hot reload.
- Undo/redo, autosave.
- FR/EN.

**Plus tard (Phases 4–5)**

- Vue carte complète.
- Gestion avancée des assets.
- Vue traduction confortable.
- Assistant de nouveau projet.
- Import de l'ancien `content.py`.
- Export/packaging.

## 9. Tests

- Tests unitaires du document et des commandes undo.
- Tests des formulaires Tkinter sous `xvfb-run` (ou avec un affichage virtuel).
- Tests de validation : un projet invalide produit les bons messages.
- Test de round-trip YAML : charger → sauvegarder → recharger donne le même modèle.
- Test de hot reload : modifier un fichier → l'aperçu se met à jour.

## 10. Critères de sortie

- Créer un jeu de 3 pièces, 2 objets et 2 interactions sans éditer de YAML.
- Ajouter une traduction anglaise complète.
- Valider et lancer l'aperçu depuis l'éditeur.
- Sauvegarder, fermer, rouvrir : le projet est identique.
- Aucune perte de commentaire YAML après sauvegarde.
