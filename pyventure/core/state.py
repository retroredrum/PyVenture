"""État d'une partie, sérialisable et séparé du contenu."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .model import Exit, GameProject

INVENTORY = "inventory"
NOWHERE = "nowhere"


@dataclass
class GameState:
    """État mutable d'une partie."""

    room: str
    language: str
    inventory: list[str] = field(default_factory=list)
    object_locations: dict[str, str] = field(default_factory=dict)
    object_states: dict[str, str] = field(default_factory=dict)
    room_variants: dict[str, str] = field(default_factory=dict)
    flags: dict[str, bool] = field(default_factory=dict)
    counters: dict[str, int] = field(default_factory=dict)
    turns: int = 0
    ended: str | None = None
    added_exits: dict[str, dict[str, dict[str, Any]]] = field(default_factory=dict)
    removed_exits: dict[str, list[str]] = field(default_factory=dict)

    # -- Construction ---------------------------------------------------
    @classmethod
    def new(cls, project: GameProject, language: str | None = None) -> GameState:
        language = language or project.meta.default_language
        locations: dict[str, str] = {}
        for object_id, game_object in project.objects.items():
            locations[object_id] = game_object.location or NOWHERE
        inventory = [oid for oid, loc in locations.items() if loc == INVENTORY]
        return cls(
            room=project.meta.start_room,
            language=language,
            inventory=inventory,
            object_locations=locations,
            object_states={
                oid: game_object.initial_state
                for oid, game_object in project.objects.items()
                if game_object.initial_state
            },
            flags=dict(project.flags),
            counters=dict(project.counters),
        )

    # -- Requêtes -------------------------------------------------------
    def location_of(self, object_id: str) -> str:
        return self.object_locations.get(object_id, NOWHERE)

    def carries(self, object_id: str) -> bool:
        return self.location_of(object_id) == INVENTORY

    def objects_in(self, room_id: str) -> list[str]:
        return [oid for oid, loc in self.object_locations.items() if loc == room_id]

    def object_state(self, project: GameProject, object_id: str) -> str | None:
        if object_id in self.object_states:
            return self.object_states[object_id]
        game_object = project.objects.get(object_id)
        return game_object.initial_state if game_object else None

    def counter(self, project: GameProject, name: str) -> int:
        if name in self.counters:
            return self.counters[name]
        return project.counters.get(name, 0)

    def score(self, project: GameProject) -> int:
        return self.counter(project, "score")

    def exits_for(self, project: GameProject, room_id: str) -> dict[str, Exit]:
        room = project.rooms[room_id]
        merged: dict[str, Exit] = dict(room.exits)
        for direction, data in self.added_exits.get(room_id, {}).items():
            merged[direction] = _exit_from_data(data)
        for direction in self.removed_exits.get(room_id, []):
            merged.pop(direction, None)
        return merged

    # -- Mutations ------------------------------------------------------
    def move_object(self, object_id: str, destination: str) -> None:
        if object_id in self.inventory:
            self.inventory.remove(object_id)
        self.object_locations[object_id] = destination
        if destination == INVENTORY and object_id not in self.inventory:
            self.inventory.append(object_id)

    # -- Sérialisation --------------------------------------------------
    def to_dict(self) -> dict[str, Any]:
        return {
            "room": self.room,
            "language": self.language,
            "inventory": list(self.inventory),
            "object_locations": dict(self.object_locations),
            "object_states": dict(self.object_states),
            "room_variants": dict(self.room_variants),
            "flags": dict(self.flags),
            "counters": dict(self.counters),
            "turns": self.turns,
            "ended": self.ended,
            "added_exits": {room: dict(dirs) for room, dirs in self.added_exits.items()},
            "removed_exits": {room: list(dirs) for room, dirs in self.removed_exits.items()},
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GameState:
        return cls(
            room=data["room"],
            language=data["language"],
            inventory=list(data.get("inventory", [])),
            object_locations=dict(data.get("object_locations", {})),
            object_states=dict(data.get("object_states", {})),
            room_variants=dict(data.get("room_variants", {})),
            flags=dict(data.get("flags", {})),
            counters=dict(data.get("counters", {})),
            turns=int(data.get("turns", 0)),
            ended=data.get("ended"),
            added_exits={room: dict(dirs) for room, dirs in data.get("added_exits", {}).items()},
            removed_exits={
                room: list(dirs) for room, dirs in data.get("removed_exits", {}).items()
            },
        )


def _exit_from_data(data: dict[str, Any]) -> Exit:
    from .loader import parse_condition_list

    return Exit(
        room=data["room"],
        when=parse_condition_list(data.get("when")),
        locked_message=data.get("locked_message"),
        hidden=bool(data.get("hidden", False)),
    )


def exit_to_data(exit_value: Exit) -> dict[str, Any]:
    data: dict[str, Any] = {
        "room": exit_value.room,
        "locked_message": exit_value.locked_message,
        "hidden": exit_value.hidden,
    }
    return data
