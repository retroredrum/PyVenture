"""Utilitaires de texte : découpage en lignes et rendu."""

from __future__ import annotations

import pygame

from ...core.events import OutputLine
from .theme import RGB, Theme


def wrap_text(text: str, font: pygame.font.Font, width: int) -> list[str]:
    """Découpe un texte en lignes qui tiennent dans ``width`` pixels.

    Les sauts de ligne explicites sont respectés. Les mots plus larges que
    ``width`` sont coupés caractère par caractère.
    """
    if width <= 0:
        return [text]
    lines: list[str] = []
    for paragraph in text.split("\n"):
        if not paragraph:
            lines.append("")
            continue
        current = ""
        for word in paragraph.split(" "):
            if font.size(word)[0] > width:
                if current:
                    lines.append(current)
                    current = ""
                chunks = _break_word(word, font, width)
                lines.extend(chunks[:-1])
                current = chunks[-1] if chunks else ""
                continue
            candidate = word if not current else f"{current} {word}"
            if font.size(candidate)[0] <= width:
                current = candidate
            else:
                lines.append(current)
                current = word
        if current:
            lines.append(current)
    return lines or [""]


def _break_word(word: str, font: pygame.font.Font, width: int) -> list[str]:
    chunks: list[str] = []
    current = ""
    for char in word:
        if current and font.size(current + char)[0] > width:
            chunks.append(current)
            current = char
        else:
            current += char
    if current:
        chunks.append(current)
    return chunks


def render_lines(
    lines: list[OutputLine],
    font: pygame.font.Font,
    theme: Theme,
    width: int,
) -> list[tuple[pygame.Surface, int]]:
    """Convertit des lignes stylées en surfaces rendues et leur hauteur."""
    rendered: list[tuple[pygame.Surface, int]] = []
    line_height = font.get_linesize()
    for line in lines:
        for visual in wrap_text(line.text, font, width):
            surface = font.render(visual, True, theme.color(line.style))
            rendered.append((surface, line_height))
    return rendered


def draw_text(
    target: pygame.Surface,
    text: str,
    font: pygame.font.Font,
    color: RGB,
    position: tuple[int, int],
) -> pygame.Rect:
    surface = font.render(text, True, color)
    return target.blit(surface, position)
