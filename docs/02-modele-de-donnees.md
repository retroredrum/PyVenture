# 02 — Modèle de données

## 1. Principes

- Un projet de jeu est un fichier YAML (`game.yaml`) + un dossier `art/`.
- Les identifiants sont des slugs stables : `bedroom`, `flashlight`, `light-cave`.
- Les textes sont localisés : soit une chaîne (identique dans toutes les langues), soit un objet `{fr: ..., en: ...}`.
- Le contenu ne contient pas d'état de partie. Les flags ont seulement une valeur initiale.
- Le schéma de référence est [`pyventure/schema/game.schema.json`](../pyventure/schema/game.schema.json).
- Un exemple complet est fourni dans [`examples/mini-game/game.yaml`](../examples/mini-game/game.yaml).

## 2. Structure d'un projet

```text
mon-jeu/
├── game.yaml
├── art/
│   ├── rooms/
│   │   ├── bedroom.png
│   │   └── cave_lit.png
│   ├── objects/
│   │   └── flashlight.png
│   └── endings/
│       └── escaped.png
└── .pyventure/          # cache, autosave, backups (généré)
```

## 3. Structure générale du fichier

```yaml
format: pyventure-game
format_version: 1

meta:
  id: the-old-house
  title: {fr: La Vieille Maison, en: The Old House}
  default_language: fr
  start_room: bedroom
  version: "0.1.0"
  max_score: 50
  art: {width: 320, height: 180, scale: 3}

languages: [fr, en]

flags: {}
counters: {}
vocabulary: {}
messages: {}
rooms: {}
objects: {}
interactions: []
endings: {}
```

## 4. Métadonnées (`meta`)

| Champ | Type | Obligatoire | Rôle |
| --- | --- | --- | --- |
| `id` | slug | oui | Identifiant stable du projet (sauvegardes) |
| `title` | texte localisé | oui | Titre affiché |
| `default_language` | code langue | oui | Langue de départ et fallback |
| `start_room` | ID de pièce | oui | Pièce initiale |
| `version` | chaîne | non | Version du contenu |
| `max_score` | entier | non | Score maximal, pour l'affichage |
| `authors` | liste de chaînes | non | Crédits |
| `description` | texte localisé | non | Résumé du jeu |
| `art` | objet | non | Résolution de base et facteur d'échelle |

## 5. Langues

```yaml
languages: [fr, en]
```

- Codes BCP-47 courts (`fr`, `en`, `pt-BR`).
- `default_language` doit figurer dans `languages`.
- Le fallback est : langue demandée → langue par défaut → première langue.
- Les clés de traduction inconnues sont signalées par le validateur.

## 6. Flags et compteurs

```yaml
flags:
  front_door_unlocked: false
  cave_lit: false

counters:
  score: 0
  visits: 0
```

- Les flags sont des booléens.
- Les compteurs sont des entiers.
- Les effets peuvent les modifier ; les conditions peuvent les tester.
- Les flags internes créés par `once` sont préfixés par `_done:` et ne sont pas listés dans le fichier.

## 7. Vocabulaire du parseur

Le vocabulaire est **par langue**. Les clés sont les mots tapés par le joueur ; les valeurs sont des identifiants canoniques, indépendants de la langue.

```yaml
vocabulary:
  verbs:
    fr:
      prendre: get
      ramasser: get
      regarder: look
      examiner: look
      utiliser: use
      pousser: push
      aller: go
      inventaire: inventory
      quitter: quit
    en:
      get: get
      take: get
      look: look
      examine: look
      use: use
      push: push
      go: go
      inventory: inventory
      quit: quit
  directions:
    fr: {nord: n, sud: s, est: e, ouest: w, haut: u, bas: d}
    en: {north: n, south: s, east: e, west: w, up: u, down: d}
  prepositions:
    fr: {dans: in, sur: on, avec: with, sous: under}
    en: {in: in, on: on, with: with, under: under}
```

- Les verbes canoniques du moteur : `look`, `inventory`, `get`, `drop`, `examine`, `use`, `push`, `go`, `wait`, `help`, `quit`, `save`, `load`, `undo`, `language`, `score`.
- Un verbe inconnu du moteur peut être utilisé par une interaction (`read`, `dig`, `switch`…).
- Les verbes multi-mots sont autorisés (`pick up: get`).
- Les directions canoniques sont `n, s, e, w, u, d`, plus `in` et `out` si besoin.

## 8. Messages

```yaml
messages:
  door_locked:
    fr: La porte est verrouillée.
    en: The door is locked.
  flashlight_on:
    fr: "Vous allumez la lampe. La grotte s'éclaire."
    en: "You switch on the lamp. The cave lights up."
```

- Les effets `say` référencent une clé de message.
- Les messages peuvent contenir des placeholders : `{object}`, `{room}`, `{player}`.
- Un effet `say` peut aussi contenir un texte localisé inline pour les messages à usage unique.

## 9. Pièces

