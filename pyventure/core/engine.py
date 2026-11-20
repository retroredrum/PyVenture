"""Moteur de jeu : exécution d'un tour et production de sortie."""

from __future__ import annotations

import random
from pathlib import Path

from .errors import ParseError
from .events import ArtHint, OutputLine, Style, TurnResult
from .i18n import Translator
from .model import GameProject
from .parser import Command, parse
from .rules import EffectContext, apply_effects, evaluate_all
from .state import INVENTORY, GameState

LOCALES_DIR = Path(__file__).resolve().parent.parent / "locales"


class Engine:
    """Exécute des commandes sur un ``GameState`` donné."""

    def __init__(
        self,
        project: GameProject,
        translator: Translator | None = None,
        rng: random.Random | None = None,
    ) -> None:
        self.project = project
        self.translator = translator or Translator.from_directory(
            LOCALES_DIR, default_language=project.meta.default_language
        )
        self.rng = rng or random.Random()

    # -- API ------------------------------------------------------------
    def new_state(self, language: str | None = None) -> GameState:
        state = GameState.new(self.project, language)
        return state

    def start(self, state: GameState) -> TurnResult:
        """Résultat d'ouverture : accueil + description de la pièce."""
        lines = [
            OutputLine(
                self._t(state, "game.welcome", title=self.project.text(self.project.meta.title, state.language)),
                Style.SYSTEM,
            )
        ]
        lines.extend(self._room_lines(state))
        return TurnResult(lines=lines, art=self._art_hint(state))

    def look(self, state: GameState) -> TurnResult:
        """Résultat d'un simple « regarder » : description de la pièce."""
        return TurnResult(lines=self._room_lines(state), art=self._art_hint(state))

    def execute(self, text: str, state: GameState) -> TurnResult:
        result = TurnResult()
        state.turns += 1

        try:
            command = parse(self.project, state, text)
        except ParseError as exc:
            result.lines.append(OutputLine(self._t(state, exc.key, **exc.params), Style.ERROR))
            return result

        if command.verb == "quit":
            result.lines.append(OutputLine(self._t(state, "game.quit"), Style.SYSTEM))
            result.quit = True
            return result

        ctx = EffectContext(
            project=self.project,
            state=state,
            language=state.language,
            rng=self.rng,
        )
        room_before = state.room
        if not self._try_interactions(command, ctx):
            self._builtin(command, ctx)
        if state.room != room_before and not ctx.ended:
            ctx.lines.extend(self._room_lines(state))

        if ctx.ended:
            ctx.lines.extend(self._ending_lines(state, ctx.ended))

        result.lines.extend(ctx.lines)
        result.ended = ctx.ended
        result.sound = ctx.sound
        result.art = self._art_hint(state)
        return result

    # -- Interactions ---------------------------------------------------
    def _try_interactions(self, command: Command, ctx: EffectContext) -> bool:
        state = ctx.state
        candidates = []
        for interaction in self.project.interactions:
            if command.verb not in interaction.verbs:
                continue
            if interaction.objects:
                if command.direct not in interaction.objects:
                    continue
            elif command.direct is not None:
                continue
            if interaction.indirect_objects:
                if command.indirect not in interaction.indirect_objects:
                    continue
            elif command.indirect is not None:
                continue
            if interaction.prepositions and command.preposition not in interaction.prepositions:
                continue
            if interaction.once and state.flags.get(f"_done:{interaction.id}"):
                continue
            if not evaluate_all(interaction.when, self.project, state):
                continue
            candidates.append(interaction)

        if not candidates:
            return False

        candidates.sort(key=lambda item: item.priority, reverse=True)
        chosen = candidates[0]
        if chosen.once:
            state.flags[f"_done:{chosen.id}"] = True
        apply_effects(chosen.effects, ctx)
        return True

    # -- Commandes intégrées -------------------------------------------
    def _builtin(self, command: Command, ctx: EffectContext) -> None:
        state = ctx.state
        verb = command.verb
        if verb in {"look", "examine"}:
            if command.direct:
                ctx.lines.extend(self._examine_lines(state, command.direct))
            else:
                ctx.lines.extend(self._room_lines(state))
        elif verb == "inventory":
            ctx.lines.extend(self._inventory_lines(state))
        elif verb == "get":
            self._get(command, ctx)
        elif verb == "drop":
            self._drop(command, ctx)
        elif verb == "go":
            self._go(command, ctx)
        elif verb == "wait":
            ctx.say(self._t(state, "wait.nothing"))
        elif verb == "help":
            ctx.say(self._t(state, "help.text"), Style.SYSTEM)
        elif verb == "score":
            ctx.say(
                self._t(
                    state,
                    "score.text",
                    score=state.score(self.project),
                    max=self.project.meta.max_score,
                ),
                Style.SYSTEM,
            )
        else:
            ctx.say(self._t(state, "error.generic"), Style.ERROR)

    def _get(self, command: Command, ctx: EffectContext) -> None:
        state = ctx.state
        if not command.direct:
            ctx.say(self._t(state, "get.what"), Style.ERROR)
            return
        game_object = self.project.objects[command.direct]
        name = self.project.text(game_object.name, state.language)
        location = state.location_of(game_object.id)
        if location == INVENTORY:
            ctx.say(self._t(state, "get.already", object=name))
        elif location != state.room:
            ctx.say(self._t(state, "get.not_here", object=name), Style.ERROR)
        elif not game_object.portable:
            ctx.say(self._t(state, "get.cant", object=name), Style.ERROR)
        else:
            state.move_object(game_object.id, INVENTORY)
            ctx.say(self._t(state, "get.taken", object=name), Style.SUCCESS)

    def _drop(self, command: Command, ctx: EffectContext) -> None:
        state = ctx.state
        if not command.direct:
            ctx.say(self._t(state, "drop.what"), Style.ERROR)
            return
        game_object = self.project.objects[command.direct]
        name = self.project.text(game_object.name, state.language)
        if not state.carries(game_object.id):
            ctx.say(self._t(state, "drop.not_carrying", object=name), Style.ERROR)
            return
        state.move_object(game_object.id, state.room)
        ctx.say(self._t(state, "drop.dropped", object=name), Style.SUCCESS)

    def _go(self, command: Command, ctx: EffectContext) -> None:
        state = ctx.state
        direction = command.direct
        exits = state.exits_for(self.project, state.room)
        exit_value = exits.get(direction or "")
        if exit_value is None:
            ctx.say(self._t(state, "go.cant"), Style.ERROR)
            ctx.lines.extend(self._exit_lines(state))
            return
        if exit_value.when and not evaluate_all(exit_value.when, self.project, state):
            if exit_value.locked_message is not None:
                ctx.say(self._message(state, exit_value.locked_message))
            else:
                ctx.say(self._t(state, "go.locked"), Style.ERROR)
            return
        state.room = exit_value.room
        room = self.project.rooms[state.room]
        if room.on_enter:
            apply_effects(room.on_enter, ctx)

    # -- Rendu ----------------------------------------------------------
    def _room_lines(self, state: GameState) -> list[OutputLine]:
        room = self.project.rooms[state.room]
        lines: list[OutputLine] = []
        name = self.project.text(room.name, state.language)
        variant_name = state.room_variants.get(state.room)
        variant = room.variants.get(variant_name) if variant_name else None
        if variant and variant.name is not None:
            name = self.project.text(variant.name, state.language)
        lines.append(OutputLine(name, Style.ROOM_TITLE))

        description = variant.description if variant else room.description
        lines.append(OutputLine(self.project.text(description, state.language), Style.DESCRIPTION))

        objects = [
            self.project.text(self.project.objects[oid].name, state.language)
            for oid in state.objects_in(state.room)
        ]
        if objects:
            lines.append(
                OutputLine(
                    self._t(state, "room.you_see", objects=", ".join(objects)),
                    Style.ITEM,
                )
            )
        lines.extend(self._exit_lines(state))
        return lines

    def _exit_lines(self, state: GameState) -> list[OutputLine]:
        exits = state.exits_for(self.project, state.room)
        visible: list[str] = []
        for direction, exit_value in exits.items():
            if exit_value.hidden and exit_value.when and not evaluate_all(
                exit_value.when, self.project, state
            ):
                continue
            visible.append(self._t(state, f"direction.{direction}"))
        if not visible:
            return []
        return [OutputLine(self._t(state, "exits.title", exits=", ".join(visible)), Style.EXIT)]

    def _inventory_lines(self, state: GameState) -> list[OutputLine]:
        if not state.inventory:
            return [OutputLine(self._t(state, "inventory.empty"), Style.NORMAL)]
        names = [
            self.project.text(self.project.objects[oid].name, state.language)
            for oid in state.inventory
        ]
        return [
            OutputLine(self._t(state, "inventory.title"), Style.NORMAL),
            OutputLine(", ".join(names), Style.ITEM),
        ]

    def _examine_lines(self, state: GameState, object_id: str) -> list[OutputLine]:
        game_object = self.project.objects[object_id]
        lines = [OutputLine(self.project.text(game_object.name, state.language), Style.ROOM_TITLE)]
        state_name = state.object_state(self.project, object_id)
        state_def = game_object.states.get(state_name) if state_name else None
        description = (
            state_def.description
            if state_def and state_def.description is not None
            else game_object.description
        )
        lines.append(OutputLine(self.project.text(description, state.language), Style.DESCRIPTION))
        return lines

    def _ending_lines(self, state: GameState, ending_id: str) -> list[OutputLine]:
        ending = self.project.endings.get(ending_id)
        if ending is None:
            return []
        return [
            OutputLine(self.project.text(ending.title, state.language), Style.ROOM_TITLE),
            OutputLine(self.project.text(ending.text, state.language), Style.DESCRIPTION),
            OutputLine(self._t(state, "game.ended"), Style.SYSTEM),
        ]

    def _art_hint(self, state: GameState) -> ArtHint:
        return ArtHint(room=state.room, variant=state.room_variants.get(state.room))

    def _message(self, state: GameState, value: object) -> str:
        if isinstance(value, str) and value in self.project.messages:
            return self.project.text(
                self.project.messages[value], state.language, key=f"message {value}"
            )
        return self.project.text(value, state.language)

    # -- Utilitaires ----------------------------------------------------
    def _t(self, state: GameState, key: str, **params: object) -> str:
        return self.translator.t(key, state.language, **params)
