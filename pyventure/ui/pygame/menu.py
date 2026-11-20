"""Menu overlay de la fenêtre pygame."""

from __future__ import annotations

from dataclasses import dataclass

import pygame

from .theme import Fonts, Theme


@dataclass(frozen=True)
class MenuItem:
    action: str
    label: str


class Menu:
    """Menu déroulant superposé, navigable au clavier."""

    def __init__(self) -> None:
        self.title = ""
        self.items: list[MenuItem] = []
        self.index = 0
        self.open = False

    def show(self, title: str, items: list[MenuItem]) -> None:
        self.title = title
        self.items = list(items)
        self.index = 0
        self.open = True

    def hide(self) -> None:
        self.open = False

    def move(self, delta: int) -> None:
        if self.items:
            self.index = (self.index + delta) % len(self.items)

    def current(self) -> MenuItem | None:
        return self.items[self.index] if self.items else None

    def draw(self, target: pygame.Surface, theme: Theme, fonts: Fonts) -> None:
        if not self.open:
            return
        width, height = target.get_size()
        veil = pygame.Surface((width, height), pygame.SRCALPHA)
        veil.fill((0, 0, 0, 150))
        target.blit(veil, (0, 0))

        item_height = fonts.body.get_linesize() + 12
        panel_width = min(440, width - 80)
        panel_height = item_height * (len(self.items) + 1) + 36
        panel = pygame.Rect(0, 0, panel_width, panel_height)
        panel.center = (width // 2, height // 2)
        pygame.draw.rect(target, theme.panel, panel)
        pygame.draw.rect(target, theme.panel_border, panel, width=2)

        title_surface = fonts.title.render(self.title, True, theme.prompt)
        target.blit(title_surface, (panel.x + 18, panel.y + 12))
        y = panel.y + 12 + title_surface.get_height() + 10

        for index, item in enumerate(self.items):
            row = pygame.Rect(panel.x + 8, y, panel.width - 16, item_height)
            if index == self.index:
                pygame.draw.rect(target, theme.selection, row)
            label = fonts.body.render(item.label, True, theme.input_fg)
            target.blit(label, (panel.x + 22, y + (item_height - label.get_height()) // 2))
            y += item_height