```yaml
rooms:
  bedroom:
    name: {fr: Chambre, en: Bedroom}
    description:
      fr: |
        Vous êtes dans une chambre poussiéreuse.
        Une lampe torche traîne sur la table de nuit.
      en: |
        You are in a dusty bedroom.
        A flashlight lies on the nightstand.
    art: rooms/bedroom.png
    exits:
      n: corridor
    variants:
      dark:
        description:
          fr: Il fait noir.
          en: It is dark.
        art: rooms/bedroom_dark.png
    on_enter:
      - say: bedroom_enter
```

| Champ | Type | Obligatoire | Rôle |
| --- | --- | --- | --- |
| `name` | texte localisé | oui | Nom court |
| `description` | texte localisé | oui | Description par défaut |
| `art` | chemin | non | Illustration par défaut |
| `exits` | map direction → sortie | non | Sorties |
| `variants` | map nom → variante | non | Descriptions/arts alternatifs |
| `on_enter` | liste d'effets | non | Effets à l'entrée |
| `comment` | chaîne | non | Note d'auteur |

### Sorties

Les clés de `exits` sont des **codes de direction canoniques** : `n`, `s`, `e`, `w`, `u`, `d` (et `in`, `out` si besoin). Les mots tapés par le joueur (`nord`, `north`, `n`…) sont définis dans `vocabulary.directions`.

Forme courte :

```yaml
exits:
  n: corridor
```

Forme complète :

```yaml
exits:
  e:
    room: vault
    when:
      - flag: cave_lit
    locked_message: door_locked
    hidden: true
```

| Champ | Type | Rôle |
| --- | --- | --- |
| `room` | ID de pièce | Destination |
| `when` | condition ou liste | Condition d'accès |
| `locked_message` | message | Affiché si la condition échoue |
| `hidden` | booléen | Ne pas lister la sortie tant que la condition échoue |

### Variantes de pièce

Une variante remplace la description et/ou l'art. Elle est activée par l'effet `set_room_variant`.

## 10. Objets

```yaml
objects:
  flashlight:
    name: {fr: lampe torche, en: flashlight}
    synonyms:
      fr: [lampe, torche]
      en: [torch, light]
    description:
      fr: Une lampe torche en métal, encore en état de marche.
      en: A metal flashlight, still working.
    location: bedroom
    portable: true
    art: objects/flashlight.png
    states:
      off:
        description: {fr: La lampe est éteinte., en: The flashlight is off.}
      on:
        description: {fr: La lampe est allumée., en: The flashlight is on.}
    initial_state: off
```

| Champ | Type | Obligatoire | Rôle |
| --- | --- | --- | --- |
| `name` | texte localisé | oui | Nom affiché |
| `synonyms` | map langue → liste | non | Mots acceptés par le parseur |
| `description` | texte localisé | oui | Description par défaut |
| `location` | ID de pièce, `inventory` ou `nowhere` | non | Emplacement initial |
| `portable` | booléen | non (défaut `true`) | Peut être pris |
| `art` | chemin | non | Icône / illustration |
| `states` | map nom → état | non | États alternatifs |
| `initial_state` | chaîne | non | État de départ |
| `comment` | chaîne | non | Note d'auteur |

Un objet `nowhere` existe mais n'est pas encore dans le monde. Un objet `inventory` commence dans l'inventaire du joueur.

### États d'objet

Un état peut remplacer la description et/ou l'art. Il est activé par `set_object_state`.

## 11. Interactions

Les interactions sont globales et filtrées par conditions. Elles sont évaluées avant les commandes intégrées, par priorité décroissante puis par ordre du fichier.

```yaml
interactions:
  - id: light-cave
    verbs: [use]
    objects: [flashlight]
    when:
      - room: cave
      - not_flag: cave_lit
    effects:
      - say: flashlight_on
      - set_flag: cave_lit
      - set_object_state: {object: flashlight, state: on}
      - set_room_variant: {room: cave, variant: lit}
    once: true

  - id: unlock-vault
    verbs: [use]
    objects: [key]
    when:
      - room: vault
    effects:
      - say: vault_open
      - add_counter: {name: score, delta: 10}
      - end_game: escaped
```

| Champ | Type | Obligatoire | Rôle |
| --- | --- | --- | --- |
| `id` | slug | oui | Identifiant unique |
| `verbs` | liste de verbes canoniques | oui | Verbes déclencheurs |
| `objects` | liste d'IDs | non | Objet direct attendu ; absent = commande sans objet |
| `indirect_objects` | liste d'IDs | non | Objet indirect attendu |
| `prepositions` | liste | non | Prépositions attendues (`in`, `on`, `with`…) |
| `when` | condition ou liste | non | Conditions d'activation |
| `effects` | liste d'effets | oui | Effets appliqués dans l'ordre |
| `once` | booléen | non | Ne s'exécute qu'une fois |
| `priority` | entier | non | Plus grand = testé en premier |
| `comment` | chaîne | non | Note d'auteur |

## 12. Conditions

Une condition est un objet avec **une seule** clé. `when` accepte une condition ou une liste (ET implicite).

