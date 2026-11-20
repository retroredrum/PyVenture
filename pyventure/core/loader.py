"""Chargement d'un projet YAML vers le modèle."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

from .errors import ProjectError
from .model import (
    Condition,
    Effect,
    Ending,
    Exit,
    GameObject,
    GameProject,
    Interaction,
    Meta,
    ObjectState,
    Room,
    RoomVariant,
    Vocabulary,
)

_SIMPLE_CONDITIONS = {
    "has": "object",
    "not_has": "object",
    "flag": "flag",
    "not_flag": "flag",
    "room": "room",
}

_SIMPLE_EFFECTS = {
    "set_flag": "flag",
    "clear_flag": "flag",
    "remove_object": "object",
    "teleport": "room",
    "end_game": "ending",
    "play_sound": "sound",
}

_DICT_EFFECTS = {
    "set_counter",
    "add_counter",
    "move_object",
    "set_room_variant",
    "set_exit",
    "remove_exit",
}

_PAIR_EFFECTS = {"set_object_state": ("object", "state")}


def _require_mapping(data: Any, what: str) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ProjectError(f"{what} doit être un objet, reçu {type(data).__name__}")
    return data


def _single_entry(data: Any, what: str) -> tuple[str, Any]:
    mapping = _require_mapping(data, what)
    if len(mapping) != 1:
        raise ProjectError(f"{what} doit avoir exactement une clé, reçu {len(mapping)}")
    key, value = next(iter(mapping.items()))
    return str(key), value


def parse_condition(data: Any) -> Condition:
    key, value = _single_entry(data, "une condition")
    if key in _SIMPLE_CONDITIONS:
        return Condition(key, {_SIMPLE_CONDITIONS[key]: value})
    if key == "object_state":
        mapping = _require_mapping(value, "object_state")
        return Condition("object_state", {"object": mapping["object"], "state": mapping["state"]})
    if key in {"counter", "score"}:
        return Condition(key, dict(_require_mapping(value, key)))
    if key in {"any", "all"}:
        if not isinstance(value, list) or not value:
            raise ProjectError(f"{key} attend une liste non vide de conditions")
        return Condition(key, {"conditions": tuple(parse_condition(item) for item in value)})
    if key == "not":
        return Condition("not", {"condition": parse_condition(value)})
    raise ProjectError(f"condition inconnue : {key}")


def parse_condition_list(data: Any) -> tuple[Condition, ...]:
    if data is None:
        return ()
    if isinstance(data, dict):
        return (parse_condition(data),)
    if isinstance(data, list):
        return tuple(parse_condition(item) for item in data)
    raise ProjectError("les conditions doivent être un objet ou une liste")


def parse_effect(data: Any) -> Effect:
    key, value = _single_entry(data, "un effet")
    if key in _SIMPLE_EFFECTS:
        return Effect(key, {_SIMPLE_EFFECTS[key]: value})
    if key == "say":
        return Effect("say", {"message": value})
    if key in _DICT_EFFECTS:
        return Effect(key, dict(_require_mapping(value, key)))
    if key in _PAIR_EFFECTS:
        first, second = _PAIR_EFFECTS[key]
        mapping = _require_mapping(value, key)
        return Effect(key, {first: mapping[first], second: mapping[second]})
    if key == "score":
        return Effect("score", {"delta": value})
    raise ProjectError(f"effet inconnu : {key}")


def parse_effect_list(data: Any) -> tuple[Effect, ...]:
    if not isinstance(data, list):
        raise ProjectError("les effets doivent être une liste")
    return tuple(parse_effect(item) for item in data)


def _parse_exit(value: Any) -> Exit:
    if isinstance(value, str):
        return Exit(room=value)
    mapping = _require_mapping(value, "une sortie")
    return Exit(
        room=mapping["room"],
        when=parse_condition_list(mapping.get("when")),
        locked_message=mapping.get("locked_message"),
        hidden=bool(mapping.get("hidden", False)),
    )


def _parse_room(room_id: str, data: Any) -> Room:
    mapping = _require_mapping(data, f"la pièce {room_id}")
    variants = {
        name: RoomVariant(
            description=_require_mapping(value, "une variante")["description"],
            art=value.get("art"),
            name=value.get("name"),
        )
        for name, value in (mapping.get("variants") or {}).items()
    }
    return Room(
        id=room_id,
        name=mapping["name"],
        description=mapping["description"],
        art=mapping.get("art"),
        exits={
            str(direction): _parse_exit(value)
            for direction, value in (mapping.get("exits") or {}).items()
        },
        variants=variants,
        on_enter=parse_effect_list(mapping.get("on_enter") or []),
        comment=mapping.get("comment"),
    )


def _parse_object(object_id: str, data: Any) -> GameObject:
    mapping = _require_mapping(data, f"l'objet {object_id}")
    synonyms = {
        language: tuple(words) for language, words in (mapping.get("synonyms") or {}).items()
    }
    states = {
        name: ObjectState(
            description=value.get("description"),
            art=value.get("art"),
            name=value.get("name"),
        )
        for name, value in (mapping.get("states") or {}).items()
    }
    return GameObject(
        id=object_id,
        name=mapping["name"],
        description=mapping["description"],
        synonyms=synonyms,
        location=mapping.get("location"),
        portable=bool(mapping.get("portable", True)),
        art=mapping.get("art"),
        states=states,
        initial_state=mapping.get("initial_state"),
        comment=mapping.get("comment"),
    )


def _parse_interaction(data: Any) -> Interaction:
    mapping = _require_mapping(data, "une interaction")
    return Interaction(
        id=mapping["id"],
        verbs=tuple(mapping["verbs"]),
        effects=parse_effect_list(mapping["effects"]),
        objects=tuple(mapping.get("objects") or ()),
        indirect_objects=tuple(mapping.get("indirect_objects") or ()),
        prepositions=tuple(mapping.get("prepositions") or ()),
        when=parse_condition_list(mapping.get("when")),
        once=bool(mapping.get("once", False)),
        priority=int(mapping.get("priority", 0)),
        comment=mapping.get("comment"),
    )


def _parse_ending(ending_id: str, data: Any) -> Ending:
    mapping = _require_mapping(data, f"la fin {ending_id}")
    return Ending(
        id=ending_id,
        title=mapping["title"],
        text=mapping["text"],
        art=mapping.get("art"),
    )


def _parse_vocabulary(data: Any) -> Vocabulary:
    mapping = data or {}
    return Vocabulary(
        verbs={language: dict(words) for language, words in (mapping.get("verbs") or {}).items()},
        directions={
            language: dict(words) for language, words in (mapping.get("directions") or {}).items()
        },
        prepositions={
            language: dict(words) for language, words in (mapping.get("prepositions") or {}).items()
        },
    )


def _parse_meta(data: Any) -> Meta:
    mapping = _require_mapping(data, "meta")
    art = mapping.get("art") or {}
    return Meta(
        id=mapping["id"],
        title=mapping["title"],
        start_room=mapping["start_room"],
        default_language=mapping["default_language"],
        version=str(mapping.get("version", "0.0.0")),
        max_score=int(mapping.get("max_score", 0)),
        authors=tuple(mapping.get("authors") or ()),
        description=mapping.get("description"),
        art_width=int(art.get("width", 320)),
        art_height=int(art.get("height", 180)),
        art_scale=int(art.get("scale", 3)),
    )


def project_from_data(data: dict[str, Any], root: Path) -> GameProject:
    """Construit un ``GameProject`` depuis un dictionnaire déjà chargé."""
    return GameProject(
        meta=_parse_meta(data["meta"]),
        languages=tuple(data["languages"]),
        rooms={room_id: _parse_room(room_id, value) for room_id, value in data["rooms"].items()},
        objects={
            object_id: _parse_object(object_id, value)
            for object_id, value in (data.get("objects") or {}).items()
        },
        interactions=tuple(_parse_interaction(item) for item in (data.get("interactions") or [])),
        endings={
            ending_id: _parse_ending(ending_id, value)
            for ending_id, value in (data.get("endings") or {}).items()
        },
        vocabulary=_parse_vocabulary(data.get("vocabulary")),
        messages=dict(data.get("messages") or {}),
        flags={str(k): bool(v) for k, v in (data.get("flags") or {}).items()},
        counters={str(k): int(v) for k, v in (data.get("counters") or {}).items()},
        root=root,
    )


def read_yaml(path: Path) -> dict[str, Any]:
    """Lit un fichier YAML et vérifie qu'il contient un objet à la racine."""
    yaml = YAML(typ="safe")
    try:
        data = yaml.load(path)
    except Exception as exc:  # noqa: BLE001 - message utilisateur
        raise ProjectError(f"YAML invalide dans {path} : {exc}") from exc
    if not isinstance(data, dict):
        raise ProjectError(f"{path} doit contenir un objet YAML à la racine")
    return data


def load_project(path: Path, *, validate: bool = True, strict_i18n: bool = False) -> GameProject:
    """Charge un projet depuis ``game.yaml``."""
    from .schema import validate_data, validate_project

    path = Path(path)
    if path.is_dir():
        path = path / "game.yaml"
    if not path.is_file():
        raise ProjectError(f"projet introuvable : {path}")

    data = read_yaml(path)
    if validate:
        problems = validate_data(data)
        if problems:
            from .errors import ValidationError

            raise ValidationError(problems)

    project = project_from_data(data, path.parent)
    if validate:
        problems = validate_project(project, strict_i18n=strict_i18n)
        if problems:
            from .errors import ValidationError

            raise ValidationError(problems)
    return project
