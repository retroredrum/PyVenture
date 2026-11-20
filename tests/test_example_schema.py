"""Validation du schéma et de l'exemple de projet."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator
from ruamel.yaml import YAML

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "pyventure" / "schema" / "game.schema.json"
EXAMPLE = ROOT / "examples" / "mini-game" / "game.yaml"


def load_example() -> dict[str, Any]:
    data = YAML(typ="safe").load(EXAMPLE)
    assert isinstance(data, dict)
    return data


def test_schema_is_valid_json() -> None:
    json.loads(SCHEMA.read_text(encoding="utf-8"))


def test_example_matches_schema() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    errors = sorted(
        Draft202012Validator(schema).iter_errors(load_example()),
        key=lambda error: list(error.path),
    )
    assert not errors, "\n".join(f"{list(error.path)}: {error.message}" for error in errors)


def test_example_references_are_resolvable() -> None:
    data = load_example()
    rooms = data["rooms"]
    assert data["meta"]["start_room"] in rooms

    for room in rooms.values():
        for exit_value in room.get("exits", {}).values():
            target = exit_value if isinstance(exit_value, str) else exit_value["room"]
            assert target in rooms, f"sortie vers une pièce inconnue : {target}"

    for object_id, game_object in data.get("objects", {}).items():
        location = game_object.get("location")
        if location in (None, "inventory", "nowhere"):
            continue
        assert location in rooms, f"objet {object_id} dans une pièce inconnue : {location}"