| Clé | Exemple | Sens |
| --- | --- | --- |
| `has` | `has: key` | Le joueur possède l'objet |
| `not_has` | `not_has: key` | Le joueur ne possède pas l'objet |
| `flag` | `flag: cave_lit` | Le flag est vrai |
| `not_flag` | `not_flag: cave_lit` | Le flag est faux |
| `room` | `room: cave` | Le joueur est dans la pièce |
| `object_state` | `object_state: {object: flashlight, state: on}` | État d'un objet |
| `counter` | `counter: {name: visits, gte: 3}` | Comparaison de compteur (`eq`, `gte`, `lte`) |
| `score` | `score: {gte: 10}` | Comparaison du score |
| `any` | `any: [{flag: a}, {flag: b}]` | OU |
| `all` | `all: [{flag: a}, {room: cave}]` | ET explicite |
| `not` | `not: {flag: a}` | Négation |

## 13. Effets

Un effet est un objet avec **une seule** clé. Ils sont appliqués dans l'ordre.

| Clé | Exemple | Effet |
| --- | --- | --- |
| `say` | `say: door_locked` | Affiche un message (clé ou texte localisé) |
| `set_flag` | `set_flag: cave_lit` | Met le flag à vrai |
| `clear_flag` | `clear_flag: cave_lit` | Met le flag à faux |
| `set_counter` | `set_counter: {name: visits, value: 0}` | Fixe un compteur |
| `add_counter` | `add_counter: {name: score, delta: 10}` | Ajoute au compteur |
| `move_object` | `move_object: {object: key, to: inventory}` | Déplace un objet |
| `remove_object` | `remove_object: key` | Envoie l'objet nulle part |
| `set_object_state` | `set_object_state: {object: flashlight, state: on}` | Change l'état |
| `set_room_variant` | `set_room_variant: {room: cave, variant: lit}` | Change la variante |
| `set_exit` | `set_exit: {room: lobby, direction: w, target: path}` | Crée/modifie une sortie |
| `remove_exit` | `remove_exit: {room: lobby, direction: w}` | Supprime une sortie |
| `teleport` | `teleport: vault` | Déplace le joueur |
| `score` | `score: 10` | Ajoute au score |
| `end_game` | `end_game: escaped` | Termine la partie |
| `play_sound` | `play_sound: door_open` | Joue un son |

## 14. Fins

```yaml
endings:
  escaped:
    title: {fr: Évasion, en: Escape}
    text:
      fr: |
        Vous ressortez de la caverne, le trésor en main.
      en: |
        You emerge from the cave, treasure in hand.
    art: endings/escaped.png
```

Une fin est déclenchée par `end_game`. Le moteur affiche le titre et le texte, puis propose de recommencer ou de quitter.

## 15. Conventions d'assets

```text
art/rooms/<room_id>.png              # illustration par défaut
art/rooms/<room_id>_<variant>.png    # variante
art/objects/<object_id>.png          # icône / illustration
art/endings/<ending_id>.png          # illustration de fin
```

- PNG, résolution de base 320×180 pour les pièces.
- Icônes d'objets : 32×32 ou 64×64.
- Agrandissement entier uniquement.
- Un asset manquant produit un placeholder, pas un crash.
- Le validateur signale les assets absents et les dimensions incorrectes.

## 16. Validation sémantique

Au-delà du schéma JSON, le validateur vérifie :

- `default_language` ∈ `languages` ;
- `start_room` existe ;
- les destinations de sorties existent ;
- les emplacements d'objets existent (`room`, `inventory`, `nowhere`) ;
- les références de conditions/effets existent (objets, pièces, flags, compteurs, messages, fins) ;
- `initial_state` existe dans `states` ;
- les IDs d'interactions sont uniques ;
- les variantes et états référencés existent ;
- les sorties non réciproques et les pièces inaccessibles sont signalées (avertissements) ;
- les traductions manquantes sont signalées selon le mode strict ;
- les doublons de synonymes sont signalés ;
- les assets manquants sont signalés.

## 17. Sauvegarde (rappel)

Le contenu est immuable ; seule la partie (`GameState`) est sauvegardée. Format JSON versionné, avec l'ID et la version du projet pour détecter les incompatibilités. Voir [`01-architecture.md`](01-architecture.md#8-sauvegarde).

## 18. Correspondance avec l'ancien format

| Ancien | Nouveau |
| --- | --- |
| `curRoomDesc[id][1]` (liste direction/ID) | `rooms.<id>.exits` |
| `curRoomDesc[id][2]` | `rooms.<id>.description` |
| `curRoomDesc[id][3]["object"]` | `objects.<id>.location` |
| `curRoomActions[id][1]` (objet) | `interactions[].objects` |
| `curRoomActions[id][2]` (message) | `interactions[].effects[].say` |
| `curRoomActions[id][3]` (nouvelle description) | `rooms.<id>.variants` |
| `curRoomActions[id][5]` (nouvelle sortie) | `effects.set_exit` |
| `errorMessage` | `messages` + catalogue UI |
| `welcomeMessage` | `messages` + `meta` |

Le convertisseur `tools/convert_legacy.py` fera ce mapping automatiquement, avec des avertissements pour les cas ambigus.
