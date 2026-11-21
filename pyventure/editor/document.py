"""Document de projet éditable : chargement, sauvegarde, undo/redo, validation.

Cette couche ne dépend pas de Tkinter : elle est testable sans interface.
"""

from __future__ import annotations

import copy
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq

from ..core.errors import ProjectError
from ..core.loader import project_from_data
from ..core.model import GameProject
from ..core.schema import validate_data, validate_project

FORMAT = "pyventure-game"
FORMAT_VERSION = 1
MAX_UNDO = 100


def make_yaml() -> YAML:
    """YAML en mode round-trip : préserve commentaires, ordre et guillemets."""
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.indent(mapping=2, sequence=4, offset=2)
    return yaml


class ProjectDocument:
    """Projet en mémoire, avec pile d'annulation et validation."""

    def __init__(self, data: CommentedMap, path: Path | None = None) -> None:
        self.data = data
        self.path = Path(path) if path is not None else None
        self.dirty = False
        self._undo: list[CommentedMap] = []
        self._redo: list[CommentedMap] = []

    # -- Construction ---------------------------------------------------
    @classmethod
    def new(
        cls,
        *,
        game_id: str = "new-game",
        title: str = "New Game",
        languages: tuple[str, ...] = ("en",),
        start_room: str = "start",
    ) -> ProjectDocument:
        data = CommentedMap()
        data["format"] = FORMAT
        data["format_version"] = FORMAT_VERSION

        meta = CommentedMap()
        meta["id"] = game_id
        meta["title"] = CommentedMap({language: title for language in languages})
        meta["default_language"] = languages[0]
        meta["start_room"] = start_room
        meta["version"] = "0.1.0"
        meta["max_score"] = 0
        meta["art"] = CommentedMap({"width": 320, "height": 180, "scale": 3})
        data["meta"] = meta

        data["languages"] = CommentedSeq(languages)
        data["flags"] = CommentedMap()
        data["counters"] = CommentedMap({"score": 0})
        data["vocabulary"] = CommentedMap(
            {
                "verbs": CommentedMap({languages[0]: CommentedMap()}),
                "directions": CommentedMap({languages[0]: CommentedMap()}),
            }
        )
        data["messages"] = CommentedMap()
        rooms = CommentedMap()
        room = CommentedMap()
        room["name"] = CommentedMap({language: "Start" for language in languages})
        room["description"] = CommentedMap({language: "A new room." for language in languages})
        rooms[start_room] = room
        data["rooms"] = rooms
        data["objects"] = CommentedMap()
        data["interactions"] = CommentedSeq()
        data["endings"] = CommentedMap()
        return cls(data)

    @classmethod
    def load(cls, path: Path | str) -> ProjectDocument:
        path = Path(path)
        if path.is_dir():
            path = path / "game.yaml"
        if not path.is_file():
            raise ProjectError(f"projet introuvable : {path}")
        yaml = make_yaml()
        try:
            with path.open("r", encoding="utf-8") as handle:
                data = yaml.load(handle)
        except Exception as exc:  # noqa: BLE001 - message utilisateur
            raise ProjectError(f"YAML invalide dans {path} : {exc}") from exc
        if not isinstance(data, dict):
            raise ProjectError(f"{path} doit contenir un objet YAML à la racine")
        return cls(data, path)

    # -- Persistance ----------------------------------------------------
    @property
    def root(self) -> Path:
        return self.path.parent if self.path is not None else Path.cwd()

    def save(self, path: Path | str | None = None) -> Path:
        target = Path(path) if path is not None else self.path
        if target is None:
            raise ProjectError("aucun chemin de sauvegarde")
        if target.is_dir():
            target = target / "game.yaml"
        target.parent.mkdir(parents=True, exist_ok=True)
        yaml = make_yaml()
        with target.open("w", encoding="utf-8") as handle:
            yaml.dump(self.data, handle)
        self.path = target
        self.dirty = False
        return target

    # -- Annulation -----------------------------------------------------
    def snapshot(self) -> None:
        self._undo.append(copy.deepcopy(self.data))
        if len(self._undo) > MAX_UNDO:
            self._undo.pop(0)
        self._redo.clear()

    def can_undo(self) -> bool:
        return bool(self._undo)

    def can_redo(self) -> bool:
        return bool(self._redo)

    def undo(self) -> bool:
        if not self._undo:
            return False
        self._redo.append(copy.deepcopy(self.data))
        self.data = self._undo.pop()
        self.dirty = True
        return True

    def redo(self) -> bool:
        if not self._redo:
            return False
        self._undo.append(copy.deepcopy(self.data))
        self.data = self._redo.pop()
        self.dirty = True
        return True

    def touch(self) -> None:
        self.dirty = True

    # -- Accès ----------------------------------------------------------
    def languages(self) -> list[str]:
        languages = self.data.get("languages")
        return list(languages) if languages else []

    def default_language(self) -> str:
        meta = self.data.get("meta") or {}
        return str(meta.get("default_language", "en"))

    def meta(self) -> CommentedMap:
        return self.data.setdefault("meta", CommentedMap())

    def section(self, name: str) -> Any:
        return self.data.setdefault(name, CommentedMap())

    # -- Modèle et validation -------------------------------------------
    def project(self) -> GameProject:
        return project_from_data(self.data, self.root)

    def validate(self) -> list[str]:
        problems = validate_data(self.data)
        if problems:
            return problems
        try:
            project = self.project()
        except ProjectError as exc:
            return [str(exc)]
        return validate_project(project)

    # -- Mises à jour typées --------------------------------------------
    def set_localized(self, container: Any, key: str, language: str, value: str) -> None:
        """Écrit une valeur localisée, en respectant la forme simple ou multilingue."""
        current = container.get(key)
        if isinstance(current, dict):
            current[language] = value
        else:
            container[key] = value

    # -- Renommage avec mise à jour des références ----------------------
    def rename_room(self, old: str, new: str) -> None:
        self._rename_key("rooms", old, new)
        self._rewrite_references(old, new)

    def rename_object(self, old: str, new: str) -> None:
        self._rename_key("objects", old, new)
        self._rewrite_references(old, new)

    def _rename_key(self, section: str, old: str, new: str) -> None:
        mapping = self.data.get(section)
        if not isinstance(mapping, dict) or old not in mapping or new in mapping:
            return
        value = mapping[old]
        items = list(mapping.items())
        keys = [key for key, _ in items]
        index = keys.index(old)
        mapping.clear()
        for position, (key, item) in enumerate(items):
            if position == index:
                mapping[new] = value
            else:
                mapping[key] = item

    def _rewrite_references(self, old: str, new: str) -> None:
        meta = self.data.get("meta")
        if isinstance(meta, dict) and meta.get("start_room") == old:
            meta["start_room"] = new

        rooms = self.data.get("rooms")
        if isinstance(rooms, dict):
            for room in rooms.values():
                if not isinstance(room, dict):
                    continue
                exits = room.get("exits")
                if isinstance(exits, dict):
                    for direction, value in list(exits.items()):
                        if value == old:
                            exits[direction] = new
                        elif isinstance(value, dict) and value.get("room") == old:
                            value["room"] = new
                self._rewrite_effects(room.get("on_enter"), old, new)

        objects = self.data.get("objects")
        if isinstance(objects, dict):
            for game_object in objects.values():
                if isinstance(game_object, dict) and game_object.get("location") == old:
                    game_object["location"] = new

        interactions = self.data.get("interactions")
        if isinstance(interactions, list):
            for interaction in interactions:
                if not isinstance(interaction, dict):
                    continue
                for key in ("objects", "indirect_objects"):
                    values = interaction.get(key)
                    if isinstance(values, list):
                        interaction[key] = [new if item == old else item for item in values]
                self._rewrite_conditions(interaction.get("when"), old, new)
                self._rewrite_effects(interaction.get("effects"), old, new)

    def _rewrite_conditions(self, conditions: Any, old: str, new: str) -> None:
        if not isinstance(conditions, list):
            return
        for condition in conditions:
            if not isinstance(condition, dict) or len(condition) != 1:
                continue
            kind, value = next(iter(condition.items()))
            if kind in ("has", "not_has", "room") and value == old:
                condition[kind] = new
            elif kind == "object_state" and isinstance(value, dict) and value.get("object") == old:
                value["object"] = new
            elif kind in ("any", "all"):
                self._rewrite_conditions(value, old, new)
            elif kind == "not":
                self._rewrite_conditions([value], old, new)

    def _rewrite_effects(self, effects: Any, old: str, new: str) -> None:
        if not isinstance(effects, list):
            return
        for effect in effects:
            if not isinstance(effect, dict) or len(effect) != 1:
                continue
            kind, value = next(iter(effect.items()))
            if kind == "move_object" and isinstance(value, dict):
                if value.get("object") == old:
                    value["object"] = new
                if value.get("to") == old:
                    value["to"] = new
            elif kind in ("remove_object", "teleport") and value == old:
                effect[kind] = new
            elif kind == "set_object_state" and isinstance(value, dict):
                if value.get("object") == old:
                    value["object"] = new
            elif kind == "set_room_variant" and isinstance(value, dict):
                if value.get("room") == old:
                    value["room"] = new
            elif kind in ("set_exit", "remove_exit") and isinstance(value, dict):
                if value.get("room") == old:
                    value["room"] = new
                if kind == "set_exit" and value.get("target") == old:
                    value["target"] = new

    # -- Positions de la carte ------------------------------------------
    def map_path(self) -> Path | None:
        if self.path is None:
            return None
        return self.path.parent / ".pyventure" / "map.yaml"

    def load_map_positions(self) -> dict[str, tuple[int, int]]:
        path = self.map_path()
        if path is None or not path.is_file():
            return {}
        try:
            data = make_yaml().load(path) or {}
        except Exception:  # noqa: BLE001 - positions facultatives
            return {}
        positions: dict[str, tuple[int, int]] = {}
        if isinstance(data, dict):
            for room_id, value in data.items():
                if isinstance(value, (list, tuple)) and len(value) == 2:
                    positions[str(room_id)] = (int(value[0]), int(value[1]))
        return positions

    def save_map_positions(self, positions: dict[str, tuple[int, int]]) -> None:
        path = self.map_path()
        if path is None:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        data = CommentedMap()
        for room_id, (x, y) in positions.items():
            data[str(room_id)] = CommentedSeq([int(x), int(y)])
        with path.open("w", encoding="utf-8") as handle:
            make_yaml().dump(data, handle)
