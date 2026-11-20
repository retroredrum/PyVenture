"""Résolution des illustrations : variante > pièce > placeholder."""

from __future__ import annotations

from pathlib import Path

from .events import ArtHint
from .model import GameProject
from .state import GameState


class ArtResolver:
    """Trouve le chemin d'une image pour une pièce, un objet ou une fin."""

    def __init__(self, project: GameProject) -> None:
        self.project = project
        self.root = project.root

    def _absolute(self, relative: str | None) -> Path | None:
        if not relative:
            return None
        path = self.root / relative
        return path if path.is_file() else None

    def room_art(self, room_id: str, variant: str | None = None) -> Path | None:
        room = self.project.rooms.get(room_id)
        if room is None:
            return None
        if variant:
            variant_def = room.variants.get(variant)
            if variant_def is not None:
                found = self._absolute(variant_def.art)
                if found is not None:
                    return found
        return self._absolute(room.art)

    def object_art(self, object_id: str, state: GameState) -> Path | None:
        game_object = self.project.objects.get(object_id)
        if game_object is None:
            return None
        state_name = state.object_state(self.project, object_id)
        if state_name:
            state_def = game_object.states.get(state_name)
            if state_def is not None:
                found = self._absolute(state_def.art)
                if found is not None:
                    return found
        return self._absolute(game_object.art)

    def ending_art(self, ending_id: str) -> Path | None:
        ending = self.project.endings.get(ending_id)
        return self._absolute(ending.art) if ending is not None else None

    def resolve(self, hint: ArtHint, state: GameState) -> Path | None:
        if hint.ending:
            return self.ending_art(hint.ending)
        if hint.object_id:
            return self.object_art(hint.object_id, state)
        if hint.room:
            return self.room_art(hint.room, hint.variant)
        return None

    def placeholder_color(self, room_id: str) -> tuple[int, int, int]:
        """Couleur déterministe pour un placeholder de pièce."""
        seed = sum(ord(char) for char in room_id) % 360
        import colorsys

        red, green, blue = colorsys.hsv_to_rgb(seed / 360.0, 0.35, 0.45)
        return int(red * 255), int(green * 255), int(blue * 255)
