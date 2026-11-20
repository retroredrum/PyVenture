"""Convertit le contenu du moteur historique (``content.py``) vers le format YAML.

Usage :

    python3 tools/convert_legacy.py
    python3 tools/convert_legacy.py --source content.py --out examples/legacy-game

La conversion est volontairement « meilleur effort » : les identifiants
numériques deviennent des slugs ``room-<n>``, les descriptions d'objets
génériques sont à retravailler, et les textes sont en anglais (langue du
conteneur historique). Le résultat sert de point de départ éditable.
"""

from __future__ import annotations

import argparse
import importlib.util
import io
import sys
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq

REPO_ROOT = Path(__file__).resolve().parent.parent

EN_VERBS = {
    "get": "get",
    "take": "get",
    "look": "look",
    "examine": "look",
    "use": "use",
    "push": "push",
    "go": "go",
    "inv": "inventory",
    "inventory": "inventory",
    "quit": "quit",
}

EN_DIRECTIONS = {
    "n": "n",
    "north": "n",
    "s": "s",
    "south": "s",
    "e": "e",
    "east": "e",
    "w": "w",
    "west": "w",
    "u": "u",
    "up": "u",
    "d": "d",
    "down": "d",
}


def load_legacy_module(source: Path) -> Any:
    spec = importlib.util.spec_from_file_location("legacy_content", source)
    if spec is None or spec.loader is None:
        raise SystemExit(f"impossible de charger {source}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def room_slug(room_id: int) -> str:
    return f"room-{room_id}"


def object_slug(name: str) -> str:
    return name.strip().lower().replace(" ", "-")


def build_project(module: Any) -> CommentedMap:
    rooms_data: list[list[Any]] = module.curRoomDesc
    actions_data: list[list[Any]] = module.curRoomActions

    project = CommentedMap()
    project["format"] = "pyventure-game"
    project["format_version"] = 1

    meta = CommentedMap()
    meta["id"] = "legacy-house"
    meta["title"] = "The Old House (legacy)"
    meta["default_language"] = "en"
    meta["start_room"] = room_slug(7)
    meta["version"] = "0.1.0"
    meta["max_score"] = 0
    meta["art"] = CommentedMap({"width": 320, "height": 180, "scale": 3})
    project["meta"] = meta
    project["languages"] = ["en"]

    # -- Objets ---------------------------------------------------------
    objects: CommentedMap = CommentedMap()
    object_locations: dict[str, int] = {}
    for entry in rooms_data:
        room_id = entry[0]
        payload = entry[3] if len(entry) > 3 else {}
        name = (payload or {}).get("object") or ""
        if name:
            object_locations.setdefault(name, room_id)

    # Cibles d'action qui ne sont pas des objets ramassables.
    fixed_objects = {"statue": 7, "tree": 6}
    for name, room_id in fixed_objects.items():
        object_locations.setdefault(name, room_id)

    for name, room_id in object_locations.items():
        slug = object_slug(name)
        game_object = CommentedMap()
        game_object["name"] = name
        game_object["description"] = f"A {name}."
        game_object["location"] = room_slug(room_id)
        game_object["portable"] = name not in fixed_objects
        if name == "rope":
            game_object["description"] = "There's a rope hanging from the tree."
        objects[slug] = game_object
    objects.yaml_set_comment_before_after_key(
        "flashlight", before="TODO: descriptions d'objets génériques, à affiner."
    )
    project["objects"] = objects

    # -- Pièces ---------------------------------------------------------
    rooms: CommentedMap = CommentedMap()
    for entry in rooms_data:
        room_id = entry[0]
        exits_list = entry[1]
        description = entry[2]
        exits = CommentedMap()
        for index in range(0, len(exits_list) - 1, 2):
            direction = exits_list[index]
            target = exits_list[index + 1]
            exits[direction] = room_slug(int(target))
        room = CommentedMap()
        room["name"] = f"Room {room_id}"
        room["description"] = description if description else f"Room {room_id}."
        if exits:
            room["exits"] = exits
        rooms[room_slug(room_id)] = room

    # -- Messages et interactions --------------------------------------
    messages: CommentedMap = CommentedMap()
    flags: CommentedMap = CommentedMap()
    counters: CommentedMap = CommentedMap({"score": 0})
    interactions = CommentedSeq()

    for action in actions_data:
        if len(action) < 6:
            continue
        room_id, target_object, message, new_description, _used, new_exit = action[:6]
        room = room_slug(room_id)
        slug = object_slug(str(target_object))

        message_key = f"room_{room_id}_action"
        messages[message_key] = message

        variant_name = "changed"
        variant = CommentedMap()
        variant["description"] = new_description
        rooms[room]["variants"] = CommentedMap({variant_name: variant})

        direction, target = new_exit
        flag_name = f"{room}_changed"
        flags[flag_name] = False

        effects = CommentedSeq()
        effects.append(CommentedMap({"say": message_key}))
        effects.append(CommentedMap({"set_flag": flag_name}))
        effects.append(CommentedMap({"set_room_variant": {"room": room, "variant": variant_name}}))
        effects.append(
            CommentedMap(
                {
                    "set_exit": {
                        "room": room,
                        "direction": direction,
                        "target": room_slug(int(target)),
                    }
                }
            )
        )
        if slug not in objects:
            objects[slug] = CommentedMap(
                {
                    "name": str(target_object),
                    "description": f"A {target_object}.",
                    "location": "nowhere",
                    "portable": False,
                }
            )

        interaction = CommentedMap()
        interaction["id"] = f"{room}-{slug}"
        interaction["verbs"] = ["use", "push"]
        interaction["objects"] = [slug]
        interaction["when"] = CommentedSeq([CommentedMap({"room": room})])
        interaction["effects"] = effects
        interaction["once"] = True
        interactions.append(interaction)

    project["flags"] = flags
    project["counters"] = counters
    project["vocabulary"] = CommentedMap(
        {
            "verbs": CommentedMap({"en": CommentedMap(EN_VERBS)}),
            "directions": CommentedMap({"en": CommentedMap(EN_DIRECTIONS)}),
        }
    )
    project["messages"] = messages
    project["rooms"] = rooms
    project["interactions"] = interactions

    project.yaml_set_comment_before_after_key(
        "format",
        before=(
            "Généré par tools/convert_legacy.py depuis content.py.\n"
            "Conversion meilleur effort : à retravailler dans l'éditeur."
        ),
    )
    return project


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Convertit content.py vers le format PyVenture.")
    parser.add_argument("--source", type=Path, default=REPO_ROOT / "content.py")
    parser.add_argument("--out", type=Path, default=REPO_ROOT / "examples" / "legacy-game")
    args = parser.parse_args(argv)

    if not args.source.is_file():
        print(f"Source introuvable : {args.source}", file=sys.stderr)
        return 1

    module = load_legacy_module(args.source)
    project = build_project(module)

    args.out.mkdir(parents=True, exist_ok=True)
    target = args.out / "game.yaml"
    yaml = YAML()
    yaml.indent(mapping=2, sequence=4, offset=2)
    buffer = io.StringIO()
    yaml.dump(project, buffer)
    target.write_text(buffer.getvalue(), encoding="utf-8")
    print(f"Écrit {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
