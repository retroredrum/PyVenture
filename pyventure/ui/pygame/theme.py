"""Palette et polices de la fenêtre pygame."""

from __future__ import annotations

from dataclasses import dataclass, field

import pygame

from ...core.events import Style

RGB = tuple[int, int, int]


@dataclass(frozen=True)
class Theme:
    """Couleurs et tailles de police."""

    name: str = "dark"
    background: RGB = (18, 18, 24)
    panel: RGB = (28, 28, 38)
    panel_border: RGB = (64, 64, 86)
    input_bg: RGB = (24, 24, 32)
    input_fg: RGB = (232, 232, 232)
    prompt: RGB = (230, 190, 90)
    scrollbar: RGB = (90, 90, 120)
    overlay: RGB = (10, 10, 16)
    selection: RGB = (60, 60, 90)
    style_colors: dict[Style, RGB] = field(
        default_factory=lambda: {
            Style.NORMAL: (222, 222, 222),
            Style.ROOM_TITLE: (240, 200, 90),
            Style.DESCRIPTION: (205, 205, 205),
            Style.EXIT: (120, 200, 220),
            Style.ITEM: (130, 210, 140),
            Style.ERROR: (230, 120, 120),
            Style.SUCCESS: (130, 210, 140),
            Style.SYSTEM: (190, 150, 220),
            Style.DIALOGUE: (140, 170, 230),
        }
    )

    def color(self, style: Style) -> RGB:
        return self.style_colors.get(style, self.style_colors[Style.NORMAL])

    @classmethod
    def dark(cls) -> Theme:
        return cls()

    @classmethod
    def light(cls) -> Theme:
        return cls(
            name="light",
            background=(238, 238, 242),
            panel=(248, 248, 250),
            panel_border=(180, 180, 195),
            input_bg=(255, 255, 255),
            input_fg=(28, 28, 38),
            prompt=(150, 90, 10),
            scrollbar=(150, 150, 170),
            overlay=(230, 230, 236),
            selection=(205, 215, 235),
            style_colors={
                Style.NORMAL: (40, 40, 48),
                Style.ROOM_TITLE: (140, 80, 0),
                Style.DESCRIPTION: (55, 55, 65),
                Style.EXIT: (20, 90, 120),
                Style.ITEM: (20, 110, 50),
                Style.ERROR: (170, 30, 30),
                Style.SUCCESS: (20, 110, 50),
                Style.SYSTEM: (110, 50, 150),
                Style.DIALOGUE: (30, 70, 160),
            },
        )


class Fonts:
    """Polices mises en cache pour une échelle donnée."""

    def __init__(self, scale: float = 1.0) -> None:
        if not pygame.font.get_init():
            pygame.font.init()
        self.body = pygame.font.Font(None, max(10, int(20 * scale)))
        self.title = pygame.font.Font(None, max(12, int(26 * scale)))
        self.small = pygame.font.Font(None, max(9, int(16 * scale)))
        self.input = pygame.font.Font(None, max(10, int(22 * scale)))
