"""Affichage des illustrations pixel art avec agrandissement entier."""

from __future__ import annotations

import pygame

from ...core.art import ArtResolver
from ...core.events import ArtHint
from ...core.model import GameProject
from ...core.state import GameState
from .theme import Theme


class ArtView:
    """Charge et affiche l'image d'une pièce, avec placeholder si absente."""

    def __init__(
        self,
        project: GameProject,
        font: pygame.font.Font,
        base_size: tuple[int, int] = (320, 180),
    ) -> None:
        self.project = project
        self.resolver = ArtResolver(project)
        self.font = font
        self.base_size = base_size
        self._cache: dict[str, pygame.Surface] = {}

    def surface_for(self, hint: ArtHint | None, state: GameState) -> pygame.Surface:
        key, path = self._key_and_path(hint, state)
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        if path is not None:
            surface = self._prepare(pygame.image.load(str(path)))
        else:
            surface = self._placeholder(hint, state)
        self._cache[key] = surface
        return surface

    @staticmethod
    def _prepare(surface: pygame.Surface) -> pygame.Surface:
        """Convertit la surface si un affichage est disponible."""
        if pygame.display.get_surface() is not None:
            return surface.convert_alpha()
        return surface

    def _key_and_path(self, hint: ArtHint | None, state: GameState) -> tuple[str, object | None]:
        if hint is None:
            return "placeholder:none", None
        path = self.resolver.resolve(hint, state)
        if path is not None:
            return f"file:{path}", path
        label = hint.ending or hint.room or "?"
        variant = hint.variant or ""
        return f"placeholder:{label}:{variant}:{state.language}", None

    def _placeholder_label(self, hint: ArtHint | None, state: GameState) -> str:
        if hint is None:
            return "?"
        if hint.room:
            room = self.project.rooms.get(hint.room)
            if room is not None:
                return self.project.text(room.name, state.language)
        return hint.ending or hint.room or "?"

    def _placeholder(self, hint: ArtHint | None, state: GameState) -> pygame.Surface:
        label = self._placeholder_label(hint, state)
        color = self.resolver.placeholder_color(label)
        surface = self._prepare(pygame.Surface(self.base_size))
        surface.fill(color)
        border = pygame.Rect(0, 0, *self.base_size)
        pygame.draw.rect(surface, (12, 12, 18), border, width=4)
        text = self.font.render(label, True, (240, 240, 240))
        text_rect = text.get_rect(center=(self.base_size[0] // 2, self.base_size[1] // 2))
        surface.blit(text, text_rect)
        return surface

    def scaled(
        self, hint: ArtHint | None, state: GameState, rect: pygame.Rect
    ) -> tuple[pygame.Surface, tuple[int, int]]:
        """Renvoie la surface agrandie et sa position centrée dans ``rect``."""
        surface = self.surface_for(hint, state)
        scale = self.integer_scale(surface.get_size(), rect.size)
        scaled = pygame.transform.scale(
            surface, (surface.get_width() * scale, surface.get_height() * scale)
        )
        position = (
            rect.x + (rect.width - scaled.get_width()) // 2,
            rect.y + (rect.height - scaled.get_height()) // 2,
        )
        return scaled, position

    def draw(
        self,
        target: pygame.Surface,
        rect: pygame.Rect,
        hint: ArtHint | None,
        state: GameState,
    ) -> None:
        scaled, position = self.scaled(hint, state, rect)
        target.blit(scaled, position)

    @staticmethod
    def integer_scale(source: tuple[int, int], available: tuple[int, int]) -> int:
        width_scale = available[0] // max(1, source[0])
        height_scale = available[1] // max(1, source[1])
        return max(1, min(width_scale, height_scale))

    def object_surface(self, object_id: str, state: GameState) -> pygame.Surface | None:
        path = self.resolver.object_art(object_id, state)
        if path is None:
            return None
        key = f"object:{path}"
        cached = self._cache.get(key)
        if cached is None:
            cached = self._prepare(pygame.image.load(str(path)))
            self._cache[key] = cached
        return cached


def draw_panel(
    target: pygame.Surface, rect: pygame.Rect, theme: Theme, title: str, font: pygame.font.Font
) -> None:
    """Dessine un panneau avec bordure et titre."""
    pygame.draw.rect(target, theme.panel, rect)
    pygame.draw.rect(target, theme.panel_border, rect, width=1)
    if title:
        label = font.render(title, True, theme.prompt)
        target.blit(label, (rect.x + 8, rect.y + 6))
