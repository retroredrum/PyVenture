"""Panneau d'inventaire avec icônes d'objets."""

from __future__ import annotations

import pygame

from ...core.events import Style
from ...core.i18n import Translator
from ...core.model import GameProject
from ...core.state import GameState
from .art_view import ArtView, draw_panel
from .theme import Fonts, Theme

ICON_SIZE = 32


class InventoryPanel:
    """Liste les objets portés, avec leur icône si elle existe."""

    def __init__(
        self, theme: Theme, fonts: Fonts, art_view: ArtView, translator: Translator
    ) -> None:
        self.theme = theme
        self.fonts = fonts
        self.art_view = art_view
        self.translator = translator

    def draw(
        self,
        target: pygame.Surface,
        rect: pygame.Rect,
        project: GameProject,
        state: GameState,
    ) -> None:
        title = self.translator.t("inventory.title", state.language).rstrip(" :")
        draw_panel(target, rect, self.theme, title, self.fonts.small)

        y = rect.y + 30
        if not state.inventory:
            empty = self.fonts.small.render(
                self.translator.t("inventory.empty", state.language),
                True,
                self.theme.color(Style.NORMAL),
            )
            target.blit(empty, (rect.x + 10, y))
            return

        for object_id in state.inventory:
            game_object = project.objects[object_id]
            name = project.text(game_object.name, state.language)
            icon_rect = pygame.Rect(rect.x + 10, y, ICON_SIZE, ICON_SIZE)
            self._draw_icon(target, icon_rect, object_id, state, name)
            label = self.fonts.small.render(name, True, self.theme.color(Style.ITEM))
            target.blit(label, (icon_rect.right + 8, y + (ICON_SIZE - label.get_height()) // 2))
            y += ICON_SIZE + 6
            if y > rect.bottom - ICON_SIZE:
                break

    def _draw_icon(
        self,
        target: pygame.Surface,
        rect: pygame.Rect,
        object_id: str,
        state: GameState,
        name: str,
    ) -> None:
        surface = self.art_view.object_surface(object_id, state)
        if surface is None:
            pygame.draw.rect(target, self.theme.panel_border, rect)
            letter = self.fonts.small.render(name[:1].upper(), True, self.theme.color(Style.ITEM))
            target.blit(letter, letter.get_rect(center=rect.center))
            return
        scaled = pygame.transform.scale(surface, (ICON_SIZE, ICON_SIZE))
        target.blit(scaled, rect)
