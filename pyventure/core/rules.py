"""Conditions, effets et registre de métadonnées pour l'éditeur."""

from __future__ import annotations

import random
from dataclasses import dataclass, field
from typing import Any

from .events import OutputLine, Style
from .model import Condition, Effect, GameProject
from .state import INVENTORY, GameState, exit_to_data


@dataclass
class EffectContext:
    """Contexte d'application des effets."""

    project: GameProject
    state: GameState
    lines: list[OutputLine] = field(default_factory=list)
    language: str = "en"
    rng: random.Random = field(default_factory=random.Random)
    ended: str | None = None
    sound: str | None = None

    def say(self, text: str, style: Style = Style.NORMAL) -> None:
        if text:
            self.lines.append(OutputLine(text, style))


# --- Conditions --------------------------------------------------------


def evaluate(condition: Condition, project: GameProject, state: GameState) -> bool:
    kind = condition.kind
    args = condition.args

    if kind == "has":
        return state.carries(args["object"])
    if kind == "not_has":
        return not state.carries(args["object"])
    if kind == "flag":
        return bool(state.flags.get(args["flag"], False))
    if kind == "not_flag":
        return not bool(state.flags.get(args["flag"], False))
    if kind == "room":
        return state.room == args["room"]
    if kind == "object_state":
        return state.object_state(project, args["object"]) == args["state"]
    if kind == "counter":
        return _compare(state.counter(project, args["name"]), args)
    if kind == "score":
        return _compare(state.score(project), args)
    if kind == "any":
        return any(evaluate(item, project, state) for item in args["conditions"])
    if kind == "all":
        return all(evaluate(item, project, state) for item in args["conditions"])
    if kind == "not":
        return not evaluate(args["condition"], project, state)
    return False


def evaluate_all(conditions: tuple[Condition, ...], project: GameProject, state: GameState) -> bool:
    return all(evaluate(condition, project, state) for condition in conditions)


def _compare(value: int, args: dict[str, Any]) -> bool:
    if "eq" in args and value != int(args["eq"]):
        return False
    if "gte" in args and value < int(args["gte"]):
        return False
    return not ("lte" in args and value > int(args["lte"]))


# --- Effets ------------------------------------------------------------


def apply_effect(effect: Effect, ctx: EffectContext) -> None:
    kind = effect.kind
    args = effect.args
    state = ctx.state
    project = ctx.project

    if kind == "say":
        ctx.say(_resolve_message(project, ctx.language, args["message"]))
    elif kind == "set_flag":
        state.flags[args["flag"]] = True
    elif kind == "clear_flag":
        state.flags[args["flag"]] = False
    elif kind == "set_counter":
        state.counters[args["name"]] = int(args["value"])
    elif kind == "add_counter":
        state.counters[args["name"]] = state.counter(project, args["name"]) + int(args["delta"])
    elif kind == "move_object":
        state.move_object(args["object"], args["to"])
    elif kind == "remove_object":
        state.move_object(args["object"], "nowhere")
    elif kind == "set_object_state":
        state.object_states[args["object"]] = args["state"]
    elif kind == "set_room_variant":
        state.room_variants[args["room"]] = args["variant"]
    elif kind == "set_exit":
        room = args["room"]
        direction = args["direction"]
        state.added_exits.setdefault(room, {})[direction] = exit_to_data(_dynamic_exit(args))
        removed = state.removed_exits.get(room, [])
        if direction in removed:
            removed.remove(direction)
    elif kind == "remove_exit":
        room = args["room"]
        direction = args["direction"]
        state.added_exits.get(room, {}).pop(direction, None)
        state.removed_exits.setdefault(room, []).append(direction)
    elif kind == "teleport":
        state.room = args["room"]
    elif kind == "score":
        state.counters["score"] = state.counter(project, "score") + int(args["delta"])
    elif kind == "end_game":
        ctx.ended = args["ending"]
        state.ended = args["ending"]
    elif kind == "play_sound":
        ctx.sound = args["sound"]


def apply_effects(effects: tuple[Effect, ...], ctx: EffectContext) -> None:
    for effect in effects:
        apply_effect(effect, ctx)


def _resolve_message(project: GameProject, language: str, message: Any) -> str:
    if isinstance(message, str) and message in project.messages:
        return project.text(project.messages[message], language, key=f"message {message}")
    return project.text(message, language)


def _dynamic_exit(args: dict[str, Any]):
    from .model import Exit

    return Exit(
        room=args["target"],
        locked_message=args.get("locked_message"),
        hidden=bool(args.get("hidden", False)),
    )


# --- Registre de métadonnées (éditeur) ---------------------------------

CONDITION_SPECS: dict[str, dict[str, str]] = {
    "has": {"label": "possède l'objet", "field": "object", "field_type": "object"},
    "not_has": {"label": "ne possède pas l'objet", "field": "object", "field_type": "object"},
    "flag": {"label": "flag vrai", "field": "flag", "field_type": "flag"},
    "not_flag": {"label": "flag faux", "field": "flag", "field_type": "flag"},
    "room": {"label": "dans la pièce", "field": "room", "field_type": "room"},
    "object_state": {
        "label": "état d'objet",
        "field": "object+state",
        "field_type": "object_state",
    },
    "counter": {"label": "compteur", "field": "name+comparison", "field_type": "counter"},
    "score": {"label": "score", "field": "comparison", "field_type": "comparison"},
    "any": {"label": "au moins une", "field": "conditions", "field_type": "conditions"},
    "all": {"label": "toutes", "field": "conditions", "field_type": "conditions"},
    "not": {"label": "négation", "field": "condition", "field_type": "condition"},
}

EFFECT_SPECS: dict[str, dict[str, str]] = {
    "say": {"label": "afficher un message", "field": "message", "field_type": "message"},
    "set_flag": {"label": "flag vrai", "field": "flag", "field_type": "flag"},
    "clear_flag": {"label": "flag faux", "field": "flag", "field_type": "flag"},
    "set_counter": {"label": "fixer un compteur", "field": "name+value", "field_type": "counter"},
    "add_counter": {
        "label": "ajouter au compteur",
        "field": "name+delta",
        "field_type": "counter",
    },
    "move_object": {"label": "déplacer un objet", "field": "object+to", "field_type": "move"},
    "remove_object": {"label": "retirer un objet", "field": "object", "field_type": "object"},
    "set_object_state": {
        "label": "changer l'état d'un objet",
        "field": "object+state",
        "field_type": "object_state",
    },
    "set_room_variant": {
        "label": "changer une variante",
        "field": "room+variant",
        "field_type": "room_variant",
    },
    "set_exit": {
        "label": "créer une sortie",
        "field": "room+direction+target",
        "field_type": "exit",
    },
    "remove_exit": {
        "label": "supprimer une sortie",
        "field": "room+direction",
        "field_type": "exit",
    },
    "teleport": {"label": "téléporter", "field": "room", "field_type": "room"},
    "score": {"label": "ajouter du score", "field": "delta", "field_type": "int"},
    "end_game": {"label": "terminer la partie", "field": "ending", "field_type": "ending"},
    "play_sound": {"label": "jouer un son", "field": "sound", "field_type": "sound"},
}


def condition_kinds() -> list[str]:
    return sorted(CONDITION_SPECS)


def effect_kinds() -> list[str]:
    return sorted(EFFECT_SPECS)


__all__ = [
    "CONDITION_SPECS",
    "EFFECT_SPECS",
    "EffectContext",
    "apply_effect",
    "apply_effects",
    "condition_kinds",
    "effect_kinds",
    "evaluate",
    "evaluate_all",
    "INVENTORY",
]
