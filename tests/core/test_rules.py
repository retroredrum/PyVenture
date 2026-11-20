"""Tests des conditions et effets."""

from __future__ import annotations

from pyventure.core.model import Condition, Effect, GameProject
from pyventure.core.rules import EffectContext, apply_effect, evaluate
from pyventure.core.state import GameState


def test_flag_conditions(project: GameProject) -> None:
    state = GameState.new(project)
    assert evaluate(Condition("flag", {"flag": "cave_lit"}), project, state) is False
    assert evaluate(Condition("not_flag", {"flag": "cave_lit"}), project, state) is True
    state.flags["cave_lit"] = True
    assert evaluate(Condition("flag", {"flag": "cave_lit"}), project, state) is True


def test_has_and_room(project: GameProject) -> None:
    state = GameState.new(project)
    assert evaluate(Condition("room", {"room": "bedroom"}), project, state) is True
    assert evaluate(Condition("has", {"object": "flashlight"}), project, state) is False
    state.move_object("flashlight", "inventory")
    assert evaluate(Condition("has", {"object": "flashlight"}), project, state) is True
    assert evaluate(Condition("not_has", {"object": "flashlight"}), project, state) is False


def test_logical_conditions(project: GameProject) -> None:
    state = GameState.new(project)
    any_condition = Condition(
        "any",
        {
            "conditions": (
                Condition("flag", {"flag": "cave_lit"}),
                Condition("room", {"room": "bedroom"}),
            )
        },
    )
    assert evaluate(any_condition, project, state) is True
    all_condition = Condition(
        "all",
        {
            "conditions": (
                Condition("flag", {"flag": "cave_lit"}),
                Condition("room", {"room": "bedroom"}),
            )
        },
    )
    assert evaluate(all_condition, project, state) is False
    not_condition = Condition("not", {"condition": Condition("flag", {"flag": "cave_lit"})})
    assert evaluate(not_condition, project, state) is True


def test_object_state_default(project: GameProject) -> None:
    state = GameState.new(project)
    condition = Condition("object_state", {"object": "flashlight", "state": "off"})
    assert evaluate(condition, project, state) is True


def test_counter_comparison(project: GameProject) -> None:
    state = GameState.new(project)
    state.counters["score"] = 5
    assert evaluate(Condition("counter", {"name": "score", "gte": 3}), project, state) is True
    assert evaluate(Condition("counter", {"name": "score", "gte": 10}), project, state) is False
    assert evaluate(Condition("score", {"gte": 5}), project, state) is True


def test_move_object_effect(project: GameProject) -> None:
    state = GameState.new(project)
    ctx = EffectContext(project, state)
    apply_effect(Effect("move_object", {"object": "flashlight", "to": "inventory"}), ctx)
    assert state.carries("flashlight")
    apply_effect(Effect("move_object", {"object": "flashlight", "to": "corridor"}), ctx)
    assert state.location_of("flashlight") == "corridor"
    assert "flashlight" not in state.inventory


def test_set_and_add_counter(project: GameProject) -> None:
    state = GameState.new(project)
    ctx = EffectContext(project, state)
    apply_effect(Effect("set_counter", {"name": "score", "value": 3}), ctx)
    apply_effect(Effect("add_counter", {"name": "score", "delta": 4}), ctx)
    assert state.score(project) == 7


def test_end_game_effect(project: GameProject) -> None:
    state = GameState.new(project)
    ctx = EffectContext(project, state)
    apply_effect(Effect("end_game", {"ending": "escaped"}), ctx)
    assert ctx.ended == "escaped"
    assert state.ended == "escaped"


def test_set_exit_and_teleport(project: GameProject) -> None:
    state = GameState.new(project)
    ctx = EffectContext(project, state)
    apply_effect(
        Effect("set_exit", {"room": "bedroom", "direction": "west", "target": "cave"}),
        ctx,
    )
    exits = state.exits_for(project, "bedroom")
    assert exits["west"].room == "cave"
    apply_effect(Effect("teleport", {"room": "vault"}), ctx)
    assert state.room == "vault"
