"""Transcript défilant des lignes de jeu."""

from __future__ import annotations

import pygame

from ...core.events import OutputLine
from .text import render_lines
from .theme import Fonts, Theme


class Transcript:
    """Historique de texte, aligné en bas, avec défilement."""

    def __init__(self, theme: Theme, fonts: Fonts, padding: int = 10) -> None:
        self.theme = theme
        self.fonts = fonts
        self.padding = padding
        self.lines: list[OutputLine] = []
        self.scroll = 0
        self._cache_width = -1
        self._rendered: list[tuple[pygame.Surface, int]] = []

    def append(self, lines: list[OutputLine]) -> None:
        self.lines.extend(lines)
        self.scroll = 0
        self._cache_width = -1

    def clear(self) -> None:
        self.lines.clear()
        self.scroll = 0
        self._cache_width = -1

    def scroll_by(self, delta: int) -> None:
        """Fait défiler le transcript. ``delta`` positif remonte vers le passé."""
        self.scroll = max(0, self.scroll + delta)

    def content_height(self) -> int:
        return sum(height for _, height in self._rendered)

    def draw(self, target: pygame.Surface, rect: pygame.Rect) -> None:
        inner_width = max(1, rect.width - 2 * self.padding)
        if self._cache_width != inner_width:
            self._rendered = render_lines(self.lines, self.fonts.body, self.theme, inner_width)
            self._cache_width = inner_width

        view_height = rect.height - 2 * self.padding
        total_height = self.content_height()
        max_scroll = max(0, total_height - view_height)
        self.scroll = min(self.scroll, max_scroll)

        start_y = rect.bottom - self.padding - total_height + self.scroll
        target.set_clip(rect)
        y = start_y
        for surface, height in self._rendered:
            if y + height >= rect.top and y <= rect.bottom:
                target.blit(surface, (rect.x + self.padding, y))
            y += height
        target.set_clip(None)

        if max_scroll > 0:
            self._draw_scrollbar(target, rect, total_height, view_height)

    def _draw_scrollbar(
        self, target: pygame.Surface, rect: pygame.Rect, total_height: int, view_height: int
    ) -> None:
        track = pygame.Rect(rect.right - 6, rect.top + 4, 3, rect.height - 8)
        pygame.draw.rect(target, self.theme.panel_border, track)
        ratio = view_height / total_height
        thumb_height = max(16, int(track.height * ratio))
        max_scroll = total_height - view_height
        offset = 0 if max_scroll == 0 else self.scroll / max_scroll
        thumb_y = track.y + int((track.height - thumb_height) * (1 - offset))
        thumb = pygame.Rect(track.x, thumb_y, track.width, thumb_height)
        pygame.draw.rect(target, self.theme.scrollbar, thumb)
