"""Validation d'un projet : schéma JSON puis règles sémantiques."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .model import Condition, Effect, GameProject

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schema" / "game.schema.json"

_RESERVED_LOCATIONS = {"inventory", "nowhere"}


def load_schema(path: Path | None = None) -> dict[str, Any]:
    schema_file = path or SCHEMA_PATH
    return json.loads(schema_file.read_text(encoding="utf-8"))


def validate_data(data: dict[str, Any], schema_path: Path | None = None) -> list[str]:
    """Valide un dictionnaire brut contre le schéma JSON."""
    from jsonschema import Draft202012Validator

    schema = load_schema(schema_path)
    validator = Draft202012Validator(schema)
    problems: list[str] = []
    for error in sorted(validator.iter_errors(data), key=lambda item: list(item.path)):
        location = ".".join(str(part) for part in error.absolute_path) or "<racine>"
        problems.append(f"{location}: {error.message}")
    return problems


def _iter_conditions(conditions: tuple[Condition, ...]):
    for condition in conditions:
        yield condition
        if condition.kind in {"any", "all"}:
            yield from _iter_conditions(condition.args["conditions"])
        elif condition.kind == "not":
            yield from _iter_conditions((condition.args["condition"],))


def _iter_effects(effects: tuple[Effect, ...]):
    yield from effects


def _check_condition(condition: Condition, project: GameProject, problems: list[str]) -> None:
    args = condition.args
    kind = condition.kind
    if kind in {"has", "not_has"} and args.get("object") not in project.objects:
        problems.append(f"condition {kind}: objet inconnu « {args.get('object')} »")
    elif kind == "room" and args.get("room") not in project.rooms:
        problems.append(f"condition room: pièce inconnue « {args.get('room')} »")
    elif kind == "object_state":
        target = project.objects.get(args.get("object", ""))
        if target is None:
            problems.append(f"condition object_state: objet inconnu « {args.get('object')} »")
        elif args.get("state") not in target.states:
            problems.append(
                f"condition object_state: état inconnu « {args.get('state')} » pour « {target.id} »"
            )
    elif kind == "counter" and args.get("name") not in project.counters:
        problems.append(f"condition counter: compteur inconnu « {args.get('name')} »")


def _check_effect(effect: Effect, project: GameProject, problems: list[str]) -> None:
    args = effect.args
    kind = effect.kind
    if kind == "move_object":
        if args.get("object") not in project.objects:
            problems.append(f"effet move_object: objet inconnu « {args.get('object')} »")
        destination = args.get("to")
        if destination not in _RESERVED_LOCATIONS and destination not in project.rooms:
            problems.append(f"effet move_object: destination inconnue « {destination} »")
    elif kind == "remove_object" and args.get("object") not in project.objects:
        problems.append(f"effet remove_object: objet inconnu « {args.get('object')} »")
    elif kind == "set_object_state":
        target = project.objects.get(args.get("object", ""))
        if target is None:
            problems.append(f"effet set_object_state: objet inconnu « {args.get('object')} »")
        elif args.get("state") not in target.states:
            problems.append(
                f"effet set_object_state: état inconnu « {args.get('state')} » pour « {target.id} »"
            )
    elif kind == "set_room_variant":
        room = project.rooms.get(args.get("room", ""))
        if room is None:
            problems.append(f"effet set_room_variant: pièce inconnue « {args.get('room')} »")
        elif args.get("variant") not in room.variants:
            problems.append(
                f"effet set_room_variant: variante inconnue « {args.get('variant')} » "
                f"pour « {room.id} »"
            )
    elif kind == "teleport" and args.get("room") not in project.rooms:
        problems.append(f"effet teleport: pièce inconnue « {args.get('room')} »")
    elif kind == "end_game" and args.get("ending") not in project.endings:
        problems.append(f"effet end_game: fin inconnue « {args.get('ending')} »")
    elif kind == "set_exit":
        if args.get("room") not in project.rooms:
            problems.append(f"effet set_exit: pièce inconnue « {args.get('room')} »")
        if args.get("target") not in project.rooms:
            problems.append(f"effet set_exit: destination inconnue « {args.get('target')} »")
    elif kind == "remove_exit" and args.get("room") not in project.rooms:
        problems.append(f"effet remove_exit: pièce inconnue « {args.get('room')} »")
    elif kind in {"set_counter", "add_counter"} and args.get("name") not in project.counters:
        problems.append(f"effet {kind}: compteur inconnu « {args.get('name')} »")


def _translation_problems(project: GameProject) -> list[str]:
    """Signale les textes localisés sans entrée pour chaque langue."""
    problems: list[str] = []
    languages = project.languages
    default = project.meta.default_language

    def check(value: Any, where: str) -> None:
        if isinstance(value, dict):
            for language in languages:
                if language not in value:
                    problems.append(f"traduction manquante ({language}) : {where}")

    check(project.meta.title, "meta.title")
    if project.meta.description is not None:
        check(project.meta.description, "meta.description")
    for room in project.rooms.values():
        check(room.name, f"room {room.id}.name")
        check(room.description, f"room {room.id}.description")
        for name, variant in room.variants.items():
            check(variant.description, f"room {room.id}.variants.{name}.description")
    for game_object in project.objects.values():
        check(game_object.name, f"object {game_object.id}.name")
        check(game_object.description, f"object {game_object.id}.description")
    for key, message in project.messages.items():
        check(message, f"message {key}")
    for ending in project.endings.values():
        check(ending.title, f"ending {ending.id}.title")
        check(ending.text, f"ending {ending.id}.text")
    _ = default
    return problems


def validate_project(project: GameProject, *, strict_i18n: bool = False) -> list[str]:
    """Vérifie les références et la cohérence d'un projet chargé."""
    problems: list[str] = []

    if project.meta.default_language not in project.languages:
        problems.append(
            f"meta.default_language « {project.meta.default_language} » absent de languages"
        )
    if project.meta.start_room not in project.rooms:
        problems.append(f"meta.start_room « {project.meta.start_room} » est inconnue")

    for room in project.rooms.values():
        for direction, exit_value in room.exits.items():
            if exit_value.room not in project.rooms:
                problems.append(
                    f"room {room.id}: sortie « {direction} » vers une pièce inconnue "
                    f"« {exit_value.room} »"
                )
            for condition in _iter_conditions(exit_value.when):
                _check_condition(condition, project, problems)
        for effect in _iter_effects(room.on_enter):
            _check_effect(effect, project, problems)

    for game_object in project.objects.values():
        location = game_object.location
        if (
            location is not None
            and location not in _RESERVED_LOCATIONS
            and location not in project.rooms
        ):
            problems.append(f"object {game_object.id}: emplacement inconnu « {location} »")
        if (
            game_object.initial_state is not None
            and game_object.initial_state not in game_object.states
        ):
            problems.append(
                f"object {game_object.id}: initial_state « {game_object.initial_state} » "
                "absent de states"
            )

    seen_interactions: set[str] = set()
    for interaction in project.interactions:
        if interaction.id in seen_interactions:
            problems.append(f"interaction « {interaction.id} » définie plusieurs fois")
        seen_interactions.add(interaction.id)
        for object_id in (*interaction.objects, *interaction.indirect_objects):
            if object_id not in project.objects:
                problems.append(f"interaction {interaction.id}: objet inconnu « {object_id} »")
        for condition in _iter_conditions(interaction.when):
            _check_condition(condition, project, problems)
        for effect in _iter_effects(interaction.effects):
            _check_effect(effect, project, problems)

    if strict_i18n:
        problems.extend(_translation_problems(project))

    return problems
